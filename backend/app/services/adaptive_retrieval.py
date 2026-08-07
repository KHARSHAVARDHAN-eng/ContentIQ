import logging
from abc import ABC, abstractmethod
from typing import Optional
import google.generativeai as genai
from app.core.config import settings
from app.schemas.query_analysis import QueryAnalysis
from app.schemas.query_rewrite import QueryRewriteResult
from app.schemas.adaptive_retrieval import AdaptiveRetrievalResult

logger = logging.getLogger("app.services.adaptive_retrieval")

class BaseAdaptiveRetrievalPolicy(ABC):
    @abstractmethod
    def determine_strategy(
        self, 
        analysis: QueryAnalysis, 
        rewrite_result: Optional[QueryRewriteResult] = None
    ) -> AdaptiveRetrievalResult:
        pass

class RulesBasedAdaptiveRetrievalPolicy(BaseAdaptiveRetrievalPolicy):
    def determine_strategy(
        self, 
        analysis: QueryAnalysis, 
        rewrite_result: Optional[QueryRewriteResult] = None
    ) -> AdaptiveRetrievalResult:
        intent = analysis.intent.lower()
        complexity = analysis.complexity.lower()
        
        strategy = "standard_retrieval"
        top_k = settings.ADAPTIVE_RETRIEVAL_DEFAULT_TOP_K
        reason = "Default standard retrieval strategy."
        confidence = min(analysis.intent_confidence, analysis.complexity_confidence)
        
        # Match combinations
        if complexity == "simple" and intent == "factual":
            top_k = settings.ADAPTIVE_RETRIEVAL_SIMPLE_FACTUAL_TOP_K
            strategy = "simple_factual"
            reason = f"Simple factual query requires compact retrieval (Top-{top_k} chunks)."
        elif complexity == "medium" and intent == "explanation":
            top_k = settings.ADAPTIVE_RETRIEVAL_MEDIUM_EXPLANATION_TOP_K
            strategy = "medium_explanation"
            reason = f"Medium explanation query requires standard explanatory context (Top-{top_k} chunks)."
        elif complexity == "complex" and intent == "analytical":
            top_k = settings.ADAPTIVE_RETRIEVAL_COMPLEX_ANALYTICAL_TOP_K
            strategy = "complex_analytical"
            reason = f"Complex analytical query requires deep retrieval matching (Top-{top_k} chunks)."
        elif intent == "comparison":
            top_k = settings.ADAPTIVE_RETRIEVAL_LARGE_COMPARISON_TOP_K
            strategy = "large_comparison"
            reason = f"Comparison query requires broad multi-source retrieval context (Top-{top_k} chunks)."
        # General fallbacks
        elif complexity == "complex":
            top_k = settings.ADAPTIVE_RETRIEVAL_COMPLEX_ANALYTICAL_TOP_K
            strategy = "complex_fallback"
            reason = f"General complex query requires deep retrieval matching (Top-{top_k} chunks)."
        elif complexity == "medium":
            top_k = settings.ADAPTIVE_RETRIEVAL_MEDIUM_EXPLANATION_TOP_K
            strategy = "medium_fallback"
            reason = f"General medium query requires standard context (Top-{top_k} chunks)."
        else:
            top_k = settings.ADAPTIVE_RETRIEVAL_SIMPLE_FACTUAL_TOP_K
            strategy = "simple_fallback"
            reason = f"General simple query requires minimal context (Top-{top_k} chunks)."
            
        return AdaptiveRetrievalResult(
            retrieval_strategy=strategy,
            selected_top_k=top_k,
            retrieval_reason=reason,
            confidence=round(confidence, 2)
        )

class LLMAdaptiveRetrievalPolicy(BaseAdaptiveRetrievalPolicy):
    def __init__(self):
        self.model_name = settings.GEMINI_MODEL

    def determine_strategy(
        self, 
        analysis: QueryAnalysis, 
        rewrite_result: Optional[QueryRewriteResult] = None
    ) -> AdaptiveRetrievalResult:
        import json
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
            
        genai.configure(api_key=api_key)
        
        system_instruction = (
            "You are an advanced Adaptive Retrieval agent. Your task is to dynamically select the optimal document retrieval strategy and chunk limit (Top-K) based on query analysis.\n"
            "You will receive the intent, complexity, keyword count, confidence scores, and rewriting status.\n"
            "Output a JSON object with the following fields:\n"
            "1. 'retrieval_strategy': A string identifier (e.g. simple_factual, medium_explanation, complex_analytical, large_comparison, or standard_retrieval).\n"
            "2. 'selected_top_k': An integer representing the recommended number of document chunks to retrieve (e.g. between 3 and 15).\n"
            "3. 'retrieval_reason': A clear, short explanation explaining why you chose this strategy and Top-K limit.\n"
            "4. 'confidence': A float score between 0.0 and 1.0 representing routing confidence.\n"
            "\n"
            "Ensure the response is valid JSON and strictly adheres to this schema. Do not add any markdown formatting outside JSON."
        )
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        )
        
        prompt = (
            f"Original Query: '{analysis.raw_query}'\n"
            f"Intent: '{analysis.intent}' (Confidence: {analysis.intent_confidence})\n"
            f"Complexity: '{analysis.complexity}' (Confidence: {analysis.complexity_confidence})\n"
            f"Rewritten Query: '{rewrite_result.rewritten_query if rewrite_result else 'N/A'}' (Applied: {rewrite_result.rewrite_applied if rewrite_result else 'False'})\n"
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
            strategy = data.get("retrieval_strategy", "standard_retrieval").strip()
            top_k = int(data.get("selected_top_k", settings.ADAPTIVE_RETRIEVAL_DEFAULT_TOP_K))
            top_k = max(1, min(50, top_k))
            reason = data.get("retrieval_reason", "LLM-based adaptive retrieval routing decision.").strip()
            confidence = float(data.get("confidence", 0.9))
            confidence = max(0.0, min(1.0, confidence))
            
            return AdaptiveRetrievalResult(
                retrieval_strategy=strategy,
                selected_top_k=top_k,
                retrieval_reason=reason,
                confidence=round(confidence, 2)
            )
        else:
            raise ValueError("Empty response from Gemini API during adaptive retrieval routing.")

class AdaptiveRetrievalService:
    def __init__(self):
        self.rules_policy = RulesBasedAdaptiveRetrievalPolicy()
        
    def determine_strategy(
        self, 
        analysis: QueryAnalysis, 
        rewrite_result: Optional[QueryRewriteResult] = None
    ) -> AdaptiveRetrievalResult:
        query = analysis.raw_query.strip()
        
        if not settings.ADAPTIVE_RETRIEVAL_ENABLED:
            logger.info("Adaptive retrieval is disabled. Returning default Top-K.")
            return AdaptiveRetrievalResult(
                retrieval_strategy="disabled_fallback",
                selected_top_k=settings.ADAPTIVE_RETRIEVAL_DEFAULT_TOP_K,
                retrieval_reason="Adaptive retrieval is disabled in configuration settings.",
                confidence=1.0
            )
            
        policy_type = settings.ADAPTIVE_RETRIEVAL_POLICY_TYPE.lower()
        result = None
        
        # LLM Policy
        if policy_type == "llm":
            try:
                llm_policy = LLMAdaptiveRetrievalPolicy()
                result = llm_policy.determine_strategy(analysis, rewrite_result)
            except Exception as e:
                logger.error(f"Error in LLMAdaptiveRetrievalPolicy: {e}. Falling back to RulesBasedAdaptiveRetrievalPolicy.", exc_info=True)
                result = self.rules_policy.determine_strategy(analysis, rewrite_result)
                
        # Rules Policy
        elif policy_type == "rules":
            result = self.rules_policy.determine_strategy(analysis, rewrite_result)
            
        # Hybrid Policy (Default)
        else:
            if settings.GEMINI_API_KEY:
                try:
                    llm_policy = LLMAdaptiveRetrievalPolicy()
                    result = llm_policy.determine_strategy(analysis, rewrite_result)
                    logger.info("Successfully executed LLMAdaptiveRetrievalPolicy.")
                except Exception as e:
                    logger.warning(f"LLMAdaptiveRetrievalPolicy failed: {e}. Falling back to RulesBasedAdaptiveRetrievalPolicy.")
                    result = self.rules_policy.determine_strategy(analysis, rewrite_result)
            else:
                logger.info("GEMINI_API_KEY not configured. Executing RulesBasedAdaptiveRetrievalPolicy.")
                result = self.rules_policy.determine_strategy(analysis, rewrite_result)
                
        # Log adaptive retrieval decisions explaining intent, complexity, strategy, top_k, reason
        logger.info(
            f"\n--- ADAPTIVE RETRIEVAL ROUTER ---\n"
            f"Query: '{query}'\n"
            f"Intent: '{analysis.intent}' | Complexity: '{analysis.complexity}'\n"
            f"Chosen Strategy: '{result.retrieval_strategy}'\n"
            f"Chosen Top-K: {result.selected_top_k}\n"
            f"Reason: '{result.retrieval_reason}'\n"
            f"Confidence: {result.confidence}\n"
            f"----------------------------------"
        )
        
        return result

adaptive_retriever = AdaptiveRetrievalService()
