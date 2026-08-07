# ==========================================
# PRODUCTION LOCKED - STABLE RAG V1 CORE
# DO NOT MODIFY without explicit regression verification
# ==========================================

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from app.core.config import settings
from qdrant_client.http import models as qdrant_models

import logging
logger = logging.getLogger("app.api.chat")

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def grounded_chat(
    chat_req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = chat_req.question.strip()
    if not question:
        return {
            "answer": "Please ask a valid question.",
            "citations": [],
            "query_analysis": None
        }

    agentic_enabled = settings.AGENTIC_RAG_ENABLED or request.headers.get("x-agentic-rag") == "true"
    if agentic_enabled:
        from app.services.agentic_orchestrator import agentic_orchestrator
        return agentic_orchestrator.execute_agentic_flow(
            db=db,
            question=question,
            session_id=chat_req.session_id,
            current_user=current_user,
            agentic_enabled=agentic_enabled
        )

    # Run Query Transformation Engine
    query_transformation = None
    analysis = None
    query_rewrite = None
    retrieval_query = question

    try:
        from app.services.query_transformation import query_transformer
        query_transformation = query_transformer.transform(question, chat_req.session_id, db)
        
        # Populate analysis and query_rewrite for backward compatibility
        from app.services.query_analyzer import query_analyzer
        from app.services.query_rewriter import query_rewriter
        resolved_q = query_transformation.transformation_metadata.get("resolved_query", question)
        analysis = query_analyzer.analyze(resolved_q)
        query_rewrite = query_rewriter.rewrite(analysis)
        retrieval_query = query_transformation.rewritten_query
    except Exception as e:
        logger.error(f"Query transformation failed: {e}", exc_info=True)
        # Fallback to basic Query Analysis and Rewriting
        try:
            from app.services.query_analyzer import query_analyzer
            analysis = query_analyzer.analyze(question)
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

    # Retrieve all documents owned by the logged-in user to enforce security boundary
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
                
            # Multi-query Retrieval with Reciprocal Rank Fusion (RRF)
            # Collect hits per query list to prevent specific subquery results from being overridden
            query_hits_lists = []
            
            for q_idx, q in enumerate(search_queries):
                hits, hr = hybrid_retriever.search(
                    db=db,
                    query=q,
                    user_doc_ids=user_doc_ids,
                    limit=retrieval_limit
                )
                query_hits_lists.append(hits)
                if q_idx == 0:
                    hybrid_retrieval = hr
                    
            # Reciprocal Rank Fusion (RRF) across all subqueries
            rrf_k = 60.0
            chunk_rrf_scores: Dict[Any, float] = {}
            chunk_obj_map: Dict[Any, Dict[str, Any]] = {}
            
            for q_hits in query_hits_lists:
                for rank, hit in enumerate(q_hits):
                    cid = hit["chunk_id"]
                    rrf_score = 1.0 / (rrf_k + rank + 1)
                    chunk_rrf_scores[cid] = chunk_rrf_scores.get(cid, 0.0) + rrf_score
                    if cid not in chunk_obj_map or hit["score"] > chunk_obj_map[cid]["score"]:
                        chunk_obj_map[cid] = hit
                        
            # Assign RRF-fused score to merged hits
            fused_hits = []
            for cid, rrf_sc in chunk_rrf_scores.items():
                hit_item = dict(chunk_obj_map[cid])
                # Boost chunk score with RRF fused score
                hit_item["score"] = round(hit_item["score"] + rrf_sc, 4)
                fused_hits.append(hit_item)
                
            fused_hits.sort(key=lambda x: x["score"], reverse=True)
            raw_hits = fused_hits[:retrieval_limit]
            
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
                retry_query = question
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
                "document_name": doc_id_to_name.get(doc_id, "Unknown"),
                "page_number": hit["page_number"],
                "chunk_text": hit["chunk_text"],
                "score": hit["score"]
            })
            
        context_compression = context_compressor.compress(retrieval_query, full_raw_hits)
        
        # Only compressed context is passed to LLM Prompt Builder
        graph_retrieved_map = {str(hit["chunk_id"]): hit.get("is_graph_retrieved", False) for hit in raw_hits}
        context_chunks = []
        for cc in context_compression.compressed_chunks:
            cid_str = str(cc.chunk_id)
            context_chunks.append({
                "chunk_id": cc.chunk_id,
                "document_id": cc.document_id,
                "document_name": cc.document_name,
                "page_number": cc.page_number,
                "chunk_text": cc.chunk_text,
                "score": cc.score,
                "is_graph_retrieved": graph_retrieved_map.get(cid_str, False)
            })
    except Exception as e:
        logger.error(f"Context compression failed: {e}", exc_info=True)
        # Fallback logic
        context_chunks = []
        for hit in raw_hits:
            doc_id = hit["document_id"]
            context_chunks.append({
                "chunk_id": hit["chunk_id"],
                "document_id": doc_id,
                "document_name": doc_id_to_name.get(doc_id, "Unknown"),
                "page_number": hit["page_number"],
                "chunk_text": hit["chunk_text"],
                "score": hit["score"],
                "is_graph_retrieved": hit.get("is_graph_retrieved", False)
            })

    # Call LLM service to compile prompts, call Gemini, and format grounding outputs
    res = llm_service.generate_answer(question, context_chunks)

    # Run Hallucination Detection
    hallucination_detection = None
    try:
        from app.services.hallucination_detector import hallucination_detector as detector_service
        hallucination_detection = detector_service.detect(question, context_chunks, res["answer"])
        if hallucination_detection.hallucination_status in ["WARNING", "FAILED"]:
            logger.warning(
                f"Hallucination detection alert for query '{question}': Status: {hallucination_detection.hallucination_status} | "
                f"Confidence: {hallucination_detection.confidence_score:.2f} | Reasoning: {hallucination_detection.reasoning}"
            )
    except Exception as e:
        logger.error(f"Hallucination detection failed: {e}", exc_info=True)

    # Run Answer Verification
    answer_verification = None
    try:
        from app.services.answer_verifier import answer_verifier
        answer_verification = answer_verifier.verify(res["answer"], context_chunks)
    except Exception as e:
        logger.error(f"Answer verification failed: {e}", exc_info=True)

    # Run Self Reflection
    self_reflection = None
    try:
        from app.services.self_reflector import self_reflector
        self_reflection = self_reflector.reflect(
            question, 
            res["answer"], 
            context_chunks, 
            hallucination_detection, 
            answer_verification
        )
    except Exception as e:
        logger.error(f"Self reflection failed: {e}", exc_info=True)

    final_answer = res["answer"]
    if self_reflection and self_reflection.refinement_performed and self_reflection.refined_answer:
        final_answer = self_reflection.refined_answer

    # Format output citations conforming strictly to Citation schema
    citations = []
    for source in res["sources"]:
        citations.append(
            Citation(
                document_name=source["document_name"],
                page_number=source["page_number"],
                chunk_index=source["chunk_index"],
                chunk_text=source["chunk_text"]
            )
        )

    # Run Confidence Scoring
    confidence = None
    try:
        from app.services.confidence_engine import confidence_engine
        confidence = confidence_engine.compute_confidence(
            final_answer,
            citations,
            retrieval_verification,
            reranking,
            hallucination_detection,
            answer_verification,
            self_reflection
        )
    except Exception as e:
        logger.error(f"Confidence scoring failed: {e}", exc_info=True)

    # Run RAG Evaluation
    evaluation = None
    try:
        from app.services.evaluation_engine import evaluation_engine
        evaluation = evaluation_engine.evaluate_response(
            question=question,
            answer=final_answer,
            citations=citations,
            context_chunks=context_chunks,
            pipeline_outputs={
                "hallucination_detection": hallucination_detection,
                "answer_verification": answer_verification,
                "confidence": confidence
            }
        )
    except Exception as e:
        logger.error(f"RAG evaluation failed: {e}", exc_info=True)

    return {
        "answer": final_answer,
        "citations": citations,
        "query_analysis": analysis,
        "query_rewrite": query_rewrite,
        "adaptive_retrieval": adaptive_retrieval,
        "retrieval_verification": retrieval_verification,
        "reranking": reranking,
        "hallucination_detection": hallucination_detection,
        "hybrid_retrieval": hybrid_retrieval,
        "query_transformation": query_transformation,
        "context_compression": context_compression,
        "answer_verification": answer_verification,
        "self_reflection": self_reflection,
        "confidence": confidence,
        "evaluation": evaluation
    }

