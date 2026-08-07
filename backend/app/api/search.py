# ==========================================
# PRODUCTION LOCKED - STABLE RAG V1 CORE
# DO NOT MODIFY without explicit regression verification
# ==========================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.search import SearchRequest, SearchResponse, SearchHit
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from app.core.config import settings
from qdrant_client.http import models as qdrant_models

import logging
logger = logging.getLogger("app.api.search")

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
def semantic_search(
    search_req: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = search_req.query.strip()
    if not query:
        return {"chunks": [], "query_analysis": None, "query_rewrite": None}

    # Run Query Transformation Engine
    query_transformation = None
    analysis = None
    query_rewrite = None
    retrieval_query = query

    try:
        from app.services.query_transformation import query_transformer
        query_transformation = query_transformer.transform(query, None, db)
        
        # Populate analysis and query_rewrite for backward compatibility
        from app.services.query_analyzer import query_analyzer
        from app.services.query_rewriter import query_rewriter
        resolved_q = query_transformation.transformation_metadata.get("resolved_query", query)
        analysis = query_analyzer.analyze(resolved_q)
        query_rewrite = query_rewriter.rewrite(analysis)
        retrieval_query = query_transformation.rewritten_query
    except Exception as e:
        logger.error(f"Query transformation failed: {e}", exc_info=True)
        # Fallback to basic Query Analysis and Rewriting
        try:
            from app.services.query_analyzer import query_analyzer
            analysis = query_analyzer.analyze(query)
        except Exception as ae:
            logger.error(f"Fallback Query analysis failed: {ae}", exc_info=True)
        try:
            from app.services.query_rewriter import query_rewriter
            query_rewrite = query_rewriter.rewrite(analysis) if analysis else None
            if query_rewrite and query_rewrite.rewrite_applied:
                retrieval_query = query_rewrite.rewritten_query
        except Exception as re:
            logger.error(f"Fallback Query rewriting failed: {re}", exc_info=True)

    # Run Adaptive Retrieval Routing
    retrieval_limit = 5
    adaptive_retrieval = None
    if analysis:
        try:
            from app.services.adaptive_retrieval import adaptive_retriever
            adaptive_retrieval = adaptive_retriever.determine_strategy(analysis, query_rewrite)
            if adaptive_retrieval:
                retrieval_limit = adaptive_retrieval.selected_top_k
        except Exception as e:
            logger.error(f"Adaptive retrieval routing failed: {e}", exc_info=True)

    # Enforce security filter: retrieve only documents owned by the logged-in user
    user_docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    user_doc_ids = [doc.id for doc in user_docs]
    doc_id_to_name = {doc.id: doc.name for doc in user_docs}

    # Retrieve semantic chunks using Hybrid Retrieval Engine
    raw_hits = []
    hybrid_retrieval = None
    if user_doc_ids:
        try:
            from app.services.hybrid_retriever import hybrid_retriever
            
            # Determine search queries list (single or multi-query)
            search_queries = [retrieval_query]
            if query_transformation and settings.MULTI_QUERY_ENABLED:
                search_queries = query_transformation.generated_retrieval_queries
                
            all_hits = []
            seen_chunks = set()
            
            for q_idx, q in enumerate(search_queries):
                hits, hr = hybrid_retriever.search(
                    db=db,
                    query=q,
                    user_doc_ids=user_doc_ids,
                    limit=retrieval_limit
                )
                all_hits.extend(hits)
                # Keep primary hybrid_retrieval for response metadata
                if q_idx == 0:
                    hybrid_retrieval = hr
                    
            # Deduplicate and sort by score descending
            all_hits.sort(key=lambda x: x["score"], reverse=True)
            deduped_hits = []
            for h in all_hits:
                cid = h["chunk_id"]
                if cid not in seen_chunks:
                    seen_chunks.add(cid)
                    deduped_hits.append(h)
            raw_hits = deduped_hits[:retrieval_limit]
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Hybrid search failed: {str(e)}"
            )

    # Run Retrieval Verification
    retrieval_verification = None
    try:
        from app.services.retrieval_verifier import retrieval_verifier
        verification_result = retrieval_verifier.verify(raw_hits, retrieval_query)
        
        # Check if verification status is FAIL and verifier is enabled
        if verification_result.verification_status == "FAIL" and settings.RETRIEVAL_VERIFIER_ENABLED:
            logger.info("Retrieval Verification failed. Triggering retrieval retry...")
            
            # Record first attempt metadata
            verification_result.first_attempt_status = "FAIL"
            verification_result.first_attempt_score = verification_result.quality_score
            verification_result.retry_performed = True
            
            # Apply configured retry strategy
            retry_strategy = settings.RETRIEVAL_VERIFIER_RETRY_STRATEGY.lower()
            retry_limit = retrieval_limit
            retry_query = retrieval_query
            
            if retry_strategy == "expand_limit":
                retry_limit = retrieval_limit * 2
                logger.info(f"Retry Strategy: expand_limit (expanding limit from {retrieval_limit} to {retry_limit})")
            elif retry_strategy == "raw_query":
                retry_query = query
                logger.info(f"Retry Strategy: raw_query (falling back to original user query: '{retry_query}')")
                
            # Perform second retrieval attempt
            retried_hits = []
            if user_doc_ids:
                retried_hits, retry_hybrid = hybrid_retriever.search(
                    db=db,
                    query=retry_query,
                    user_doc_ids=user_doc_ids,
                    limit=retry_limit
                )
                hybrid_retrieval = retry_hybrid
            
            # Verify the retried hits
            retry_verify_result = retrieval_verifier.verify(retried_hits, retry_query)
            
            # Update verification result with final outcomes
            verification_result.verification_status = retry_verify_result.verification_status
            verification_result.quality_score = retry_verify_result.quality_score
            verification_result.retrieval_confidence = retry_verify_result.retrieval_confidence
            verification_result.verification_reason = f"Attempt 1 FAIL (Quality: {verification_result.first_attempt_score}). Attempt 2 [{retry_verify_result.verification_status}] (Quality: {retry_verify_result.quality_score}). Reason: {retry_verify_result.verification_reason}"
            verification_result.recommended_action = retry_verify_result.recommended_action
            verification_result.final_attempt_status = retry_verify_result.verification_status
            verification_result.final_attempt_score = retry_verify_result.quality_score
            
            # Overwrite original hits
            raw_hits = retried_hits
            
        retrieval_verification = verification_result
    except Exception as e:
        logger.error(f"Retrieval verification or retry failed: {e}", exc_info=True)

    # Run GraphRAG Retrieval and Merge Context if enabled
    if settings.GRAPHRAG_ENABLED:
        try:
            from app.services.graph_retriever import graph_retriever
            from app.services.graph_ranker import graph_ranker
            
            graph_hits, subgraph = graph_retriever.retrieve_graph_context(
                db=db,
                query=retrieval_query,
                user_doc_ids=user_doc_ids
            )
            if graph_hits:
                nodes_ids = {node["id"] for node in subgraph["entities"]}
                pr_scores = graph_ranker.calculate_pagerank(nodes_ids, subgraph["relationships"])
                raw_hits = graph_ranker.rank_hybrid_chunks(raw_hits, graph_hits, pr_scores)
        except Exception as ge:
            logger.error(f"GraphRAG retrieval/ranking failed: {ge}", exc_info=True)

    # Run Cross-Encoder Reranking
    reranking = None
    try:
        from app.services.reranker import reranker as reranker_service
        raw_hits, reranking = reranker_service.rerank(retrieval_query, raw_hits, retrieval_verification)
    except Exception as e:
        logger.error(f"Reranking failed: {e}", exc_info=True)

    # Run Context Compression Engine
    context_compression = None
    try:
        from app.services.context_compressor import context_compressor
        full_raw_hits = []
        for hit in raw_hits:
            doc_id = hit["document_id"]
            full_raw_hits.append({
                "chunk_id": hit["chunk_id"],
                "document_id": doc_id,
                "document_name": doc_id_to_name.get(doc_id, "Unknown Document"),
                "page_number": hit["page_number"],
                "chunk_text": hit["chunk_text"],
                "score": hit["score"]
            })
            
        context_compression = context_compressor.compress(retrieval_query, full_raw_hits)
        
        if context_compression.enabled:
            hits = []
            for cc in context_compression.compressed_chunks:
                hits.append(
                    SearchHit(
                        chunk_text=cc.chunk_text,
                        score=round(cc.score, 4),
                        page_number=cc.page_number,
                        document_name=cc.document_name,
                        document_id=cc.document_id
                    )
                )
        else:
            hits = []
            for hit in raw_hits:
                doc_id = hit["document_id"]
                hits.append(
                    SearchHit(
                        chunk_text=hit["chunk_text"],
                        score=round(hit["score"], 4),
                        page_number=hit["page_number"],
                        document_name=doc_id_to_name.get(doc_id, "Unknown Document"),
                        document_id=doc_id
                    )
                )
    except Exception as e:
        logger.error(f"Context compression in search failed: {e}", exc_info=True)
        hits = []
        for hit in raw_hits:
            doc_id = hit["document_id"]
            hits.append(
                SearchHit(
                    chunk_text=hit["chunk_text"],
                    score=round(hit["score"], 4),
                    page_number=hit["page_number"],
                    document_name=doc_id_to_name.get(doc_id, "Unknown Document"),
                    document_id=doc_id
                )
            )

    return {
        "chunks": hits,
        "query_analysis": analysis,
        "query_rewrite": query_rewrite,
        "adaptive_retrieval": adaptive_retrieval,
        "retrieval_verification": retrieval_verification,
        "reranking": reranking,
        "hybrid_retrieval": hybrid_retrieval,
        "query_transformation": query_transformation,
        "context_compression": context_compression,
        "answer_verification": None,
        "self_reflection": None,
        "confidence": None,
        "evaluation": None,
        "agentic_rag": None
    }

