import logging
import time
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from qdrant_client.http import models as qdrant_models

from app.core.config import settings
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from app.services.bm25_retriever import bm25_retriever
from app.schemas.hybrid_retrieval import HybridRetrievalResult, HybridRetrievalHitMetadata

logger = logging.getLogger("app.services.hybrid_retriever")

class HybridRetrievalService:
    def search(
        self,
        db: Session,
        query: str,
        user_doc_ids: List[int],
        limit: int
    ) -> Tuple[List[Dict[str, Any]], HybridRetrievalResult]:
        start_time = time.perf_counter()
        
        if not user_doc_ids:
            logger.info("HybridRetrieval: Empty user_doc_ids list. Returning empty list.")
            empty_res = HybridRetrievalResult(
                hits=[],
                original_dense_ranking=[],
                original_sparse_ranking=[],
                merged_ranking=[]
            )
            return [], empty_res
            
        # 1. Fallback to dense if disabled
        if not settings.HYBRID_RETRIEVAL_ENABLED:
            logger.info("HybridRetrieval is disabled. Falling back to dense semantic retrieval.")
            query_vector = embedding_service.get_embedding(query)
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="document_id",
                        match=qdrant_models.MatchAny(any=user_doc_ids)
                    )
                ]
            )
            dense_hits = vector_store.search_similar_chunks(
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter
            )
            
            original_dense = [str(h["chunk_id"]) for h in dense_hits]
            
            hits_meta = []
            for idx, h in enumerate(dense_hits):
                h["score"] = float(h["score"])
                h["chunk_id"] = str(h["chunk_id"])
                
                hits_meta.append(
                    HybridRetrievalHitMetadata(
                        chunk_id=str(h["chunk_id"]),
                        source="dense",
                        dense_score=h["score"],
                        sparse_score=0.0,
                        normalized_dense_score=1.0,
                        normalized_sparse_score=0.0,
                        final_score=h["score"],
                        document_id=h["document_id"],
                        page_number=h["page_number"],
                        chunk_text=h["chunk_text"]
                    )
                )
                
            result_obj = HybridRetrievalResult(
                hits=hits_meta,
                original_dense_ranking=original_dense,
                original_sparse_ranking=[],
                merged_ranking=original_dense
            )
            
            # Map chunk_ids back to integers if digit
            output_hits = []
            for hit in dense_hits:
                output_hits.append({
                    "chunk_id": int(hit["chunk_id"]) if hit["chunk_id"].isdigit() else hit["chunk_id"],
                    "document_id": hit["document_id"],
                    "page_number": hit["page_number"],
                    "chunk_text": hit["chunk_text"],
                    "score": hit["score"]
                })
            return output_hits, result_obj

        # 2. Dense Semantic Search
        dense_start = time.perf_counter()
        query_vector = embedding_service.get_embedding(query)
        query_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="document_id",
                    match=qdrant_models.MatchAny(any=user_doc_ids)
                )
            ]
        )
        dense_hits = vector_store.search_similar_chunks(
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter
        )
        dense_latency = time.perf_counter() - dense_start

        # 3. Sparse Keyword Search (BM25)
        sparse_start = time.perf_counter()
        sparse_hits = []
        if settings.BM25_ENABLED:
            sparse_hits = bm25_retriever.search(
                db=db,
                query=query,
                user_doc_ids=user_doc_ids,
                limit=limit
            )
        sparse_latency = time.perf_counter() - sparse_start

        # 4. Normalization map calculation
        def get_normalization_map(hits: List[Dict[str, Any]]) -> Dict[str, float]:
            if not hits:
                return {}
            scores = [float(h["score"]) for h in hits]
            min_score = min(scores)
            max_score = max(scores)
            diff = max_score - min_score
            
            norm_map = {}
            for h in hits:
                cid = str(h["chunk_id"])
                if diff > 0.0:
                    norm_map[cid] = (float(h["score"]) - min_score) / diff
                else:
                    norm_map[cid] = 1.0
            return norm_map

        dense_norm = get_normalization_map(dense_hits)
        sparse_norm = get_normalization_map(sparse_hits)

        # Build lookup tables for details
        dense_lookup = {str(h["chunk_id"]): h for h in dense_hits}
        sparse_lookup = {str(h["chunk_id"]): h for h in sparse_hits}

        all_cids = set(dense_lookup.keys()).union(set(sparse_lookup.keys()))
        merged_candidates = []

        w_dense = settings.DENSE_RETRIEVAL_WEIGHT
        w_sparse = settings.BM25_WEIGHT

        for cid in all_cids:
            in_dense = cid in dense_lookup
            in_sparse = cid in sparse_lookup
            
            orig_dense_score = float(dense_lookup[cid]["score"]) if in_dense else 0.0
            orig_sparse_score = float(sparse_lookup[cid]["score"]) if in_sparse else 0.0
            
            n_dense = dense_norm[cid] if in_dense else 0.0
            n_sparse = sparse_norm[cid] if in_sparse else 0.0
            
            final_score = w_dense * n_dense + w_sparse * n_sparse
            
            if in_dense and in_sparse:
                src = "hybrid"
            elif in_dense:
                src = "dense"
            else:
                src = "sparse"
                
            doc = dense_lookup[cid] if in_dense else sparse_lookup[cid]
            
            candidate = {
                "chunk_id": cid,
                "document_id": doc["document_id"],
                "page_number": doc["page_number"],
                "chunk_text": doc["chunk_text"],
                "score": round(final_score, 4),
                "source": src,
                "dense_score": round(orig_dense_score, 4),
                "sparse_score": round(orig_sparse_score, 4),
                "normalized_dense_score": round(n_dense, 4),
                "normalized_sparse_score": round(n_sparse, 4)
            }
            merged_candidates.append(candidate)

        # 5. Sort candidates descending
        merged_candidates.sort(key=lambda x: x["score"], reverse=True)
        final_hits = merged_candidates[:limit]
        
        # Build schema hits lists
        hits_meta = []
        for rank, h in enumerate(final_hits):
            hits_meta.append(
                HybridRetrievalHitMetadata(
                    chunk_id=h["chunk_id"],
                    source=h["source"],
                    dense_score=h["dense_score"],
                    sparse_score=h["sparse_score"],
                    normalized_dense_score=h["normalized_dense_score"],
                    normalized_sparse_score=h["normalized_sparse_score"],
                    final_score=h["score"],
                    document_id=h["document_id"],
                    page_number=h["page_number"],
                    chunk_text=h["chunk_text"]
                )
            )

        original_dense = [str(h["chunk_id"]) for h in dense_hits]
        original_sparse = [str(h["chunk_id"]) for h in sparse_hits]
        merged_ranking = [str(h["chunk_id"]) for h in final_hits]

        result_obj = HybridRetrievalResult(
            hits=hits_meta,
            original_dense_ranking=original_dense,
            original_sparse_ranking=original_sparse,
            merged_ranking=merged_ranking
        )
        
        total_latency = time.perf_counter() - start_time
        
        if settings.HYBRID_DEBUG_LOGGING:
            logger.info("\n--- HYBRID RETRIEVAL REPORT ---")
            logger.info(f"Query: '{query}' | Target Docs: {user_doc_ids}")
            logger.info(f"Dense Chunks found: {len(dense_hits)} (Latency: {dense_latency*1000:.2f}ms)")
            logger.info(f"Sparse Chunks found: {len(sparse_hits)} (Latency: {sparse_latency*1000:.2f}ms)")
            logger.info(f"Total Unique Candidates: {len(merged_candidates)}")
            logger.info(f"Original Dense Ranking:  {original_dense}")
            logger.info(f"Original Sparse Ranking: {original_sparse}")
            logger.info(f"Final Merged Ranking:    {merged_ranking}")
            logger.info(f"Total Hybrid Latency:    {total_latency*1000:.2f}ms")
            
            for rank, hit in enumerate(final_hits):
                logger.info(
                    f" - Rank {rank}: Chunk {hit['chunk_id']} | Source: {hit['source']} | "
                    f"Dense: {hit['dense_score']:.4f} (Norm: {hit['normalized_dense_score']:.4f}) | "
                    f"Sparse: {hit['sparse_score']:.4f} (Norm: {hit['normalized_sparse_score']:.4f}) | "
                    f"Final: {hit['score']:.4f}"
                )
            logger.info("--------------------------------\n")
            
        output_hits = []
        for h in final_hits:
            output_hits.append({
                "chunk_id": int(h["chunk_id"]) if h["chunk_id"].isdigit() else h["chunk_id"],
                "document_id": h["document_id"],
                "page_number": h["page_number"],
                "chunk_text": h["chunk_text"],
                "score": h["score"]
            })

        return output_hits, result_obj

hybrid_retriever = HybridRetrievalService()
