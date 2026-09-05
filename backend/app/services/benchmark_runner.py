import time
import json
import logging
from typing import List, Dict, Any, Optional

from app.services.evaluation_engine import evaluation_engine
from app.schemas.evaluation import BenchmarkStats

logger = logging.getLogger("app.services.benchmark_runner")

class BenchmarkRunnerService:
    def run_benchmark(
        self,
        dataset_path: str,
        rag_client_fn: Any  # A callable function that takes a query string and returns RAG outputs
    ) -> BenchmarkStats:
        start_time = time.time()
        
        try:
            with open(dataset_path, "r") as f:
                dataset = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load benchmark dataset from {dataset_path}: {e}")
            raise ValueError(f"Invalid dataset path: {dataset_path}")

        total_queries = len(dataset)
        if total_queries == 0:
            return BenchmarkStats(
                dataset_name=dataset_path,
                run_timestamp=start_time,
                total_queries=0,
                average_overall_score=0.0,
                metric_averages={},
                quality_grade_distribution={"A": 0, "B": 0, "C": 0, "F": 0},
                pass_rate=0.0
            )

        overall_scores_sum = 0.0
        metric_sums: Dict[str, float] = {}
        grade_distribution = {"A": 0, "B": 0, "C": 0, "F": 0}
        passed_count = 0

        for item in dataset:
            question = item.get("question", "")
            reference_documents = item.get("expected_documents", [])
            ground_truth = item.get("ground_truth", "")

            # Execute the RAG pipeline output callable
            try:
                rag_output = rag_client_fn(question)
            except Exception as e:
                logger.error(f"Error running pipeline on query '{question}': {e}")
                continue

            answer = rag_output.get("answer", "")
            citations = rag_output.get("citations", [])
            context_chunks = rag_output.get("context_chunks", [])
            
            # Map pipeline stages to expected structure
            pipeline_outputs = {
                "hallucination_detection": rag_output.get("hallucination_detection"),
                "answer_verification": rag_output.get("answer_verification"),
                "confidence": rag_output.get("confidence")
            }

            # Evaluate response
            eval_res = evaluation_engine.evaluate_response(
                question=question,
                answer=answer,
                citations=citations,
                context_chunks=context_chunks,
                pipeline_outputs=pipeline_outputs,
                ground_truth=ground_truth,
                reference_documents=reference_documents
            )

            # Sum statistics
            overall_scores_sum += eval_res.overall_score
            grade_distribution[eval_res.quality_grade] = grade_distribution.get(eval_res.quality_grade, 0) + 1
            if eval_res.passed:
                passed_count += 1

            for m_name, m_val in eval_res.metrics.items():
                if m_val.score is not None:
                    metric_sums[m_name] = metric_sums.get(m_name, 0.0) + m_val.score

        # Calculate averages
        avg_overall = overall_scores_sum / total_queries
        metric_averages = {k: v / total_queries for k, v in metric_sums.items()}
        pass_rate = passed_count / total_queries

        # Detection of potential regression alerts
        warnings = []
        if avg_overall < 0.75:
            warnings.append(f"Performance regression risk: average quality score is low ({avg_overall:.2f})")
        if pass_rate < 0.80:
            warnings.append(f"Pass rate is below target SLA: {pass_rate:.1%}")

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Benchmark completed: Dataset: {dataset_path} | Overall Avg: {avg_overall:.2f} | "
            f"Pass Rate: {pass_rate:.1%} | Runs: {total_queries} | Latency: {latency_ms}ms"
        )

        return BenchmarkStats(
            dataset_name=dataset_path,
            run_timestamp=start_time,
            total_queries=total_queries,
            average_overall_score=float(round(avg_overall, 2)),
            metric_averages={k: float(round(v, 2)) for k, v in metric_averages.items()},
            quality_grade_distribution=grade_distribution,
            pass_rate=float(round(pass_rate, 2)),
            regression_warnings=warnings
        )

benchmark_runner = BenchmarkRunnerService()
