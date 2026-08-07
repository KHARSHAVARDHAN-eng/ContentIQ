import time
import json
import logging
import re
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from app.core.config import settings
from app.schemas.self_reflection import SelfReflectionResult

logger = logging.getLogger("app.services.self_reflector")

class SelfReflectorService:
    def reflect(
        self,
        question: str,
        original_answer: str,
        context_chunks: List[Dict[str, Any]],
        hallucination_detection: Optional[Any] = None,
        answer_verification: Optional[Any] = None
    ) -> SelfReflectionResult:
        start_time = time.time()

        if not original_answer:
            return SelfReflectionResult(
                reflection_summary="Empty answer provided.",
                detected_issues=[],
                improvement_suggestions=[],
                quality_score=1.0,
                refinement_performed=False,
                original_answer="",
                refined_answer="",
                confidence=1.0,
                metadata={"reason": "Empty answer"}
            )

        api_key = settings.GEMINI_API_KEY
        if api_key and settings.SELF_REFLECTION_ENABLED:
            try:
                return self._reflect_with_llm(
                    question,
                    original_answer,
                    context_chunks,
                    hallucination_detection,
                    answer_verification,
                    api_key,
                    start_time
                )
            except Exception as e:
                logger.warning(f"LLM self-reflection failed: {e}. Falling back to rule-based reflector.")
                return self._reflect_with_rules(
                    question,
                    original_answer,
                    context_chunks,
                    hallucination_detection,
                    answer_verification,
                    start_time
                )
        else:
            return self._reflect_with_rules(
                question,
                original_answer,
                context_chunks,
                hallucination_detection,
                answer_verification,
                start_time
            )

    def _reflect_with_llm(
        self,
        question: str,
        original_answer: str,
        context_chunks: List[Dict[str, Any]],
        hallucination_detection: Optional[Any],
        answer_verification: Optional[Any],
        api_key: str,
        start_time: float
    ) -> SelfReflectionResult:
        genai.configure(api_key=api_key)

        # Context serialization
        evidence_text = "\n".join([f"- Chunk {c.get('chunk_id')}: {c.get('chunk_text')}" for c in context_chunks])
        
        # Serialize upstream validation reports
        hallucination_payload = "N/A"
        if hallucination_detection:
            hallucination_payload = (
                f"Status: {getattr(hallucination_detection, 'hallucination_status', 'N/A')}\n"
                f"Score: {getattr(hallucination_detection, 'confidence_score', 'N/A')}\n"
                f"Reasoning: {getattr(hallucination_detection, 'reasoning', 'N/A')}"
            )
            
        verification_payload = "N/A"
        if answer_verification:
            claims_summary = []
            for cv in getattr(answer_verification, "claim_verifications", []):
                claims_summary.append(
                    f"Claim: '{cv.claim_text}' | Status: {cv.verification_label} | Explanation: {cv.explanation}"
                )
            verification_payload = (
                f"Score: {getattr(answer_verification, 'overall_verification_score', 'N/A')}\n"
                f"Claims:\n" + "\n".join(claims_summary)
            )

        system_instruction = (
            "You are a critical self-reflection agent. Your task is to evaluate the quality of a generated RAG answer using the user query, "
            "retrieved evidence, hallucination status, and claim verification reports.\n"
            "Identify weaknesses such as factual gaps, ungrounded reasoning, repetition, ambiguity, and poor clarity.\n"
            "Assign a quality score between 0.0 and 1.0.\n"
            "If the score falls below the target threshold, and answer refinement is enabled, you should refine the answer.\n"
            "To refine the answer:\n"
            "- REMOVE any factual claims marked as UNSUPPORTED or CONTRADICTED.\n"
            "- PRESERVE all factual statements that are VERIFIED or PARTIALLY_SUPPORTED.\n"
            "- Improve formatting, clarity, transitions, and structure.\n"
            "- Do NOT invent new facts not found in the evidence chunks.\n"
            "Return a JSON object matching:\n"
            "{\n"
            "  'reflection_summary': str,\n"
            "  'detected_issues': [str],\n"
            "  'improvement_suggestions': [str],\n"
            "  'quality_score': float,\n"
            "  'refinement_performed': bool,\n"
            "  'refined_answer': str (optional, keep empty if no refinement was performed)\n"
            "}"
        )

        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_instruction
        )

        prompt = (
            f"USER QUERY: {question}\n\n"
            f"EVIDENCE CONTEXT:\n{evidence_text}\n\n"
            f"ORIGINAL ANSWER:\n{original_answer}\n\n"
            f"HALLUCINATION REPORT:\n{hallucination_payload}\n\n"
            f"VERIFICATION REPORT:\n{verification_payload}\n\n"
            f"REFINEMENT ENABLED: {settings.ENABLE_ANSWER_REFINEMENT}\n"
            f"SCORE THRESHOLD: {settings.REFLECTION_SCORE_THRESHOLD}"
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
            ref_performed = bool(data.get("refinement_performed", False))
            refined = data.get("refined_answer", "").strip()

            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Self-Reflection (LLM): Score: {data.get('quality_score')} | "
                f"Refinement Performed: {ref_performed} | Latency: {latency_ms}ms"
            )

            return SelfReflectionResult(
                reflection_summary=data.get("reflection_summary", ""),
                detected_issues=data.get("detected_issues", []),
                improvement_suggestions=data.get("improvement_suggestions", []),
                quality_score=float(data.get("quality_score", 1.0)),
                refinement_performed=ref_performed,
                original_answer=original_answer,
                refined_answer=refined if ref_performed and refined else original_answer,
                confidence=1.0,
                metadata={"mode": settings.SELF_REFLECTION_MODE, "latency_ms": latency_ms}
            )

        raise ValueError("Empty response from self-reflection API")

    def _reflect_with_rules(
        self,
        question: str,
        original_answer: str,
        context_chunks: List[Dict[str, Any]],
        hallucination_detection: Optional[Any],
        answer_verification: Optional[Any],
        start_time: float
    ) -> SelfReflectionResult:
        score = 1.0
        detected_issues = []
        improvement_suggestions = []

        # 1. Evaluate Hallucination report
        if hallucination_detection:
            h_status = getattr(hallucination_detection, "hallucination_status", "PASSED")
            if h_status == "FAILED":
                score -= 0.4
                detected_issues.append("Answer contains severe hallucinated/ungrounded text.")
                improvement_suggestions.append("Purge ungrounded details and stay factual.")
            elif h_status == "WARNING":
                score -= 0.2
                detected_issues.append("Answer has moderate hallucination warnings.")
                improvement_suggestions.append("Verify grounding and remove loose speculations.")

        # 2. Evaluate Answer Verification report
        if answer_verification:
            verification_score = getattr(answer_verification, "overall_verification_score", 1.0)
            score -= (1.0 - verification_score) * 0.4
            
            unsupported_claims = [
                cv.claim_text for cv in getattr(answer_verification, "claim_verifications", [])
                if cv.verification_label in ["UNSUPPORTED", "CONTRADICTED"]
            ]
            if unsupported_claims:
                detected_issues.append(f"Contains {len(unsupported_claims)} unsupported or contradicted statements.")
                improvement_suggestions.append("Filter out unverified claims and keep only verified context assertions.")

        # 3. Check for phrase repetition / word-level redundancy
        words = original_answer.lower().split()
        if len(words) > 30:
            unique_words = set(words)
            lexical_density = len(unique_words) / len(words)
            if lexical_density < 0.40:
                score -= 0.1
                detected_issues.append("High redundancy or word repetition detected in answer structure.")
                improvement_suggestions.append("Rephrase to improve conciseness and reduce repetition.")

        # 4. Check for page citations
        if "citations" not in original_answer.lower() and len(original_answer) > 100:
            # Simple heuristic
            pass

        score = max(0.0, min(1.0, round(score, 2)))
        
        # Decide refinement
        ref_necessary = score < settings.REFLECTION_SCORE_THRESHOLD and settings.ENABLE_ANSWER_REFINEMENT
        
        refined_answer = None
        if ref_necessary:
            refined_answer = self._perform_rules_refinement(original_answer, answer_verification)
            
        latency_ms = int((time.time() - start_time) * 1000)

        summary = (
            f"Factual self-reflection complete (rule-based). Answer Quality Score: {score:.2f}. "
            f"Refinement Performed: {ref_necessary}."
        )

        logger.info(
            f"Self-Reflection (Rules): Score: {score:.2f} | Refinement Performed: {ref_necessary} | "
            f"Latency: {latency_ms}ms"
        )

        return SelfReflectionResult(
            reflection_summary=summary,
            detected_issues=detected_issues,
            improvement_suggestions=improvement_suggestions,
            quality_score=score,
            refinement_performed=ref_necessary,
            original_answer=original_answer,
            refined_answer=refined_answer if ref_necessary else original_answer,
            confidence=0.8,
            metadata={"mode": settings.SELF_REFLECTION_MODE, "latency_ms": latency_ms}
        )

    def _perform_rules_refinement(self, answer: str, answer_verification: Optional[Any]) -> str:
        if not answer_verification:
            return answer

        unsupported_texts = []
        for cv in getattr(answer_verification, "claim_verifications", []):
            if cv.verification_label in ["UNSUPPORTED", "CONTRADICTED"]:
                # Lowercase and strip punctuation for soft matching
                norm = re.sub(r'[^\w\s]', '', cv.claim_text.lower()).strip()
                if norm:
                    unsupported_texts.append(norm)

        if not unsupported_texts:
            return answer

        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if s.strip()]
        refined_sentences = []

        for sent in sentences:
            norm_sent = re.sub(r'[^\w\s]', '', sent.lower()).strip()
            # If the sentence contains or overlaps significantly with an unsupported statement, drop it
            should_skip = False
            for un_norm in unsupported_texts:
                if un_norm in norm_sent or norm_sent in un_norm:
                    should_skip = True
                    break
            if not should_skip:
                refined_sentences.append(sent)

        if not refined_sentences:
            return "The original answer could not be supported by retrieved evidence context."

        return " ".join(refined_sentences)

self_reflector = SelfReflectorService()
