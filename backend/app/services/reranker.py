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

        # 1. Model inference
        model = self.get_model()
        pairs = [[query, h["chunk_text"]] for h in hits]
        
        inference_start = time.perf_counter()
        raw_scores = model.predict(pairs, batch_size=settings.RERANK_BATCH_SIZE)
        inference_latency = time.perf_counter() - inference_start
        
        scored_hits = []
        for idx, h in enumerate(hits):
            raw_score = float(raw_scores[idx])
            prob_score = 1.0 / (1.0 + math.exp(-raw_score))
            
            hit_copy = dict(h)
            hit_copy["rerank_score"] = round(prob_score, 4)
            hit_copy["score"] = round(prob_score, 4)
            hit_copy["_orig_rank"] = idx
            scored_hits.append(hit_copy)

        # 2. Sort by rerank score descending
        scored_hits.sort(key=lambda x: x["rerank_score"], reverse=True)

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

        final_hits = retained_hits[:top_k]
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
