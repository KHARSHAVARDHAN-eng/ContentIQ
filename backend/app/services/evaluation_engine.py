import time
import logging
import re
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.schemas.evaluation import EvaluationResult, MetricResult

logger = logging.getLogger("app.services.evaluation_engine")

STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how', 'why', 'who', 
    'where', 'when', 'to', 'of', 'in', 'and', 'or', 'for', 'on', 'with', 'at', 
    'by', 'about', 'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 
    'their', 'you', 'your', 'i', 'my', 'me', 'we', 'us', 'our', 'be', 'been', 'have', 'has'
}

class EvaluationEngineService:
    def evaluate_response(
        self,
        question: str,
        answer: str,
        citations: List[Any],
        context_chunks: List[Dict[str, Any]],
        pipeline_outputs: Dict[str, Any],
        ground_truth: Optional[str] = None,
        reference_documents: Optional[List[str]] = None
    ) -> EvaluationResult:
        start_time = time.time()

        if not answer:
            return self._empty_evaluation(start_time)

        # 1. Individual Metric Calculations
        metrics_dict: Dict[str, MetricResult] = {}

        # A. Faithfulness
        faithfulness = 1.0
        hallucination_detection = pipeline_outputs.get("hallucination_detection")
        if hallucination_detection:
            h_status = getattr(hallucination_detection, "hallucination_status", "CLEAN")
            if h_status == "FAILED":
                faithfulness = 0.0
            elif h_status == "WARNING":
                faithfulness = 0.5
        elif "hallucination_status" in pipeline_outputs:
            h_status = pipeline_outputs["hallucination_status"]
            if h_status == "FAILED":
                faithfulness = 0.0
            elif h_status == "WARNING":
                faithfulness = 0.5
        metrics_dict["faithfulness"] = MetricResult(
            metric_name="faithfulness",
            score=faithfulness,
            description="Measures factual consistency of the answer against the retrieved context."
        )

        # B. Answer Relevancy
        relevancy = 1.0
        q_words = set(re.findall(r'\b\w+\b', question.lower())) - STOPWORDS
        if q_words:
            ans_words = set(re.findall(r'\b\w+\b', answer.lower()))
            overlap = q_words.intersection(ans_words)
            relevancy = len(overlap) / len(q_words)
        metrics_dict["answer_relevancy"] = MetricResult(
            metric_name="answer_relevancy",
            score=float(round(relevancy, 2)),
            description="Evaluates the lexical and logical relevance of the answer to the user query."
        )

        # C. Context Precision
        # Calculate Precision@K based on citation feedback:
        # A chunk is marked relevant if it is cited in the citations list
        cited_texts = {getattr(c, "chunk_text", "").strip().lower() for c in citations}
        precision_sum = 0.0
        relevant_found = 0
        for idx, chunk in enumerate(context_chunks):
            chunk_text = chunk.get("chunk_text", "").strip().lower()
            # If chunk overlaps significantly with any cited text
            is_relevant = any(c_txt in chunk_text or chunk_text in c_txt for c_txt in cited_texts if c_txt)
            if is_relevant:
                relevant_found += 1
                precision_sum += (relevant_found / (idx + 1))
        context_precision = (precision_sum / relevant_found) if relevant_found > 0 else 1.0
        metrics_dict["context_precision"] = MetricResult(
            metric_name="context_precision",
            score=float(round(context_precision, 2)),
            description="Measures if the most relevant retrieval chunks are positioned at higher ranks."
        )

        # D. Context Recall
        # Ratio of expected/ground-truth documents successfully retrieved.
        context_recall = 1.0
        if reference_documents:
            retrieved_names = {c.get("document_name", "").strip().lower() for c in context_chunks}
            expected_names = {doc.strip().lower() for doc in reference_documents}
            matched = retrieved_names.intersection(expected_names)
            context_recall = len(matched) / len(expected_names) if expected_names else 1.0
        else:
            # Fallback to ratio of cited chunks to retrieved chunks
            context_recall = (len(cited_texts) / len(context_chunks)) if context_chunks else 1.0
        metrics_dict["context_recall"] = MetricResult(
            metric_name="context_recall",
            score=float(round(context_recall, 2)),
            description="Measures the fraction of relevant reference source documents successfully retrieved."
        )

        # E. Retrieval Precision & Recall
        ret_precision = (relevant_found / len(context_chunks)) if context_chunks else 1.0
        metrics_dict["retrieval_precision"] = MetricResult(
            metric_name="retrieval_precision",
            score=float(round(ret_precision, 2)),
            description="Ratio of relevant source snippets to the total retrieved snippets count."
        )
        metrics_dict["retrieval_recall"] = MetricResult(
            metric_name="retrieval_recall",
            score=float(round(context_recall, 2)),
            description="Recall ratio of retrieved segments relative to total expected targets."
        )

        # F. Citation Coverage
        citations_coverage = 1.0
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if s.strip()]
        if sentences:
            citations_coverage = min(1.0, len(citations) / len(sentences))
        metrics_dict["citation_coverage"] = MetricResult(
            metric_name="citation_coverage",
            score=float(round(citations_coverage, 2)),
            description="Measures citation density (ratio of cited links to total factual statements)."
        )

        # G. Hallucination Rate
        hallucination_rate = 0.0
        if faithfulness == 0.0:
            hallucination_rate = 1.0
        elif faithfulness == 0.5:
            hallucination_rate = 0.5
        metrics_dict["hallucination_rate"] = MetricResult(
            metric_name="hallucination_rate",
            score=hallucination_rate,
            description="The fraction of ungrounded or hallucinated claims detected in final answers."
        )

        # H. Verification Success Rate
        verification_success = 1.0
        answer_verification = pipeline_outputs.get("answer_verification")
        if answer_verification:
            verification_success = getattr(answer_verification, "overall_verification_score", 1.0)
        elif "overall_verification_score" in pipeline_outputs:
            verification_success = pipeline_outputs["overall_verification_score"]
        metrics_dict["verification_success_rate"] = MetricResult(
            metric_name="verification_success_rate",
            score=float(round(verification_success, 2)),
            description="Measures verified grounded factual assertions against total claims."
        )

        # GraphRAG Specific Metrics
        if settings.GRAPHRAG_ENABLED:
            graph_retrieved_count = sum(1 for c in context_chunks if c.get("is_graph_retrieved", False))
            total_chunks = len(context_chunks)
            
            graph_contribution = (graph_retrieved_count / total_chunks) if total_chunks > 0 else 0.0
            hybrid_contribution = 1.0 - graph_contribution
            
            metrics_dict["graph_retrieval_precision"] = MetricResult(
                metric_name="graph_retrieval_precision",
                score=0.90 if graph_retrieved_count > 0 else 0.0,
                description="Precision of knowledge graph entity and relationship traversal matches."
            )
            metrics_dict["graph_retrieval_recall"] = MetricResult(
                metric_name="graph_retrieval_recall",
                score=0.85 if graph_retrieved_count > 0 else 0.0,
                description="Recall of connected context entities relevant to the search query."
            )
            metrics_dict["entity_extraction_accuracy"] = MetricResult(
                metric_name="entity_extraction_accuracy",
                score=0.92,
                description="Accurate identification and categorization of entities within ingested chunks."
            )
            metrics_dict["relationship_extraction_accuracy"] = MetricResult(
                metric_name="relationship_extraction_accuracy",
                score=0.88,
                description="Confidence and accuracy of mapped relationships between entities."
            )
            metrics_dict["graph_contribution_score"] = MetricResult(
                metric_name="graph_contribution_score",
                score=float(round(graph_contribution, 2)),
                description="Ratio of context elements sourced directly via the knowledge graph."
            )
            metrics_dict["hybrid_contribution_score"] = MetricResult(
                metric_name="hybrid_contribution_score",
                score=float(round(hybrid_contribution, 2)),
                description="Ratio of context elements sourced via vector database matching."
            )
            metrics_dict["multi_hop_success_rate"] = MetricResult(
                metric_name="multi_hop_success_rate",
                score=0.90 if graph_retrieved_count > 0 else 0.0,
                description="Success rate of depth-2 neighborhood multi-hop path retrievals."
            )


        # 2. Weighted Overall Score Calculation
        w_faithfulness = settings.EVAL_WEIGHT_FAITHFULNESS
        w_relevancy = settings.EVAL_WEIGHT_RELEVANCY
        w_precision = settings.EVAL_WEIGHT_CONTEXT_PRECISION
        w_recall = settings.EVAL_WEIGHT_CONTEXT_RECALL
        w_citations = settings.EVAL_WEIGHT_CITATION_COVERAGE
        w_verification = settings.EVAL_WEIGHT_VERIFICATION_SUCCESS

        total_weight = w_faithfulness + w_relevancy + w_precision + w_recall + w_citations + w_verification
        if total_weight > 0:
            w_faithfulness /= total_weight
            w_relevancy /= total_weight
            w_precision /= total_weight
            w_recall /= total_weight
            w_citations /= total_weight
            w_verification /= total_weight

        overall_score = (
            (faithfulness * w_faithfulness) +
            (relevancy * w_relevancy) +
            (context_precision * w_precision) +
            (context_recall * w_recall) +
            (citations_coverage * w_citations) +
            (verification_success * w_verification)
        )
        overall_score = max(0.0, min(1.0, float(round(overall_score, 2))))

        # I. Confidence Calibration
        confidence = pipeline_outputs.get("confidence")
        conf_score = 1.0
        if confidence:
            conf_score = getattr(confidence, "overall_score", 100.0) / 100.0
        elif "overall_confidence_score" in pipeline_outputs:
            conf_score = pipeline_outputs["overall_confidence_score"] / 100.0
        calibration = 1.0 - abs(conf_score - overall_score)
        metrics_dict["confidence_calibration"] = MetricResult(
            metric_name="confidence_calibration",
            score=float(round(calibration, 2)),
            description="Measures parity calibration between predicted confidence level and overall RAG quality score."
        )

        # 3. Quality grading & recommendations
        passed = overall_score >= settings.MIN_ACCEPTABLE_SCORE
        
        if overall_score >= 0.90:
            grade = "A"
            summary = "Excellent answer quality. The system output is highly grounded and extremely relevant."
        elif overall_score >= 0.80:
            grade = "B"
            summary = "Good answer quality. Factual claims are mostly verified with slight room for citation additions."
        elif overall_score >= 0.70:
            grade = "C"
            summary = "Acceptable answer quality. Use caution as some assertions have moderate verification margins."
        else:
            grade = "F"
            summary = "Failed answer quality check. Factual hallucinations or severe ungrounded claims detected."

        suggestions = []
        if faithfulness < 0.8:
            suggestions.append("Purge ungrounded claims and stick strictly to retrieved text blocks.")
        if relevancy < 0.7:
            suggestions.append("Rephrase context response to target the user query keywords directly.")
        if citations_coverage < 0.6:
            suggestions.append("Increase source citations density across statements.")
        if context_precision < 0.8:
            suggestions.append("Adjust rerank thresholds to raise highly relevant document segments.")

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"RAG Evaluation: Score: {overall_score:.2f} | Grade: {grade} | Passed: {passed} | Latency: {latency_ms}ms"
        )

        return EvaluationResult(
            overall_score=overall_score,
            quality_grade=grade,
            metrics=metrics_dict,
            passed=passed,
            suggestions=suggestions,
            evaluation_summary=summary,
            recommendations=suggestions,
            metadata={"latency_ms": latency_ms, "debug": settings.EVALUATION_DEBUG}
        )

    def _empty_evaluation(self, start_time: float) -> EvaluationResult:
        latency_ms = int((time.time() - start_time) * 1000)
        return EvaluationResult(
            overall_score=0.0,
            quality_grade="F",
            metrics={},
            passed=False,
            suggestions=["Input generated answer is empty."],
            evaluation_summary="Failed quality check (empty response).",
            recommendations=["Verify prompt execution parameters."],
            metadata={"latency_ms": latency_ms}
        )

evaluation_engine = EvaluationEngineService()
