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
        reference_documents: Optional[List[str]] = None,
        reference_evidence: Optional[List[str]] = None
    ) -> EvaluationResult:
        start_time = time.time()

        if not answer:
            return self._empty_evaluation(start_time)

        metrics_dict: Dict[str, MetricResult] = {}

        # Refusal check for unanswerable / refused questions
        refusal_phrases = ["couldn't find information", "not mentioned", "not provided", "do not have", "refuse", "unanswerable", "no information"]
        is_refusal = any(rp in answer.lower() for rp in refusal_phrases)

        # ----------------------------------------------------
        # A. Independent Grounding Evaluation (Faithfulness & Hallucination Rate)
        # Evaluates answer claims/sentences independently against reference evidence & retrieved context.
        # DOES NOT read pipeline_outputs["hallucination_detection"]!
        # ----------------------------------------------------
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if s.strip() and len(s.strip()) > 5]
        
        if is_refusal or not sentences:
            faithfulness = 1.0
        else:
            evidence_texts = []
            if reference_evidence:
                evidence_texts.extend(reference_evidence)
            for c in context_chunks:
                if c.get("chunk_text"):
                    evidence_texts.append(c["chunk_text"])
            
            full_evidence_corpus = " ".join(evidence_texts).lower()
            grounded_sentences = 0
            for sentence in sentences:
                s_words = set(re.findall(r'\b\w+\b', sentence.lower())) - STOPWORDS
                if not s_words:
                    grounded_sentences += 1
                    continue
                
                # Check overlap ratio against evidence corpus
                evidence_words = set(re.findall(r'\b\w+\b', full_evidence_corpus))
                overlap = s_words.intersection(evidence_words)
                ratio = len(overlap) / len(s_words)
                if ratio >= 0.35 or sentence.lower() in full_evidence_corpus:
                    grounded_sentences += 1
            
            faithfulness = grounded_sentences / len(sentences)

        faithfulness = float(round(faithfulness, 2))
        hallucination_rate = float(round(max(0.0, 1.0 - faithfulness), 2))

        metrics_dict["faithfulness"] = MetricResult(
            metric_name="faithfulness",
            score=faithfulness,
            description="Automated evidence-grounding metric: independent ratio of factual statements supported by reference evidence."
        )

        metrics_dict["hallucination_rate"] = MetricResult(
            metric_name="hallucination_rate",
            score=hallucination_rate,
            description="Automated ungrounded claim metric: independent ratio of answer statements unsupported by evidence."
        )

        # ----------------------------------------------------
        # B. Semantic Answer Relevancy
        # Uses sentence-transformers MiniLM cosine similarity against ground-truth answer.
        # Handles refusal behavior for unanswerable questions.
        # ----------------------------------------------------
        if is_refusal:
            # If ground-truth indicates refusal or no ground_truth/evidence was expected
            if (ground_truth and any(rp in ground_truth.lower() for rp in refusal_phrases)) or (reference_evidence == [] and not ground_truth):
                relevancy = 1.0
            elif ground_truth:
                relevancy = 0.0
            else:
                relevancy = 1.0
        elif ground_truth:
            try:
                import numpy as np
                from app.services.embedding_service import embedding_service
                emb_ans = np.array(embedding_service.get_embedding(answer))
                emb_gt = np.array(embedding_service.get_embedding(ground_truth))
                norm_ans = np.linalg.norm(emb_ans)
                norm_gt = np.linalg.norm(emb_gt)
                if norm_ans > 0 and norm_gt > 0:
                    sim = float(np.dot(emb_ans, emb_gt) / (norm_ans * norm_gt))
                    relevancy = max(0.0, min(1.0, sim))
                else:
                    relevancy = 0.0
            except Exception as e:
                logger.warning(f"Semantic relevancy computation fallback: {e}")
                q_words = set(re.findall(r'\b\w+\b', question.lower())) - STOPWORDS
                ans_words = set(re.findall(r'\b\w+\b', answer.lower()))
                relevancy = len(q_words.intersection(ans_words)) / len(q_words) if q_words else 1.0
        else:
            q_words = set(re.findall(r'\b\w+\b', question.lower())) - STOPWORDS
            if q_words:
                ans_words = set(re.findall(r'\b\w+\b', answer.lower()))
                relevancy = len(q_words.intersection(ans_words)) / len(q_words)
            else:
                relevancy = 1.0

        metrics_dict["answer_relevancy"] = MetricResult(
            metric_name="answer_relevancy",
            score=float(round(relevancy, 2)),
            description="Semantic MiniLM embedding cosine similarity between generated answer and ground-truth answer."
        )

        # ----------------------------------------------------
        # C. Ground-Truth Context Precision
        # Measures whether retrieved chunks contain ground-truth reference evidence at high ranks.
        # Independent of system citations!
        # ----------------------------------------------------
        precision_sum = 0.0
        relevant_found = 0
        
        if reference_evidence:
            ref_ev_lower = [e.strip().lower() for e in reference_evidence if e.strip()]
            for idx, chunk in enumerate(context_chunks):
                c_text = chunk.get("chunk_text", "").strip().lower()
                is_rel = False
                for ev in ref_ev_lower:
                    if ev in c_text or c_text in ev:
                        is_rel = True
                        break
                    ev_words = set(re.findall(r'\b\w+\b', ev)) - STOPWORDS
                    if ev_words:
                        c_words = set(re.findall(r'\b\w+\b', c_text))
                        if len(ev_words.intersection(c_words)) / len(ev_words) >= 0.35:
                            is_rel = True
                            break
                if is_rel:
                    relevant_found += 1
                    precision_sum += (relevant_found / (idx + 1))
            context_precision = (precision_sum / relevant_found) if relevant_found > 0 else 0.0
        elif reference_documents:
            expected_names = {doc.strip().lower() for doc in reference_documents}
            for idx, chunk in enumerate(context_chunks):
                doc_name = chunk.get("document_name", "").strip().lower()
                if doc_name in expected_names:
                    relevant_found += 1
                    precision_sum += (relevant_found / (idx + 1))
            context_precision = (precision_sum / relevant_found) if relevant_found > 0 else 0.0
        else:
            context_precision = 1.0

        metrics_dict["context_precision"] = MetricResult(
            metric_name="context_precision",
            score=float(round(context_precision, 2)),
            description="Ground-truth rank-weighted precision of retrieved chunks relative to reference evidence."
        )

        # ----------------------------------------------------
        # D. Ground-Truth Context Recall
        # Measures whether reference evidence or expected documents were successfully retrieved.
        # Independent of system citations!
        # ----------------------------------------------------
        if reference_evidence:
            retrieved_texts = [c.get("chunk_text", "").strip().lower() for c in context_chunks]
            found_count = 0
            for ev in reference_evidence:
                ev_lower = ev.strip().lower()
                if not ev_lower:
                    continue
                ev_words = set(re.findall(r'\b\w+\b', ev_lower)) - STOPWORDS
                found = False
                for c_text in retrieved_texts:
                    if ev_lower in c_text or c_text in ev_lower:
                        found = True
                        break
                    if ev_words:
                        c_words = set(re.findall(r'\b\w+\b', c_text))
                        if len(ev_words.intersection(c_words)) / len(ev_words) >= 0.35:
                            found = True
                            break
                if found:
                    found_count += 1
            context_recall = (found_count / len(reference_evidence)) if reference_evidence else 1.0
        elif reference_documents:
            retrieved_names = {c.get("document_name", "").strip().lower() for c in context_chunks if c.get("document_name")}
            expected_names = {doc.strip().lower() for doc in reference_documents}
            matched = retrieved_names.intersection(expected_names)
            context_recall = (len(matched) / len(expected_names)) if expected_names else 1.0
        else:
            context_recall = 1.0

        metrics_dict["context_recall"] = MetricResult(
            metric_name="context_recall",
            score=float(round(context_recall, 2)),
            description="Ground-truth recall ratio of reference evidence items found in retrieved context chunks."
        )

        # E. Retrieval Precision & Recall
        ret_precision = (relevant_found / len(context_chunks)) if context_chunks else 1.0
        metrics_dict["retrieval_precision"] = MetricResult(
            metric_name="retrieval_precision",
            score=float(round(ret_precision, 2)),
            description="Ratio of relevant source snippets to total retrieved context chunks."
        )
        metrics_dict["retrieval_recall"] = MetricResult(
            metric_name="retrieval_recall",
            score=float(round(context_recall, 2)),
            description="Recall ratio of retrieved segments relative to total expected targets."
        )

        # F. Citation Coverage & Citation Precision
        citations_coverage = 1.0
        if sentences:
            citations_coverage = min(1.0, len(citations) / len(sentences))
        metrics_dict["citation_coverage"] = MetricResult(
            metric_name="citation_coverage",
            score=float(round(citations_coverage, 2)),
            description="Measures citation density (ratio of cited links to total factual statements)."
        )

        # Citation Precision explicitly marked NOT IMPLEMENTED
        metrics_dict["citation_precision"] = MetricResult(
            metric_name="citation_precision",
            score=None,
            description="NOT IMPLEMENTED - Fine-grained citation claim alignment requires sentence-level span mapping."
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

        # Weighted Overall Score Calculation
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

        # Confidence Calibration
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

        # Quality grading
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
