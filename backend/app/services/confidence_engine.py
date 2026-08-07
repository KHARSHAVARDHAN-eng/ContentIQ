import time
import logging
import re
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.schemas.confidence import ConfidenceResult, FactorScore

logger = logging.getLogger("app.services.confidence_engine")

class ConfidenceEngineService:
    def compute_confidence(
        self,
        answer: str,
        citations: List[Any],
        retrieval_verification: Optional[Any] = None,
        reranking: Optional[Any] = None,
        hallucination_detection: Optional[Any] = None,
        answer_verification: Optional[Any] = None,
        self_reflection: Optional[Any] = None
    ) -> ConfidenceResult:
        start_time = time.time()

        # 1. Norm Factors Calculations
        factor_scores: List[FactorScore] = []

        # A. Retrieval Verification
        retrieval_raw = 1.0
        if retrieval_verification:
            retrieval_raw = getattr(retrieval_verification, "quality_score", 1.0)
        # Handle dict case
        elif isinstance(retrieval_verification, dict):
            retrieval_raw = retrieval_verification.get("quality_score", 1.0)
        retrieval_norm = max(0.0, min(1.0, float(retrieval_raw)))
        
        # B. Reranking
        reranking_raw = 0.80
        if reranking:
            hits = getattr(reranking, "hits", [])
            if not hits and isinstance(reranking, dict):
                hits = reranking.get("hits", [])
            if hits:
                # Average reranker score (normally in 0-1)
                scores = []
                for h in hits:
                    if isinstance(h, dict):
                        scores.append(h.get("reranker_score", 0.80))
                    else:
                        scores.append(getattr(h, "reranker_score", 0.80))
                reranking_raw = sum(scores) / len(scores) if scores else 0.80
        # Normalize rerank score: bound between 0 and 1
        reranking_norm = max(0.0, min(1.0, float(reranking_raw)))

        # C. Hallucination Detection
        hallucination_raw = 1.0
        if hallucination_detection:
            h_status = getattr(hallucination_detection, "hallucination_status", "CLEAN")
            if h_status == "CLEAN":
                hallucination_raw = 1.0
            elif h_status == "WARNING":
                hallucination_raw = 0.5
            else:
                hallucination_raw = 0.0
        elif isinstance(hallucination_detection, dict):
            h_status = hallucination_detection.get("hallucination_status", "CLEAN")
            if h_status == "CLEAN":
                hallucination_raw = 1.0
            elif h_status == "WARNING":
                hallucination_raw = 0.5
            else:
                hallucination_raw = 0.0
        hallucination_norm = float(hallucination_raw)

        # D. Answer Verification
        verification_raw = 1.0
        if answer_verification:
            verification_raw = getattr(answer_verification, "overall_verification_score", 1.0)
        elif isinstance(answer_verification, dict):
            verification_raw = answer_verification.get("overall_verification_score", 1.0)
        verification_norm = max(0.0, min(1.0, float(verification_raw)))

        # E. Self-Reflection
        reflection_raw = 1.0
        if self_reflection:
            reflection_raw = getattr(self_reflection, "quality_score", 1.0)
        elif isinstance(self_reflection, dict):
            reflection_raw = self_reflection.get("quality_score", 1.0)
        reflection_norm = max(0.0, min(1.0, float(reflection_raw)))

        # F. Citation Coverage
        citation_raw = 1.0
        if answer:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if s.strip()]
            sentence_count = len(sentences)
            citation_count = len(citations)
            if sentence_count > 0:
                citation_raw = citation_count / sentence_count
            else:
                citation_raw = 1.0
        citation_norm = max(0.0, min(1.0, float(citation_raw)))

        # 2. Configurable Weights normalisation
        w_retrieval = settings.CONFIDENCE_WEIGHT_RETRIEVAL
        w_reranking = settings.CONFIDENCE_WEIGHT_RERANKING
        w_verification = settings.CONFIDENCE_WEIGHT_VERIFICATION
        w_hallucination = settings.CONFIDENCE_WEIGHT_HALLUCINATION
        w_reflection = settings.CONFIDENCE_WEIGHT_REFLECTION
        w_citations = settings.CONFIDENCE_WEIGHT_CITATIONS

        total_weight = w_retrieval + w_reranking + w_verification + w_hallucination + w_reflection + w_citations
        if total_weight > 0:
            w_retrieval /= total_weight
            w_reranking /= total_weight
            w_verification /= total_weight
            w_hallucination /= total_weight
            w_reflection /= total_weight
            w_citations /= total_weight

        # 3. Factor score assembly
        factors_data = [
            ("retrieval_verification", retrieval_raw, retrieval_norm, w_retrieval),
            ("reranking", reranking_raw, reranking_norm, w_reranking),
            ("hallucination_detection", hallucination_raw, hallucination_norm, w_hallucination),
            ("answer_verification", verification_raw, verification_norm, w_verification),
            ("self_reflection", reflection_raw, reflection_norm, w_reflection),
            ("citations", citation_raw, citation_norm, w_citations)
        ]

        overall_score = 0.0
        for name, raw, norm, weight in factors_data:
            contrib = norm * weight
            overall_score += contrib
            factor_scores.append(
                FactorScore(
                    factor_name=name,
                    raw_value=float(round(raw, 2)),
                    normalized_score=float(round(norm, 2)),
                    weight=float(round(weight, 2)),
                    contribution=float(round(contrib, 2))
                )
            )

        overall_score_pct = max(0.0, min(100.0, float(round(overall_score * 100.0, 2))))

        # 4. Classify category and construct explanation / recommendations
        recommendations = []
        if overall_score_pct >= settings.CONFIDENCE_HIGH_THRESHOLD:
            level = "HIGH"
            explanation = "Confidence is high. Factual grounding, citation coverage, and self-reflection margins are optimal."
            recommendations.append("The answer is highly reliable and fully validated against context documents.")
        elif overall_score_pct >= settings.CONFIDENCE_MEDIUM_THRESHOLD:
            level = "MEDIUM"
            explanation = "Confidence is moderate. Verify citations to check specific grounding details."
            recommendations.append("Cross-reference specific sentences with highlighted citation pages.")
        else:
            level = "LOW"
            explanation = "Confidence is low. Grounding gaps, hallucination warnings, or lack of citation coverage detected."
            recommendations.append("Manually audit referenced document snippets.")
            recommendations.append("Reformulate question with specific keywords to improve retrieval focus.")

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Confidence Scoring: Score: {overall_score_pct:.1f} | Level: {level} | Latency: {latency_ms}ms"
        )

        return ConfidenceResult(
            overall_score=overall_score_pct,
            confidence_level=level,
            factor_breakdown=factor_scores,
            explanation=explanation,
            recommendations=recommendations,
            metadata={"debug": settings.CONFIDENCE_DEBUG, "latency_ms": latency_ms}
        )

confidence_engine = ConfidenceEngineService()
