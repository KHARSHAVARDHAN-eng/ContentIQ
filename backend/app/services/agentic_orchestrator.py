import time
import logging
import re
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import google.generativeai as genai

from app.core.config import settings
from app.models.document import Document
from app.schemas.agentic_rag import AgenticRAGResult, AgentStep
from app.schemas.chat import Citation
from app.services.llm_service import llm_service

logger = logging.getLogger("app.services.agentic_orchestrator")

STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how', 'why', 'who', 
    'where', 'when', 'to', 'of', 'in', 'and', 'or', 'for', 'on', 'with', 'at', 
    'by', 'about', 'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 
    'their', 'you', 'your', 'i', 'my', 'me', 'we', 'us', 'our', 'be', 'been', 'have', 'has'
}

class AgenticRAGOrchestrator:
    def execute_agentic_flow(
        self,
        db: Session,
        question: str,
        session_id: Optional[int],
        current_user: Any,
        agentic_enabled: bool = True
    ) -> Dict[str, Any]:
        overall_start_time = time.time()
        steps: List[AgentStep] = []

        # Retrieve all documents owned by the logged-in user to enforce security boundary
        user_docs = db.query(Document).filter(Document.user_id == current_user.id).all()
        user_doc_ids = [doc.id for doc in user_docs]
        doc_id_to_name = {doc.id: doc.name for doc in user_docs}

        # 1. Planning Stage
        analysis = None
        query_rewrite = None
        query_transformation = None
        retrieval_query = question

        try:
            from app.services.query_transformation import query_transformer
            query_transformation = query_transformer.transform(question, session_id, db)
            
            from app.services.query_analyzer import query_analyzer
            from app.services.query_rewriter import query_rewriter
            resolved_q = query_transformation.transformation_metadata.get("resolved_query", question)
            analysis = query_analyzer.analyze(resolved_q)
            query_rewrite = query_rewriter.rewrite(analysis)
            retrieval_query = query_transformation.rewritten_query
        except Exception as e:
            logger.error(f"Agentic Planner failed: {e}", exc_info=True)

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

        steps.append(
            AgentStep(
                step_index=len(steps) + 1,
                action="PLANNING",
                thought=f"Initialized RAG reasoning path. Query: '{retrieval_query}'. Retrieval limit: {retrieval_limit}.",
                query=retrieval_query,
                retrieved_chunk_ids=[],
                latency_ms=0
            )
        )

        # 2. Execution Loop
        all_context_chunks: List[Dict[str, Any]] = []
        seen_chunk_ids = set()
        
        # Capture raw retrieval steps outputs for final response schemas
        first_retrieval_verification = None
        first_reranking = None
        first_hybrid_retrieval = None
        first_context_compression = None

        loop_prevented = False
        max_attempts = settings.AGENTIC_MAX_RETRIEVAL_ATTEMPTS

        for attempt in range(1, max_attempts + 1):
            loop_start = time.time()
            
            # Hybrid search
            raw_hits = []
            hybrid_retrieval = None
            if user_doc_ids:
                try:
                    from app.services.hybrid_retriever import hybrid_retriever
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
                        if q_idx == 0 and attempt == 1:
                            first_hybrid_retrieval = hr
                            
                    all_hits.sort(key=lambda x: x["score"], reverse=True)
                    deduped_hits = []
                    for h in all_hits:
                        cid = h["chunk_id"]
                        if cid not in seen_chunks:
                            seen_chunks.add(cid)
                            deduped_hits.append(h)
                    raw_hits = deduped_hits[:retrieval_limit]
                except Exception as e:
                    logger.error(f"Search failed: {e}")

            # Retrieval Verification
            retrieval_verification = None
            try:
                from app.services.retrieval_verifier import retrieval_verifier
                verification_result = retrieval_verifier.verify(raw_hits, retrieval_query)
                
                # Check for retry
                if verification_result.verification_status == "FAIL" and settings.RETRIEVAL_VERIFIER_ENABLED:
                    verification_result.first_attempt_status = "FAIL"
                    verification_result.first_attempt_score = verification_result.quality_score
                    verification_result.retry_performed = True
                    
                    retry_strategy = settings.RETRIEVAL_VERIFIER_RETRY_STRATEGY.lower()
                    retry_limit = retrieval_limit
                    retry_query = retrieval_query
                    
                    if retry_strategy == "expand_limit":
                        retry_limit = retrieval_limit * 2
                    elif retry_strategy == "raw_query":
                        retry_query = question
                        
                    retried_hits = []
                    if user_doc_ids:
                        retried_hits, retry_hybrid = hybrid_retriever.search(
                            db=db,
                            query=retry_query,
                            user_doc_ids=user_doc_ids,
                            limit=retry_limit
                        )
                    
                    retry_verify_result = retrieval_verifier.verify(retried_hits, retry_query)
                    verification_result.verification_status = retry_verify_result.verification_status
                    verification_result.quality_score = retry_verify_result.quality_score
                    verification_result.retrieval_confidence = retry_verify_result.retrieval_confidence
                    verification_result.verification_reason = f"Retry result: {retry_verify_result.verification_status}"
                    verification_result.recommended_action = retry_verify_result.recommended_action
                    raw_hits = retried_hits
                    
                retrieval_verification = verification_result
                if attempt == 1:
                    first_retrieval_verification = retrieval_verification
            except Exception as e:
                logger.error(f"Verification failed: {e}")

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

            # Reranker
            reranking = None
            try:
                from app.services.reranker import reranker as reranker_service
                raw_hits, reranking = reranker_service.rerank(retrieval_query, raw_hits, retrieval_verification)
                if attempt == 1:
                    first_reranking = reranking
            except Exception as e:
                logger.error(f"Reranking failed: {e}")

            # Compressor
            context_chunks = []
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
                if attempt == 1:
                    first_context_compression = context_compression

                for cc in context_compression.compressed_chunks:
                    context_chunks.append({
                        "chunk_id": cc.chunk_id,
                        "document_id": cc.document_id,
                        "document_name": cc.document_name,
                        "page_number": cc.page_number,
                        "chunk_text": cc.chunk_text,
                        "score": cc.score
                    })
            except Exception as e:
                logger.error(f"Compression failed: {e}")
                # Fallback
                for hit in raw_hits:
                    doc_id = hit["document_id"]
                    context_chunks.append({
                        "chunk_id": hit["chunk_id"],
                        "document_id": doc_id,
                        "document_name": doc_id_to_name.get(doc_id, "Unknown"),
                        "page_number": hit["page_number"],
                        "chunk_text": hit["chunk_text"],
                        "score": hit["score"]
                    })

            # Merge and deduplicate context chunks
            new_chunk_ids = []
            for chunk in context_chunks:
                cid = chunk["chunk_id"]
                new_chunk_ids.append(cid)
                if cid not in seen_chunk_ids:
                    seen_chunk_ids.add(cid)
                    all_context_chunks.append(chunk)

            # Evaluate context completeness/sufficiency
            sufficiency_score = 1.0
            refined_query = ""
            sufficient = True

            q_words = set(re.findall(r'\b\w+\b', retrieval_query.lower())) - STOPWORDS
            retrieved_text = " ".join([c["chunk_text"].lower() for c in all_context_chunks])
            
            if q_words:
                matched = {w for w in q_words if w in retrieved_text}
                sufficiency_score = len(matched) / len(q_words)
            else:
                sufficiency_score = 1.0

            # Dynamic LLM evaluation if settings permit and API key is valid
            api_key = settings.GEMINI_API_KEY
            if api_key and len(all_context_chunks) > 0:
                try:
                    sufficient, sufficiency_score, refined_query = self._evaluate_with_llm(
                        question, all_context_chunks, retrieval_query, attempt, api_key
                    )
                except Exception as ex:
                    logger.warning(f"LLM sufficiency evaluation failed: {ex}. Falling back to rules.")
                    sufficient = sufficiency_score >= settings.AGENTIC_EVALUATION_THRESHOLD
                    if not sufficient:
                        missing = q_words - matched
                        refined_query = f"{retrieval_query} {' '.join(missing)}"
            else:
                sufficient = sufficiency_score >= settings.AGENTIC_EVALUATION_THRESHOLD
                if not sufficient:
                    missing = q_words - matched
                    refined_query = f"{retrieval_query} {' '.join(missing)}"

            latency_ms = int((time.time() - loop_start) * 1000)

            steps.append(
                AgentStep(
                    step_index=len(steps) + 1,
                    action="RETRIEVAL_ATTEMPT",
                    thought=f"Attempt {attempt}: Retrieved {len(context_chunks)} chunks. Sufficiency score: {sufficiency_score:.2f}.",
                    query=retrieval_query,
                    retrieved_chunk_ids=new_chunk_ids,
                    evaluation_score=sufficiency_score,
                    latency_ms=latency_ms
                )
            )

            # Termination condition
            if sufficient or attempt == max_attempts:
                break
            
            # Loop Prevention / Redundant Query check
            if refined_query.strip().lower() == retrieval_query.strip().lower():
                logger.info("Refined query is identical to previous query. Loop prevented.")
                loop_prevented = True
                break

            retrieval_query = refined_query

        # 3. Answer Generation & Upstream Engines Pipeline
        # RAG Prompt construction with merged context chunks
        context_text = "\n\n".join([
            f"Document: {c['document_name']} (Page {c['page_number']})\nSnippet: {c['chunk_text']}"
            for c in all_context_chunks
        ])
        
        # Call LLM to generate standard answer
        res = llm_service.generate_answer(question, all_context_chunks)

        # Hallucination Detection
        hallucination_detection = None
        try:
            from app.services.hallucination_detector import hallucination_detector as detector_service
            hallucination_detection = detector_service.detect(question, all_context_chunks, res["answer"])
        except Exception as e:
            logger.error(f"Hallucination detection failed: {e}")

        # Answer Verification
        answer_verification = None
        try:
            from app.services.answer_verifier import answer_verifier
            answer_verification = answer_verifier.verify(res["answer"], all_context_chunks)
        except Exception as e:
            logger.error(f"Answer verification failed: {e}")

        # Self Reflection
        self_reflection = None
        try:
            from app.services.self_reflector import self_reflector
            self_reflection = self_reflector.reflect(
                question, 
                res["answer"], 
                all_context_chunks, 
                hallucination_detection, 
                answer_verification
            )
        except Exception as e:
            logger.error(f"Self reflection failed: {e}")

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

        # Confidence Scoring
        confidence = None
        try:
            from app.services.confidence_engine import confidence_engine
            confidence = confidence_engine.compute_confidence(
                final_answer,
                citations,
                first_retrieval_verification,
                first_reranking,
                hallucination_detection,
                answer_verification,
                self_reflection
            )
        except Exception as e:
            logger.error(f"Confidence scoring failed: {e}")

        # RAG Evaluation
        evaluation = None
        try:
            from app.services.evaluation_engine import evaluation_engine
            evaluation = evaluation_engine.evaluate_response(
                question=question,
                answer=final_answer,
                citations=citations,
                context_chunks=all_context_chunks,
                pipeline_outputs={
                    "hallucination_detection": hallucination_detection,
                    "answer_verification": answer_verification,
                    "confidence": confidence
                }
            )
        except Exception as e:
            logger.error(f"RAG evaluation failed: {e}")

        # Formulate Agentic Result
        reasoning_path = " -> ".join([s.action for s in steps]) + " -> SYNTHESIS"
        agentic_rag = AgenticRAGResult(
            agent_enabled=agentic_enabled,
            total_steps=len(steps),
            steps=steps,
            reasoning_path=reasoning_path,
            merged_context_chunks_count=len(all_context_chunks),
            loop_prevented=loop_prevented,
            metadata={"overall_latency_ms": int((time.time() - overall_start_time) * 1000)}
        )

        return {
            "answer": final_answer,
            "citations": citations,
            "query_analysis": analysis,
            "query_rewrite": query_rewrite,
            "adaptive_retrieval": adaptive_retrieval,
            "retrieval_verification": first_retrieval_verification,
            "reranking": first_reranking,
            "hallucination_detection": hallucination_detection,
            "hybrid_retrieval": first_hybrid_retrieval,
            "query_transformation": query_transformation,
            "context_compression": first_context_compression,
            "answer_verification": answer_verification,
            "self_reflection": self_reflection,
            "confidence": confidence,
            "evaluation": evaluation,
            "agentic_rag": agentic_rag,
            "context_chunks": all_context_chunks  # For test assertions and verification
        }

    def _evaluate_with_llm(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        current_query: str,
        attempt: int,
        api_key: str
    ) -> tuple:
        genai.configure(api_key=api_key)
        context_serialized = "\n".join([f"- Chunk {c.get('chunk_id')}: {c.get('chunk_text')}" for c in context_chunks])

        system_instruction = (
            "You are an expert RAG evaluator. Assess whether the retrieved context chunks contain sufficient details "
            "to answer the question completely.\n"
            "If yes, return a JSON object:\n"
            "{\n"
            "  'sufficient': true,\n"
            "  'sufficiency_score': 1.0,\n"
            "  'refined_query': ''\n"
            "}\n"
            "If no, return a JSON object:\n"
            "{\n"
            "  'sufficient': false,\n"
            "  'sufficiency_score': float (between 0.0 and 0.74),\n"
            "  'refined_query': str (a highly targeted refined keyword query to fetch the missing details from search indexes)\n"
            "}"
        )

        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_instruction
        )

        prompt = (
            f"QUESTION: {question}\n\n"
            f"CURRENT RETRIEVED CONTEXT:\n{context_serialized}\n\n"
            f"CURRENT RETRIEVED QUERY: {current_query}\n"
            f"ATTEMPT: {attempt}"
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )

        if response and response.text:
            data = json.loads(response.text.strip())
            return (
                bool(data.get("sufficient", True)),
                float(data.get("sufficiency_score", 1.0)),
                str(data.get("refined_query", ""))
            )

        raise ValueError("Empty response from RAG evaluator API")

agentic_orchestrator = AgenticRAGOrchestrator()
