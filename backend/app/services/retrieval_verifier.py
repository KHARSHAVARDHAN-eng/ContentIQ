import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from app.core.config import settings
from app.schemas.retrieval_verification import RetrievalVerificationResult

logger = logging.getLogger("app.services.retrieval_verifier")

class BaseRetrievalVerifier(ABC):
    @abstractmethod
    def verify(self, hits: List[Dict[str, Any]], query: str) -> RetrievalVerificationResult:
        pass

class RulesBasedRetrievalVerifier(BaseRetrievalVerifier):
    def verify(self, hits: List[Dict[str, Any]], query: str) -> RetrievalVerificationResult:
        if not hits:
            return RetrievalVerificationResult(
                verification_status="FAIL",
                retrieval_confidence=0.0,
                quality_score=0.0,
                verification_reason="No documents retrieved from vector search store.",
                recommended_action="Trigger retrieval retry"
            )
            
        scores = [hit.get("score", 0.0) for hit in hits]
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        
        # Count relevant chunks above typical relevance threshold (0.22)
        relevant_chunks = sum(1 for s in scores if s >= 0.22)
        
        # Calculate quality score: based on average score and number of relevant chunks
        quality_score = (avg_score * 1.4) + (min(0.3, relevant_chunks * 0.1))
        quality_score = max(0.0, min(1.0, quality_score))
        
        # Calculate confidence score
        confidence = avg_score
        
        min_pass = settings.RETRIEVAL_VERIFIER_MIN_PASS_SCORE
        min_warning = settings.RETRIEVAL_VERIFIER_MIN_WARNING_SCORE
        
        if quality_score >= min_pass:
            status = "PASS"
            action = "Continue normally"
            reason = f"Retrieval quality is high. Quality score: {quality_score:.2f} (Top hit: {max_score:.2f}, Avg: {avg_score:.2f}, Relevant: {relevant_chunks}/{len(hits)})."
        elif quality_score >= min_warning:
            status = "WARNING"
            action = "Continue with caution"
            reason = f"Retrieval quality is moderate. Quality score: {quality_score:.2f} (Top hit: {max_score:.2f}, Avg: {avg_score:.2f}, Relevant: {relevant_chunks}/{len(hits)})."
        else:
            status = "FAIL"
            action = "Trigger retrieval retry"
            reason = f"Retrieval quality is poor. Quality score: {quality_score:.2f} (Top hit: {max_score:.2f}, Avg: {avg_score:.2f}, Relevant: {relevant_chunks}/{len(hits)})."
            
        return RetrievalVerificationResult(
            verification_status=status,
            retrieval_confidence=round(confidence, 2),
            quality_score=round(quality_score, 2),
            verification_reason=reason,
            recommended_action=action
        )

class LLMRetrievalVerifier(BaseRetrievalVerifier):
    def __init__(self):
        self.model_name = settings.GEMINI_MODEL

    def verify(self, hits: List[Dict[str, Any]], query: str) -> RetrievalVerificationResult:
        import json
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
            
        genai.configure(api_key=api_key)
        
        system_instruction = (
            "You are an advanced Retrieval Verification agent. Evaluate the quality of the retrieved document chunks for the user query.\n"
            "Determine if the chunks are semantically consistent and relevant to answering the query.\n"
            "Output a JSON object with the following fields:\n"
            "1. 'verification_status': A string: PASS (relevant), WARNING (partially relevant/caution), or FAIL (poor relevance/retry).\n"
            "2. 'retrieval_confidence': A float representing retrieval confidence (0.0 to 1.0).\n"
            "3. 'quality_score': A float representing retrieval quality (0.0 to 1.0).\n"
            "4. 'verification_reason': A clear explanation explaining why you chose this verification decision.\n"
            "5. 'recommended_action': A string: 'Continue normally' (for PASS), 'Continue with caution' (for WARNING), or 'Trigger retrieval retry' (for FAIL).\n"
            "\n"
            "Ensure the response is valid JSON and strictly adheres to this schema. Do not add any markdown formatting outside JSON."
        )
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        )
        
        formatted_hits = []
        for i, h in enumerate(hits):
            formatted_hits.append(f"Chunk {i+1} (Score: {h.get('score', 0.0)}): {h.get('chunk_text', '')}")
            
        prompt = (
            f"User Query: '{query}'\n"
            f"Retrieved Chunks:\n" + "\n".join(formatted_hits)
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
            status = data.get("verification_status", "PASS").upper()
            if status not in {"PASS", "WARNING", "FAIL"}:
                status = "PASS"
                
            confidence = float(data.get("retrieval_confidence", 0.9))
            confidence = max(0.0, min(1.0, confidence))
            
            quality_score = float(data.get("quality_score", 0.9))
            quality_score = max(0.0, min(1.0, quality_score))
            
            reason = data.get("verification_reason", "LLM retrieval quality check.").strip()
            action = data.get("recommended_action", "Continue normally").strip()
            
            return RetrievalVerificationResult(
                verification_status=status,
                retrieval_confidence=round(confidence, 2),
                quality_score=round(quality_score, 2),
                verification_reason=reason,
                recommended_action=action
            )
        else:
            raise ValueError("Empty response from Gemini API during retrieval verification.")

class RetrievalVerificationService:
    def __init__(self):
        self.rules_verifier = RulesBasedRetrievalVerifier()
        
    def verify(self, hits: List[Dict[str, Any]], query: str) -> RetrievalVerificationResult:
        if not settings.RETRIEVAL_VERIFIER_ENABLED:
            logger.info("Retrieval verifier is disabled. Returning default PASS.")
            return RetrievalVerificationResult(
                verification_status="PASS",
                retrieval_confidence=1.0,
                quality_score=1.0,
                verification_reason="Retrieval verifier is disabled in configurations.",
                recommended_action="Continue normally"
            )
            
        verifier_type = settings.RETRIEVAL_VERIFIER_TYPE.lower()
        result = None
        
        # LLM Verifier
        if verifier_type == "llm":
            try:
                llm_verifier = LLMRetrievalVerifier()
                result = llm_verifier.verify(hits, query)
            except Exception as e:
                logger.error(f"Error in LLMRetrievalVerifier: {e}. Falling back to RulesBasedRetrievalVerifier.", exc_info=True)
                result = self.rules_verifier.verify(hits, query)
                
        # Rules Verifier
        elif verifier_type == "rules":
            result = self.rules_verifier.verify(hits, query)
            
        # Hybrid Verifier (Default)
        else:
            if settings.GEMINI_API_KEY:
                try:
                    llm_verifier = LLMRetrievalVerifier()
                    result = llm_verifier.verify(hits, query)
                    logger.info("Successfully executed LLMRetrievalVerifier.")
                except Exception as e:
                    logger.warning(f"LLMRetrievalVerifier failed: {e}. Falling back to RulesBasedRetrievalVerifier.")
                    result = self.rules_verifier.verify(hits, query)
            else:
                logger.info("GEMINI_API_KEY not configured. Executing RulesBasedRetrievalVerifier.")
                result = self.rules_verifier.verify(hits, query)
                
        # Log verification output: Top-K, average similarity, minimum similarity, quality score, retry decision, and final decision
        if hits:
            scores = [h.get("score", 0.0) for h in hits]
            avg_sim = sum(scores) / len(scores)
            min_sim = min(scores)
        else:
            avg_sim = 0.0
            min_sim = 0.0
            
        logger.info(
            f"\n--- RETRIEVAL VERIFICATION ENGINE ---\n"
            f"Query: '{query}'\n"
            f"Top-K retrieved: {len(hits)}\n"
            f"Average similarity: {avg_sim:.4f} | Minimum similarity: {min_sim:.4f}\n"
            f"Verification quality score: {result.quality_score:.2f} | Status: {result.verification_status}\n"
            f"Decision: '{result.recommended_action}' (Reason: '{result.verification_reason}')\n"
            f"--------------------------------------"
        )
        
        return result

retrieval_verifier = RetrievalVerificationService()
