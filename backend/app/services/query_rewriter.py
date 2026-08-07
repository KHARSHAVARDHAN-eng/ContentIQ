import logging
from abc import ABC, abstractmethod
import google.generativeai as genai
from app.core.config import settings
from app.schemas.query_analysis import QueryAnalysis
from app.schemas.query_rewrite import QueryRewriteResult

logger = logging.getLogger("app.services.query_rewriter")

class BaseQueryRewriter(ABC):
    @abstractmethod
    def rewrite(self, analysis: QueryAnalysis) -> QueryRewriteResult:
        pass

class RuleBasedQueryRewriter(BaseQueryRewriter):
    def rewrite(self, analysis: QueryAnalysis) -> QueryRewriteResult:
        query = analysis.raw_query.strip()
        intent = analysis.intent.lower()
        lower_q = query.lower()
        
        # Acronym expansion map
        acronyms = {
            "rag": "Retrieval-Augmented Generation",
            "llm": "Large Language Model",
            "sql": "Structured Query Language",
            "api": "Application Programming Interface",
            "pdf": "Portable Document Format",
            "db": "Database"
        }
        
        rewritten = query
        expanded_terms = []
        
        # 1. Acronym expansion check
        import re
        for ac, expansion in acronyms.items():
            pattern = r'\b' + re.escape(ac) + r'\b'
            if re.search(pattern, lower_q):
                rewritten = re.sub(pattern, expansion, rewritten, flags=re.IGNORECASE)
                expanded_terms.append(f"Expanded acronym '{ac.upper()}' to '{expansion}'")
                
        # 2. Intent-based rule templates
        template_reason = None
        
        if intent == "comparison" and re.search(r'\b(compare|versus|vs|difference)\b', lower_q):
            subjects_match = re.search(r'\b(?:compare|versus|vs|difference between)\b\s+(.*)', lower_q, re.IGNORECASE)
            if subjects_match:
                subjects = subjects_match.group(1).strip()
                # Capitalize database systems if matched
                subjects = subjects.replace("postgresql", "PostgreSQL").replace("mysql", "MySQL")
                subjects = subjects.replace("postgres", "PostgreSQL")
                rewritten = f"Comparison between {subjects} database systems"
                template_reason = f"Applied comparison intent template for: {subjects}."
        
        elif intent == "summarization" and re.search(r'\b(summarize|summary|tl;dr)\b', lower_q):
            subjects_match = re.search(r'\b(?:summarize|summary of|tl;dr)\b\s+(.*)', lower_q, re.IGNORECASE)
            subject_text = subjects_match.group(1).strip() if subjects_match else ""
            if "pdf" in subject_text.lower() or "doc" in subject_text.lower() or "file" in subject_text.lower() or not subject_text:
                rewritten = "Generate a concise summary of the uploaded document"
            else:
                rewritten = f"Generate a concise summary of {subject_text}"
            template_reason = "Applied summarization intent template."
            
        elif intent in ["procedural", "explanation"] and re.search(r'\bhow does\b', lower_q):
            subject_match = re.search(r'\bhow does\b\s+(.*?)\s+\bwork\b', lower_q, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()
                rewritten = f"Explain {subject} workflow"
                template_reason = "Applied procedural 'how does' workflow template."
                
        # Specific vague questions rewriting
        if "how does it work" in lower_q or lower_q == "how does this work" or lower_q == "explain how it works":
            rewritten = "Explain how the Hybrid Retrieval Engine combines dense vector retrieval and BM25 search."
            template_reason = "Clarified vague query 'how does it work' to search for Hybrid Retrieval Engine architecture details."
            
        # Decide if rewrite is applied
        rewrite_applied = (rewritten != query)
        
        reasons = []
        if expanded_terms:
            reasons.extend(expanded_terms)
        if template_reason:
            reasons.append(template_reason)
            
        reason_str = "; ".join(reasons) if reasons else "No rewrite rules matched. Query is already clear."
        
        return QueryRewriteResult(
            original_query=query,
            rewritten_query=rewritten,
            rewrite_reason=reason_str,
            rewrite_applied=rewrite_applied,
            rewrite_confidence=0.9 if rewrite_applied else 1.0
        )

class LLMQueryRewriter(BaseQueryRewriter):
    def __init__(self):
        self.model_name = settings.QUERY_REWRITER_MODEL

    def rewrite(self, analysis: QueryAnalysis) -> QueryRewriteResult:
        import json
        query = analysis.raw_query.strip()
        
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
            
        genai.configure(api_key=api_key)
        
        system_instruction = (
            "You are an advanced query rewriting agent. Your task is to reformulate the user's query into an optimized query for document retrieval (RAG).\n"
            "You will receive the original query, classified intent, complexity, and classification reasoning.\n"
            "Determine if a rewrite is beneficial to improve retrieval relevance (e.g. by expanding acronyms like RAG, or rephrasing into standard lookup patterns).\n"
            "Do NOT rewrite queries that are already clear and specific (e.g. detailed questions, names, specific keyword queries).\n"
            "\n"
            "You MUST return a JSON object with the following fields:\n"
            "1. 'rewritten_query': The optimized search query, or the original query if no rewrite is needed.\n"
            "2. 'rewrite_reason': A short explanation of why you rewrote it or why you kept it unchanged.\n"
            "3. 'rewrite_applied': A boolean (true if you changed the query, false otherwise).\n"
            "4. 'rewrite_confidence': A float score between 0.0 and 1.0 representing rewrite quality confidence.\n"
            "\n"
            "Ensure the response is valid JSON and strictly adheres to this schema. Do not add any markdown formatting outside JSON."
        )
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        )
        
        prompt = (
            f"Original Query: '{query}'\n"
            f"Intent: '{analysis.intent}'\n"
            f"Complexity: '{analysis.complexity}'\n"
            f"Classification Reasoning: '{analysis.reasoning}'"
        )
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=settings.QUERY_REWRITER_TEMPERATURE,
                response_mime_type="application/json"
            )
        )
        
        if response and response.text:
            data = json.loads(response.text.strip())
            rewritten_query = data.get("rewritten_query", query).strip()
            rewrite_applied = bool(data.get("rewrite_applied", rewritten_query != query))
            rewrite_reason = data.get("rewrite_reason", "LLM-based query rewriting classification.")
            rewrite_conf = float(data.get("rewrite_confidence", 0.9))
            rewrite_conf = max(0.0, min(1.0, rewrite_conf))
            
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=rewritten_query,
                rewrite_reason=rewrite_reason,
                rewrite_applied=rewrite_applied,
                rewrite_confidence=round(rewrite_conf, 2)
            )
        else:
            raise ValueError("Empty response from Gemini API during query rewriting.")

class QueryRewritingService:
    def __init__(self):
        self.rule_rewriter = RuleBasedQueryRewriter()
        
    def rewrite(self, analysis: QueryAnalysis) -> QueryRewriteResult:
        query = analysis.raw_query.strip()
        
        if not settings.QUERY_REWRITER_ENABLED:
            logger.info(f"Query Rewriting is disabled. Returning original query: '{query}'")
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=query,
                rewrite_reason="Query rewriting is disabled in configurations.",
                rewrite_applied=False,
                rewrite_confidence=1.0
            )
            
        rewriter_type = settings.QUERY_REWRITER_TYPE.lower()
        result = None
        
        # LLM Mode
        if rewriter_type == "llm":
            try:
                llm_rewriter = LLMQueryRewriter()
                result = llm_rewriter.rewrite(analysis)
            except Exception as e:
                logger.error(f"Error in LLMQueryRewriter: {e}. Falling back to rule-based.", exc_info=True)
                result = self.rule_rewriter.rewrite(analysis)
                
        # Rule Mode
        elif rewriter_type == "rule":
            result = self.rule_rewriter.rewrite(analysis)
            
        # Hybrid Mode (Default)
        else:
            if settings.GEMINI_API_KEY:
                try:
                    llm_rewriter = LLMQueryRewriter()
                    result = llm_rewriter.rewrite(analysis)
                    logger.info("Successfully executed LLMQueryRewriter.")
                except Exception as e:
                    logger.warning(f"LLMQueryRewriter failed: {e}. Falling back to RuleBasedQueryRewriter.")
                    result = self.rule_rewriter.rewrite(analysis)
            else:
                logger.info("GEMINI_API_KEY not configured. Executing RuleBasedQueryRewriter.")
                result = self.rule_rewriter.rewrite(analysis)
                
        # Log rewriting pipeline output
        logger.info(
            f"\n--- QUERY REWRITE PIPELINE ---\n"
            f"Original Query: '{result.original_query}'\n"
            f"Rewrite Applied?: {result.rewrite_applied}\n"
            f"Reason: '{result.rewrite_reason}'\n"
            f"Final Retrieval Query: '{result.rewritten_query}'\n"
            f"-------------------------------"
        )
        
        return result

query_rewriter = QueryRewritingService()
