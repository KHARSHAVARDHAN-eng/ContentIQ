import json
import re
import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import google.generativeai as genai

from app.core.config import settings
from app.models.chat_history import ChatMessage
from app.schemas.query_analysis import QueryAnalysis
from app.schemas.query_transformation import QueryTransformationResult
from app.services.query_analyzer import query_analyzer
from app.services.query_rewriter import query_rewriter

logger = logging.getLogger("app.services.query_transformation")

class QueryTransformationService:
    def transform(
        self,
        query: str,
        session_id: Optional[int] = None,
        db: Optional[Session] = None
    ) -> QueryTransformationResult:
        start_time = time.time()
        cleaned_query = query.strip()
        
        if not settings.QUERY_TRANSFORMATION_ENABLED:
            logger.info("Query Transformation is disabled. Bypassing engine.")
            analysis = query_analyzer.analyze(cleaned_query)
            return QueryTransformationResult(
                original_query=cleaned_query,
                rewritten_query=cleaned_query,
                expanded_queries=[],
                generated_retrieval_queries=[cleaned_query],
                query_intent=analysis.intent,
                ambiguity_score=analysis.ambiguity_score or 0.0,
                confidence_score=1.0,
                detected_entities=analysis.detected_entities or [],
                detected_keywords=analysis.keywords or [],
                transformation_metadata={"bypassed": True}
            )

        # 1. Conversation Context Resolution
        resolved_query = cleaned_query
        history_msgs = []
        if session_id and db:
            try:
                # Load last 6 messages (alternating user/bot) from history
                history_msgs = db.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).order_by(ChatMessage.created_at.desc()).limit(6).all()
                # Reverse to keep chronological order
                history_msgs.reverse()
            except Exception as e:
                logger.error(f"Failed to fetch conversation history: {e}", exc_info=True)

        if history_msgs:
            resolved_query = self._resolve_conversation_context(cleaned_query, history_msgs)
            if resolved_query != cleaned_query:
                logger.info(f"Resolved follow-up query: '{cleaned_query}' -> '{resolved_query}'")

        # 2. Query Analysis
        analysis = query_analyzer.analyze(resolved_query)

        # 3. Query Rewriting
        rewritten_query = resolved_query
        rewrite_applied = False
        rewrite_reason = "Rewriter bypassed or disabled."
        
        if settings.QUERY_REWRITE_ENABLED:
            try:
                rewrite_result = query_rewriter.rewrite(analysis)
                if rewrite_result.rewrite_applied:
                    rewritten_query = rewrite_result.rewritten_query
                    rewrite_applied = True
                    rewrite_reason = rewrite_result.rewrite_reason
            except Exception as e:
                logger.error(f"Query rewriting sub-phase failed: {e}", exc_info=True)

        # 4. Query Expansion
        expanded_queries = []
        if settings.QUERY_EXPANSION_ENABLED:
            expanded_queries = self._expand_query(rewritten_query)

        # 5. Multi-Query Formulation
        generated_retrieval_queries = [rewritten_query]
        if settings.MULTI_QUERY_ENABLED:
            for eq in expanded_queries:
                if eq not in generated_retrieval_queries:
                    generated_retrieval_queries.append(eq)
            # Limit queries based on max configured setting
            generated_retrieval_queries = generated_retrieval_queries[:settings.MAX_GENERATED_QUERIES]

        latency_ms = int((time.time() - start_time) * 1000)

        # Build transformation metadata dict
        metadata = {
            "resolved_conversation": resolved_query != cleaned_query,
            "resolved_query": resolved_query,
            "rewrite_applied": rewrite_applied,
            "rewrite_reason": rewrite_reason,
            "latency_ms": latency_ms,
            "ambiguity_threshold_triggered": (analysis.ambiguity_score or 0.0) >= settings.AMBIGUITY_THRESHOLD
        }

        result = QueryTransformationResult(
            original_query=cleaned_query,
            rewritten_query=rewritten_query,
            expanded_queries=expanded_queries,
            generated_retrieval_queries=generated_retrieval_queries,
            query_intent=analysis.intent,
            ambiguity_score=analysis.ambiguity_score or 0.0,
            confidence_score=round(analysis.intent_confidence, 2),
            detected_entities=analysis.detected_entities or [],
            detected_keywords=analysis.keywords or [],
            transformation_metadata=metadata
        )

        if settings.QUERY_TRANSFORMATION_DEBUG:
            logger.info(
                f"\n=== QUERY TRANSFORMATION REPORT ===\n"
                f"Original Query: '{result.original_query}'\n"
                f"Resolved Query: '{resolved_query}'\n"
                f"Rewritten Query: '{result.rewritten_query}' (applied={rewrite_applied})\n"
                f"Expanded Queries: {result.expanded_queries}\n"
                f"Final Search Candidates: {result.generated_retrieval_queries}\n"
                f"Ambiguity Score: {result.ambiguity_score} (Triggered?: {metadata['ambiguity_threshold_triggered']})\n"
                f"Entities: {result.detected_entities}\n"
                f"Intent: {result.query_intent} | Latency: {latency_ms} ms\n"
                f"===================================="
            )

        return result

    def _resolve_conversation_context(self, query: str, history_msgs: List[ChatMessage]) -> str:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return self._fallback_resolve_history(query, history_msgs)

        try:
            genai.configure(api_key=api_key)
            formatted_history = []
            for msg in history_msgs:
                role = "User" if msg.sender == "user" else "Assistant"
                formatted_history.append(f"{role}: {msg.text}")
            history_str = "\n".join(formatted_history)

            system_instruction = (
                "You are a conversational query resolution agent. Your task is to resolve any pronouns (like 'it', 'this', 'that', 'they'), abbreviations, or context gaps in the latest query to formulate a standalone search query.\n"
                "You will receive the conversation history and the latest user query.\n"
                "Return a JSON object with a single field 'resolved_query'.\n"
                "If the query is already standalone and does not rely on conversation context, return the original query as 'resolved_query'."
            )

            model = genai.GenerativeModel(
                model_name=settings.QUERY_ANALYZER_MODEL,
                system_instruction=system_instruction
            )

            prompt = f"Chat History:\n{history_str}\n\nLatest Query: '{query}'"
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )

            if response and response.text:
                data = json.loads(response.text.strip())
                return data.get("resolved_query", query).strip()
            return self._fallback_resolve_history(query, history_msgs)
        except Exception as e:
            logger.warning(f"LLM conversation resolution failed: {e}. Falling back to rule-based.")
            return self._fallback_resolve_history(query, history_msgs)

    def _fallback_resolve_history(self, query: str, history_msgs: List[ChatMessage]) -> str:
        # Find a topic from recent history messages (from bot or user)
        # Search for key terms to resolve "it", "this", "they", "them", "that"
        topic = None
        for msg in reversed(history_msgs):
            text = msg.text.lower()
            for term in ["hybrid retrieval", "cross-encoder", "reranking", "adaptive chunking", "hallucination", "rag", "qdrant", "vector store", "easyocr", "ocr"]:
                if term in text:
                    topic = term
                    break
            if topic:
                break

        if topic:
            # Title-case the topic for cleaner queries
            topic_capitalized = " ".join(w.capitalize() for w in topic.split())
            lower_q = query.lower()
            if "how does it work" in lower_q:
                return f"How does {topic_capitalized} work?"
            if "explain it" in lower_q:
                return f"Explain {topic_capitalized}"
            if "what is it" in lower_q:
                return f"What is {topic_capitalized}?"
            # Simple replacement of pronouns if it occurs at the end or standalone
            resolved = re.sub(r'\b(it|this|that)\b', topic_capitalized, query, flags=re.IGNORECASE)
            return resolved

        return query

    def _expand_query(self, query: str) -> List[str]:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return self._fallback_expand_query(query)

        try:
            genai.configure(api_key=api_key)
            system_instruction = (
                "You are a query expansion assistant. Generate exactly 2-3 alternative search query variations or synonyms for the given query to improve retrieval recall.\n"
                "Return a JSON object with a single field 'variations' containing a list of strings.\n"
                "Adhere strictly to valid JSON format."
            )

            model = genai.GenerativeModel(
                model_name=settings.QUERY_ANALYZER_MODEL,
                system_instruction=system_instruction
            )

            response = model.generate_content(
                f"Generate variations for: '{query}'",
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.QUERY_ANALYZER_TEMPERATURE,
                    response_mime_type="application/json"
                )
            )

            if response and response.text:
                data = json.loads(response.text.strip())
                variations = data.get("variations", [])
                if isinstance(variations, list):
                    return [str(v).strip() for v in variations if v]
            return self._fallback_expand_query(query)
        except Exception as e:
            logger.warning(f"LLM query expansion failed: {e}. Falling back to rule-based.")
            return self._fallback_expand_query(query)

    def _fallback_expand_query(self, query: str) -> List[str]:
        lower_q = query.lower()
        expansions = []

        synonyms = {
            "vector database": ["embedding database", "semantic search database", "Qdrant vector database"],
            "hybrid retrieval": ["hybrid dense sparse search", "BM25 vector search retrieval", "hybrid search retrieval"],
            "rag": ["retrieval-augmented generation", "rag search", "knowledge base retrieval"],
            "cross-encoder": ["cross encoder reranker", "ms-marco cross encoder reranking", "reranking relevance score"],
            "hallucination": ["hallucination detection", "grounding check validation", "unsupported claim detection"],
            "chunking": ["adaptive chunking engine", "document text split hierarchical", "paragraph heading hierarchy chunking"]
        }

        for kw, variations in synonyms.items():
            if kw in lower_q:
                expansions.extend(variations)

        # If no synonyms matched, generate some simple keyword variations
        if not expansions:
            words = [w.strip("?,.!") for w in query.split() if len(w) > 3]
            if len(words) >= 2:
                expansions.append(f"{words[0]} {words[1]}")

        return expansions

query_transformer = QueryTransformationService()
