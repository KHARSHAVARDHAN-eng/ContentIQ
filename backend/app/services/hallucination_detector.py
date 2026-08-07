import logging
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
import google.generativeai as genai
from app.core.config import settings
from app.schemas.hallucination import HallucinationDetectionResult

logger = logging.getLogger("app.services.hallucination_detector")

class BaseHallucinationDetector(ABC):
    @abstractmethod
    def detect(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        answer: str
    ) -> HallucinationDetectionResult:
        pass

class RulesBasedHallucinationDetector(BaseHallucinationDetector):
    def detect(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        answer: str
    ) -> HallucinationDetectionResult:
        if not answer or answer.strip() == "":
            return HallucinationDetectionResult(
                hallucination_status="CLEAN",
                confidence_score=1.0,
                unsupported_claims=[],
                grounded_claims=[],
                reasoning="Empty answer response; bypassed grounding check."
            )
            
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if s.strip()]
        if not sentences:
            return HallucinationDetectionResult(
                hallucination_status="CLEAN",
                confidence_score=1.0,
                unsupported_claims=[],
                grounded_claims=[],
                reasoning="No sentences found in answer; bypassed grounding check."
            )

        stop_words = {"what", "is", "a", "the", "and", "or", "to", "in", "of", "for", "with", "how", "does", "why", "who", "where", "which", "are", "on", "about", "this", "that", "it", "they", "them", "their", "we", "us", "our", "i", "you", "he", "she", "his", "her", "but", "so", "because", "as", "be", "been", "have", "has", "had", "do", "did"}
        
        def get_keywords(text: str):
            return set(w for w in re.findall(r'\b\w+\b', text.lower()) if w not in stop_words and len(w) > 2)

        grounded_claims = []
        unsupported_claims = []

        for sentence in sentences:
            sent_kws = get_keywords(sentence)
            # If a sentence is conversational/empty of keywords, auto-ground it
            if not sent_kws:
                grounded_claims.append(sentence)
                continue
                
            is_grounded = False
            for chunk in chunks:
                chunk_text = chunk.get("chunk_text", "").lower()
                chunk_kws = get_keywords(chunk_text)
                overlap = sent_kws.intersection(chunk_kws)
                
                # Dynamic matching threshold based on sentence keyword count
                if len(sent_kws) <= 2:
                    match_threshold = 1
                else:
                    match_threshold = max(2, int(len(sent_kws) * 0.40))
                    
                if len(overlap) >= match_threshold:
                    is_grounded = True
                    break
                    
            if is_grounded:
                grounded_claims.append(sentence)
            else:
                unsupported_claims.append(sentence)

        confidence = len(grounded_claims) / len(sentences)
        threshold = settings.HALLUCINATION_DETECTOR_THRESHOLD
        
        if confidence >= threshold:
            status = "CLEAN"
            reason = f"Grounding check validation passed. Tested {len(sentences)} claims: {len(grounded_claims)} grounded, {len(unsupported_claims)} unsupported. Grounding ratio: {confidence:.2f} >= threshold: {threshold:.2f}."
        elif confidence >= max(0.0, threshold - 0.20):
            status = "WARNING"
            reason = f"Grounding check validation warning. Grounding ratio: {confidence:.2f} lies below threshold: {threshold:.2f}."
        else:
            status = "FAILED"
            reason = f"Grounding check validation failed. Grounding ratio: {confidence:.2f} is significantly below threshold: {threshold:.2f}."

        return HallucinationDetectionResult(
            hallucination_status=status,
            confidence_score=round(confidence, 2),
            unsupported_claims=unsupported_claims,
            grounded_claims=grounded_claims,
            reasoning=reason
        )

class LLMHallucinationDetector(BaseHallucinationDetector):
    def __init__(self):
        self.model_name = settings.HALLUCINATION_DETECTOR_MODEL

    def detect(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        answer: str
    ) -> HallucinationDetectionResult:
        import json
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        if not answer or answer.strip() == "":
            return HallucinationDetectionResult(
                hallucination_status="CLEAN",
                confidence_score=1.0,
                unsupported_claims=[],
                grounded_claims=[],
                reasoning="Empty answer response; bypassed grounding check."
            )

        genai.configure(api_key=api_key)
        
        system_instruction = (
            "You are an expert Hallucination Detector. Compare the generated answer sentences against the provided source chunks.\n"
            "Identify which sentences are supported (grounded) by the source chunks, and which sentences are unsupported (hallucinations).\n"
            "Output a JSON object with the following fields:\n"
            "1. 'hallucination_status': A string status of either 'CLEAN' (if confidence is high), 'WARNING' (if some claims are unsupported), or 'FAILED' (if major claims are unsupported).\n"
            "2. 'confidence_score': A float grounding score between 0.0 and 1.0 (ratio of grounded claims to total claims).\n"
            "3. 'unsupported_claims': A list of sentences from the generated answer that are unsupported or contradict the sources.\n"
            "4. 'grounded_claims': A list of sentences from the generated answer that are supported by the sources.\n"
            "5. 'reasoning': A clear explanation detailing your grounding analysis.\n"
            "\n"
            "Ensure the response is valid JSON and strictly adheres to this schema. Do not add any markdown formatting outside JSON."
        )
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        )
        
        formatted_chunks = []
        for idx, c in enumerate(chunks):
            formatted_chunks.append(f"Source {idx}: {c.get('chunk_text', '')}")
            
        prompt = (
            f"User Query: '{query}'\n"
            f"Source Evidence Chunks:\n" + "\n".join(formatted_chunks) + "\n\n"
            f"Generated Answer to Validate:\n'{answer}'\n"
        )
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=settings.HALLUCINATION_DETECTOR_TEMPERATURE,
                response_mime_type="application/json"
            )
        )
        
        if response and response.text:
            data = json.loads(response.text.strip())
            
            # Map parameters
            status = data.get("hallucination_status", "CLEAN").strip().upper()
            if status not in ["CLEAN", "WARNING", "FAILED"]:
                status = "CLEAN"
                
            confidence = float(data.get("confidence_score", 1.0))
            confidence = max(0.0, min(1.0, confidence))
            unsupported = data.get("unsupported_claims", [])
            grounded = data.get("grounded_claims", [])
            reason = data.get("reasoning", "LLM grounding check complete.").strip()
            
            return HallucinationDetectionResult(
                hallucination_status=status,
                confidence_score=round(confidence, 2),
                unsupported_claims=unsupported,
                grounded_claims=grounded,
                reasoning=reason
            )
        else:
            raise ValueError("Empty response from Gemini API during hallucination detection.")

class HallucinationDetectionService:
    def __init__(self):
        self.rules_detector = RulesBasedHallucinationDetector()
        
    def detect(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        answer: str
    ) -> HallucinationDetectionResult:
        if not settings.HALLUCINATION_DETECTOR_ENABLED:
            logger.info("Hallucination detector is disabled. Returning CLEAN status.")
            return HallucinationDetectionResult(
                hallucination_status="CLEAN",
                confidence_score=1.0,
                unsupported_claims=[],
                grounded_claims=[],
                reasoning="Hallucination detection is disabled in configuration settings."
            )
            
        detector_type = settings.HALLUCINATION_DETECTOR_TYPE.lower()
        result = None
        
        # LLM Detector
        if detector_type == "llm":
            try:
                llm_detector = LLMHallucinationDetector()
                result = llm_detector.detect(query, chunks, answer)
            except Exception as e:
                logger.error(f"Error in LLMHallucinationDetector: {e}. Falling back to RulesBased.", exc_info=True)
                result = self.rules_detector.detect(query, chunks, answer)
                
        # Rules Detector
        elif detector_type == "rules":
            result = self.rules_detector.detect(query, chunks, answer)
            
        # Hybrid Detector (Default)
        else:
            if settings.GEMINI_API_KEY:
                try:
                    llm_detector = LLMHallucinationDetector()
                    result = llm_detector.detect(query, chunks, answer)
                    logger.info("Successfully executed LLMHallucinationDetector.")
                except Exception as e:
                    logger.warning(f"LLMHallucinationDetector failed: {e}. Falling back to RulesBased.")
                    result = self.rules_detector.detect(query, chunks, answer)
            else:
                logger.info("GEMINI_API_KEY not configured. Executing RulesBasedHallucinationDetector.")
                result = self.rules_detector.detect(query, chunks, answer)
                
        # Log detailed hallucination detection findings
        logger.info(
            f"\n--- HALLUCINATION DETECTION REPORT ---\n"
            f"Query: '{query}'\n"
            f"Validation Status: '{result.hallucination_status}' | Confidence: {result.confidence_score:.2f}\n"
            f"Reasoning: '{result.reasoning}'\n"
            f"Grounded Claims (Count: {len(result.grounded_claims)}):\n" + 
            "\n".join([f" - {c}" for c in result.grounded_claims]) + "\n"
            f"Unsupported Claims (Count: {len(result.unsupported_claims)}):\n" + 
            "\n".join([f" - {c}" for c in result.unsupported_claims]) + "\n"
            f"----------------------------------------\n"
        )
        
        return result

hallucination_detector = HallucinationDetectionService()
