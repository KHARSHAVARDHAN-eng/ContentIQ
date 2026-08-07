import unittest
import requests
import random
import time
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.services.confidence_engine import confidence_engine
from app.schemas.confidence import ConfidenceResult
from app.schemas.retrieval_verification import RetrievalVerificationResult
from app.schemas.hallucination import HallucinationDetectionResult
from app.schemas.answer_verification import AnswerVerificationResult
from app.schemas.self_reflection import SelfReflectionResult

BASE_URL = "http://localhost:8000/api"

class ConfidenceEngineUnitTest(unittest.TestCase):
    def test_score_aggregation_and_weighting(self):
        # We simulate pipeline outputs:
        # Retrieval verification: 1.0 (weight 0.15)
        # Reranking raw score: 0.80 (weight 0.15)
        # Hallucination status CLEAN: 1.0 (weight 0.20)
        # Answer Verification: 1.0 (weight 0.20)
        # Self reflection quality score: 1.0 (weight 0.15)
        # Citation coverage: 1 sentence, 1 citation -> 1.0 (weight 0.15)
        
        # All factor scores normalized are 1.0 (rerank 0.80 -> 0.80).
        # Weighted sum: 0.15*1.0 + 0.15*0.80 + 0.20*1.0 + 0.20*1.0 + 0.15*1.0 + 0.15*1.0 = 0.97.
        # Score = 97.0
        
        retrieval = RetrievalVerificationResult(
            quality_score=1.0,
            verification_status="PASS",
            retrieval_confidence=1.0,
            verification_reason="",
            recommended_action="Continue normally"
        )
        
        h_detect = HallucinationDetectionResult(
            hallucination_status="CLEAN",
            confidence_score=0.95,
            unsupported_claims=[],
            grounded_claims=["Factual sentence is valid."],
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
        
        self_reflection = SelfReflectionResult(
            reflection_summary="",
            detected_issues=[],
            improvement_suggestions=[],
            quality_score=1.0,
            refinement_performed=False,
            original_answer="Factual sentence is valid.",
            refined_answer="Factual sentence is valid.",
            confidence=0.9
        )
        
        res = confidence_engine.compute_confidence(
            answer="Factual sentence is valid.",
            citations=["citation_1"],
            retrieval_verification=retrieval,
            reranking=None,
            hallucination_detection=h_detect,
            answer_verification=a_verify,
            self_reflection=self_reflection
        )
        
        self.assertEqual(res.overall_score, 97.0)
        self.assertEqual(res.confidence_level, "HIGH")
        self.assertIn("Factual grounding, citation coverage", res.explanation)

    def test_level_classification_low(self):
        # We simulate low values
        # Hallucination FAILED -> 0.0
        # Answer verification score -> 0.0
        # Quality score -> 0.0
        h_detect = HallucinationDetectionResult(
            hallucination_status="FAILED",
            confidence_score=0.90,
            unsupported_claims=["Paris is the capital of England."],
            grounded_claims=[],
            reasoning=""
        )
        
        a_verify = AnswerVerificationResult(
            verified=False,
            overall_verification_score=0.0,
            claim_verifications=[],
            verification_summary="",
            claim_count=1,
            verified_count=0,
            partially_supported_count=0,
            unsupported_count=1,
            contradicted_count=0,
            latency_ms=10
        )
        
        res = confidence_engine.compute_confidence(
            answer="Paris is the capital of England.",
            citations=[],
            retrieval_verification=None,
            reranking=None,
            hallucination_detection=h_detect,
            answer_verification=a_verify,
            self_reflection=None
        )
        
        # Most generative parameters are 0.0. The overall score should be below 50.0 (MEDIUM/LOW thresholds).
        self.assertTrue(res.overall_score < 50.0)
        self.assertEqual(res.confidence_level, "LOW")

    def test_disabled_scoring_bypass(self):
        old_val = settings.CONFIDENCE_SCORING_ENABLED
        settings.CONFIDENCE_SCORING_ENABLED = False
        try:
            # Although API controller maps it or engine computes it when direct service is called,
            # settings can bypass execution. 
            # Calling compute_confidence directly is always active.
            res = confidence_engine.compute_confidence("Answer.", [])
            self.assertIsNotNone(res.overall_score)
        finally:
            settings.CONFIDENCE_SCORING_ENABLED = old_val


class ConfidenceScoringIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"cs_user_{cls.rand_id}@example.com"
        cls.password = "cspassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Upload a test document
        doc_content = "Confidence scoring evaluates overall factual metrics."
        files = {"file": ("test_cs_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for indexing
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_chat_endpoint_confidence_metadata(self):
        chat_req = {
            "question": "What is Confidence scoring?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify confidence field is present in response
        self.assertIn("confidence", data)
        cs = data["confidence"]
        self.assertIsNotNone(cs)
        self.assertIn("overall_score", cs)
        self.assertIn("confidence_level", cs)
        self.assertIn("factor_breakdown", cs)

    def test_search_endpoint_confidence_metadata(self):
        search_req = {
            "query": "Confidence scoring"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify confidence field is present in search response (even if null/None)
        self.assertIn("confidence", data)
        self.assertIsNone(data["confidence"])
