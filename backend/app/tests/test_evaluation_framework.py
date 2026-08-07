import unittest
import json
import os
import random
import time
import requests

from app.core.config import settings
from app.services.evaluation_engine import evaluation_engine
from app.services.benchmark_runner import benchmark_runner
from app.schemas.evaluation import EvaluationResult, BenchmarkStats
from app.schemas.retrieval_verification import RetrievalVerificationResult
from app.schemas.hallucination import HallucinationDetectionResult
from app.schemas.answer_verification import AnswerVerificationResult
from app.schemas.confidence import ConfidenceResult

BASE_URL = "http://localhost:8000/api"

class RAGEvaluationUnitTest(unittest.TestCase):
    def test_empty_answer(self):
        res = evaluation_engine.evaluate_response("question", "", [], [], {})
        self.assertEqual(res.overall_score, 0.0)
        self.assertEqual(res.quality_grade, "F")
        self.assertFalse(res.passed)

    def test_metrics_calculation(self):
        # Setup inputs
        h_detect = HallucinationDetectionResult(
            hallucination_status="CLEAN",
            confidence_score=0.95,
            unsupported_claims=[],
            grounded_claims=["This is a verified fact."],
            reasoning=""
        )

        a_verify = AnswerVerificationResult(
            verified=True,
            overall_verification_score=1.0,
            claim_verifications=[],
            verification_summary="",
            claim_count=1,
            verified_count=1,
            partially_supported_count=0,
            unsupported_count=0,
            contradicted_count=0,
            latency_ms=10
        )

        confidence = ConfidenceResult(
            overall_score=95.0,
            confidence_level="HIGH",
            factor_breakdown=[],
            explanation="",
            recommendations=[]
        )

        pipeline_outputs = {
            "hallucination_detection": h_detect,
            "answer_verification": a_verify,
            "confidence": confidence
        }

        # Mock citations matching the chunk
        citations = [
            type('Citation', (object,), {
                "chunk_text": "This is a verified fact."
            })()
        ]

        context_chunks = [
            {"chunk_text": "This is a verified fact.", "document_name": "doc_1.txt"}
        ]

        res = evaluation_engine.evaluate_response(
            question="What is a verified fact?",
            answer="This is a verified fact.",
            citations=citations,
            context_chunks=context_chunks,
            pipeline_outputs=pipeline_outputs,
            ground_truth="This is a verified fact.",
            reference_documents=["doc_1.txt"]
        )

        self.assertTrue(res.overall_score >= 0.90)
        self.assertEqual(res.quality_grade, "A")
        self.assertTrue(res.passed)
        self.assertIn("faithfulness", res.metrics)
        self.assertEqual(res.metrics["faithfulness"].score, 1.0)
        self.assertEqual(res.metrics["citation_coverage"].score, 1.0)

    def test_offline_benchmark_runner(self):
        # Create temp JSON dataset
        temp_dir = "/Users/harsha/.gemini/antigravity-ide/brain/7d488ed6-6121-4a74-88a6-64118b73eaf6/scratch"
        os.makedirs(temp_dir, exist_ok=True)
        dataset_path = os.path.join(temp_dir, "test_eval_dataset.json")

        test_data = [
            {
                "question": "What is ContentIQ?",
                "expected_documents": ["doc_a.txt"],
                "ground_truth": "ContentIQ is a stable pipeline redesign."
            }
        ]

        with open(dataset_path, "w") as f:
            json.dump(test_data, f)

        # Mock pipeline output callback
        def mock_rag(question):
            return {
                "answer": "ContentIQ is a stable pipeline redesign.",
                "citations": [
                    type('Citation', (object,), {
                        "chunk_text": "ContentIQ is a stable pipeline redesign."
                    })()
                ],
                "context_chunks": [
                    {
                        "chunk_text": "ContentIQ is a stable pipeline redesign.",
                        "document_name": "doc_a.txt"
                    }
                ],
                "hallucination_detection": None,
                "answer_verification": None,
                "confidence": None
            }

        try:
            stats = benchmark_runner.run_benchmark(dataset_path, mock_rag)
            self.assertEqual(stats.total_queries, 1)
            self.assertTrue(stats.average_overall_score > 0.8)
            self.assertEqual(stats.quality_grade_distribution["A"], 1)
            self.assertEqual(stats.pass_rate, 1.0)
        finally:
            if os.path.exists(dataset_path):
                os.remove(dataset_path)


class RAGEvaluationIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"eval_user_{cls.rand_id}@example.com"
        cls.password = "evalpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Upload a test document
        doc_content = "Enterprise RAG Evaluation computes performance grading metrics."
        files = {"file": ("test_eval_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for indexing
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_chat_endpoint_evaluation_metadata(self):
        chat_req = {
            "question": "What is Enterprise RAG Evaluation?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify evaluation field is present in response
        self.assertIn("evaluation", data)
        ev = data["evaluation"]
        self.assertIsNotNone(ev)
        self.assertIn("overall_score", ev)
        self.assertIn("quality_grade", ev)
        self.assertIn("metrics", ev)

    def test_search_endpoint_evaluation_metadata(self):
        search_req = {
            "query": "Enterprise RAG Evaluation"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify evaluation field is present in search response (even if null/None)
        self.assertIn("evaluation", data)
        self.assertIsNone(data["evaluation"])
