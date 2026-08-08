import logging
import math
import time
from typing import List, Dict, Any, Tuple
from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.schemas.reranking import RerankingResult, RerankedHitMetadata

logger = logging.getLogger("app.services.reranker")

class RerankingService:
    _model = None

    @classmethod
    def get_model(cls) -> CrossEncoder:
        if cls._model is None:
            logger.info(f"Reranker: Initializing CrossEncoder model: {settings.RERANKER_MODEL_NAME}...")
            cls._model = CrossEncoder(settings.RERANKER_MODEL_NAME)
            logger.info("Reranker: CrossEncoder Model Loaded Successfully.")
        return cls._model

    def rerank(
        self, 
        query: str, 
        hits: List[Dict[str, Any]],
        retrieval_verification: Any = None
    ) -> Tuple[List[Dict[str, Any]], RerankingResult]:
        start_time = time.perf_counter()
        
        if not hits:
            logger.info("Reranker: Empty candidate hits. Bypassing reranking.")
            return [], RerankingResult(
                hits=[],
                model_name=settings.RERANKER_MODEL_NAME,
                retained_count=0,
                discarded_count=0,
                original_ranking=[],
                reranked_ranking=[]
            )

        if not settings.RERANKER_ENABLED:
            logger.info("Reranker is disabled in config. Returning original candidates.")
            original_ranking = [str(h["chunk_id"]) for h in hits]
            
            hits_meta = []
            for idx, h in enumerate(hits):
                hits_meta.append(
                    RerankedHitMetadata(
                        chunk_id=str(h["chunk_id"]),
                        original_rank=idx,
                        reranked_position=idx,
                        reranker_score=float(h.get("score", 0.0)),
                        status="retained",
                        chunk_text=h.get("chunk_text", "")
                    )
                )
            return hits, RerankingResult(
                hits=hits_meta,
                model_name=settings.RERANKER_MODEL_NAME,
                retained_count=len(hits),
                discarded_count=0,
                original_ranking=original_ranking,
                reranked_ranking=original_ranking
            )

        # 1. Model inference with multi-clause evaluation for sequence queries
        import re
        clauses = [query]
        from_to = re.search(r'from\s+(.+?)\s+to\s+(.+)', query, re.IGNORECASE)
        if from_to:
            clauses.append(from_to.group(1).strip())
            clauses.append(from_to.group(2).strip())
        elif ' and ' in query.lower():
            parts = [p.strip() for p in re.split(r'\band\b', query, flags=re.IGNORECASE) if len(p.strip()) > 5]
            clauses.extend(parts)
        clauses = list(dict.fromkeys(clauses))

        model = self.get_model()
        
        all_pairs = []
        hit_clause_counts = []
        for h in hits:
            text = h["chunk_text"]
            pairs_for_hit = [[c, text] for c in clauses]
            all_pairs.extend(pairs_for_hit)
            hit_clause_counts.append(len(pairs_for_hit))

        inference_start = time.perf_counter()
        raw_scores = model.predict(all_pairs, batch_size=settings.RERANK_BATCH_SIZE)
        inference_latency = time.perf_counter() - inference_start

        raw_scores_list = [float(rs) for rs in (raw_scores if hasattr(raw_scores, '__iter__') else [raw_scores])]

        scored_hits = []
        score_idx = 0
        for idx, h in enumerate(hits):
            count = hit_clause_counts[idx]
            hit_raw_scores = raw_scores_list[score_idx : score_idx + count]
            score_idx += count
            
            probs = [1.0 / (1.0 + math.exp(-rs)) for rs in hit_raw_scores]
            prob_score = max(probs)
            
            orig_score = float(h.get("score", 0.0))
            combined_score = 0.70 * prob_score + 0.30 * orig_score
            
            hit_copy = dict(h)
            hit_copy["rerank_score"] = round(prob_score, 4)
            hit_copy["score"] = round(combined_score, 4)
            hit_copy["_orig_rank"] = idx
            scored_hits.append(hit_copy)

        # 2. Sort by combined rerank score descending
        scored_hits.sort(key=lambda x: x["score"], reverse=True)

        # 3. Filter and categorize by threshold
        retained_hits = []
        metadata_hits = []
        
        retained_cids = []
        original_cids = [str(h["chunk_id"]) for h in hits]
        
        retained_count = 0
        discarded_count = 0
        
        threshold = settings.RERANK_SCORE_THRESHOLD
        top_k = settings.RERANK_TOP_K
        
        for rerank_pos, h in enumerate(scored_hits):
            cid = str(h["chunk_id"])
            prob_score = h["rerank_score"]
            orig_rank = h["_orig_rank"]
            
            if prob_score >= threshold:
                status_lbl = "retained"
                retained_count += 1
                retained_hits.append(h)
                retained_cids.append(cid)
            else:
                status_lbl = "discarded"
                discarded_count += 1
                
            metadata_hits.append(
                RerankedHitMetadata(
                    chunk_id=cid,
                    original_rank=orig_rank,
                    reranked_position=rerank_pos,
                    reranker_score=prob_score,
                    status=status_lbl,
                    chunk_text=h.get("chunk_text", "")
                )
            )

        # Deduplicate near-duplicate sliding window chunks to ensure top_k contains diverse chunks across pages/sections
        deduped_retained = []
        seen_word_sets = []
        for h in retained_hits:
            words = set(re.findall(r'\b[a-z0-9]+\b', h.get("chunk_text", "").lower()))
            if not words:
                continue
            is_dup = False
            for seen in seen_word_sets:
                overlap = len(words & seen) / float(min(len(words), len(seen)))
                if len(words) >= 12 and len(seen) >= 12 and overlap > 0.75:
                    is_dup = True
                    break
            if not is_dup:
                deduped_retained.append(h)
                seen_word_sets.append(words)

        final_hits = deduped_retained[:top_k]
        final_cids = [str(h["chunk_id"]) for h in final_hits]

        total_latency = time.perf_counter() - start_time

        if settings.RERANK_DEBUG_LOGGING:
            logger.info("\n--- CROSS-ENCODER RERANKING REPORT ---")
            logger.info(f"Query: '{query}'")
            logger.info(f"Model Name: '{settings.RERANKER_MODEL_NAME}'")
            logger.info(f"Original Candidate Count: {len(hits)} | Retained: {len(final_hits)} | Discarded: {discarded_count}")
            logger.info(f"Inference Latency: {inference_latency*1000:.2f}ms | Total Latency: {total_latency*1000:.2f}ms")
            logger.info(f"Original IDs Sequence: {original_cids}")
            logger.info(f"Reranked/Retained IDs: {final_cids}")
            
            for r_pos, h in enumerate(scored_hits):
                status_lbl = "RETAINED" if h["rerank_score"] >= threshold else "DISCARDED"
                logger.info(
                    f" - {status_lbl}: Chunk {h['chunk_id']} | Original Rank {h['_orig_rank']} -> Rerank Position {r_pos} | "
                    f"Base Score: {hits[h['_orig_rank']].get('score', 0.0):.4f} -> Rerank Score: {h['rerank_score']:.4f}"
                )
            logger.info("---------------------------------------\n")

        result_obj = RerankingResult(
            hits=metadata_hits,
            model_name=settings.RERANKER_MODEL_NAME,
            retained_count=retained_count,
            discarded_count=discarded_count,
            original_ranking=original_cids,
            reranked_ranking=final_cids
        )

        output_hits = []
        for h in final_hits:
            cid = h["chunk_id"]
            if isinstance(cid, str) and cid.isdigit():
                cid = int(cid)
            output_hits.append({
                "chunk_id": cid,
                "document_id": h["document_id"],
                "page_number": h["page_number"],
                "chunk_text": h["chunk_text"],
                "score": h["score"],
                "is_graph_retrieved": h.get("is_graph_retrieved", False)
            })

        return output_hits, result_obj

reranker = RerankingService()
