import unittest
import requests
import random
import time
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.services.self_reflector import self_reflector
from app.schemas.self_reflection import SelfReflectionResult
from app.schemas.answer_verification import AnswerVerificationResult, ClaimVerificationResult
from app.schemas.hallucination import HallucinationDetectionResult

BASE_URL = "http://localhost:8000/api"

class SelfReflectionUnitTest(unittest.TestCase):
    def test_empty_and_edge_cases(self):
        # Empty answer
        res = self_reflector.reflect("question", "", [])
        self.assertEqual(res.original_answer, "")
        self.assertEqual(res.quality_score, 1.0)
        self.assertFalse(res.refinement_performed)

    def test_rule_based_quality_scoring(self):
        # Mock verification and hallucination inputs
        h_detect = HallucinationDetectionResult(
            hallucination_status="FAILED",
            confidence_score=0.90,
            unsupported_claims=["Paris is the capital of England."],
            grounded_claims=["Factual statement is valid."],
            reasoning="Severe hallucination detected."
        )
        
        a_verify = AnswerVerificationResult(
            verified=False,
            overall_verification_score=0.50,
            claim_verifications=[
                ClaimVerificationResult(
                    claim_id="claim_1",
                    claim_text="Paris is the capital of England.",
                    verification_label="CONTRADICTED",
                    confidence_score=0.90,
                    supporting_chunks=[],
                    evidence_text="",
                    explanation=""
                ),
                ClaimVerificationResult(
                    claim_id="claim_2",
                    claim_text="Factual statement is valid.",
                    verification_label="VERIFIED",
                    confidence_score=0.95,
                    supporting_chunks=["c1"],
                    evidence_text="Factual statement is valid.",
                    explanation=""
                )
            ],
            verification_summary="",
            claim_count=2,
            verified_count=1,
            partially_supported_count=0,
            unsupported_count=0,
            contradicted_count=1,
            latency_ms=10
        )
        
        # Rule-based calculation:
        # Base: 1.0
        # Hallucination FAILED: -0.4
        # Verification score (0.50): - (1.0 - 0.50) * 0.4 = -0.20
        # Expected score: 1.0 - 0.4 - 0.20 = 0.40
        res = self_reflector._reflect_with_rules(
            "question",
            "Paris is the capital of England. Factual statement is valid.",
            [],
            h_detect,
            a_verify,
            time.time()
        )
        
        self.assertEqual(res.quality_score, 0.40)
        self.assertTrue(res.refinement_performed)
        # Refined answer should have removed the contradicted claim "Paris is the capital of England."
        self.assertNotIn("Paris is the capital of England.", res.refined_answer)
        self.assertIn("Factual statement is valid.", res.refined_answer)

    def test_no_refinement_mode(self):
        old_val = settings.ENABLE_ANSWER_REFINEMENT
        settings.ENABLE_ANSWER_REFINEMENT = False
        try:
            h_detect = HallucinationDetectionResult(
                hallucination_status="FAILED",
                confidence_score=0.90,
                unsupported_claims=["Paris is the capital of England."],
                grounded_claims=["Factual statement is valid."],
                reasoning=""
            )
            res = self_reflector.reflect(
                "question",
                "Paris is the capital of England. Factual statement is valid.",
                [],
                h_detect,
                None
            )
            # Refinement should be disabled, returning original answer
            self.assertFalse(res.refinement_performed)
            self.assertEqual(res.refined_answer, "Paris is the capital of England. Factual statement is valid.")
        finally:
            settings.ENABLE_ANSWER_REFINEMENT = old_val


class SelfReflectionIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"sr_user_{cls.rand_id}@example.com"
        cls.password = "srpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Upload a test document
        doc_content = "Self-Reflection Engine evaluates generated responses."
        files = {"file": ("test_sr_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for indexing
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_chat_endpoint_reflection_metadata(self):
        chat_req = {
            "question": "What is Self-Reflection?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify self_reflection field is present in response
        self.assertIn("self_reflection", data)
        sr = data["self_reflection"]
        self.assertIsNotNone(sr)
        self.assertIn("quality_score", sr)
        self.assertIn("refinement_performed", sr)
        self.assertIn("original_answer", sr)

    def test_search_endpoint_reflection_metadata(self):
        search_req = {
            "query": "Self-Reflection"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify self_reflection field is present in search response (even if null/None)
        self.assertIn("self_reflection", data)
