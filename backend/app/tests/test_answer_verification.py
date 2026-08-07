import unittest
import requests
import random
import time
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.services.claim_extractor import claim_extractor
from app.services.answer_verifier import answer_verifier
from app.schemas.answer_verification import AnswerVerificationResult

BASE_URL = "http://localhost:8000/api"

class AnswerVerificationUnitTest(unittest.TestCase):
    def test_claim_extraction_rules(self):
        answer = "Hello! Sure, I can help. Factual claim one is true. Factual claim two is false? Factual claim three is valid."
        claims = claim_extractor._extract_with_rules(answer)
        
        # Greetings and questions must be ignored, and short sentences are filtered out.
        # "Factual claim one is true." (26 chars), "Factual claim three is valid." (29 chars) should be kept.
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0]["claim_id"], "claim_1")
        self.assertEqual(claims[0]["claim_text"], "Factual claim one is true.")
        self.assertEqual(claims[1]["claim_text"], "Factual claim three is valid.")

    def test_empty_and_edge_cases(self):
        # Empty answer
        res = answer_verifier.verify("", [])
        self.assertEqual(res.claim_count, 0)
        self.assertEqual(res.overall_verification_score, 1.0)
        self.assertTrue(res.verified)

        # Empty context
        res = answer_verifier.verify("The capital of France is Paris.", [])
        self.assertEqual(res.claim_count, 1)
        self.assertEqual(res.overall_verification_score, 0.0)
        self.assertEqual(res.claim_verifications[0].verification_label, "UNSUPPORTED")
        self.assertFalse(res.verified)

    def test_supported_and_partial_claims_rules(self):
        # We test verification classification using rule-based fallback
        chunks = [
            {"chunk_id": "c1", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.9, "chunk_text": "France has its capital in Paris."}
        ]
        
        # We patch embedding_service and cosine similarity to simulate exact scores
        # Claim 1: "Paris is the capital of France." -> high similarity to the chunk sentence
        # Claim 2: "Paris is mostly the capital." -> moderate similarity
        
        with patch("app.services.answer_verifier.AnswerVerifierService._cosine_similarity") as mock_sim:
            # We have 1 chunk sentence, so we get 1 call per claim
            # First claim returns 0.90 (high similarity)
            # Second claim returns 0.70 (moderate similarity)
            mock_sim.side_effect = [0.90, 0.70]
            
            res = answer_verifier.verify(
                "Paris is the capital of France. Paris is mostly the capital.",
                chunks
            )
            
            self.assertEqual(res.claim_count, 2)
            self.assertEqual(res.claim_verifications[0].verification_label, "VERIFIED")
            self.assertEqual(res.claim_verifications[0].confidence_score, 0.90)
            self.assertEqual(res.claim_verifications[1].verification_label, "PARTIALLY_SUPPORTED")
            self.assertEqual(res.claim_verifications[1].confidence_score, 0.70)
            
            # Score calculation: (1 + 0.5 * 1) / 2 = 0.75
            self.assertEqual(res.overall_verification_score, 0.75)
            self.assertTrue(res.verified)

    def test_contradicted_and_unsupported_claims_rules(self):
        chunks = [
            {"chunk_id": "c1", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.9, "chunk_text": "The company reported a profit of 10 million dollars."}
        ]
        
        # Claim 1: "The company did not report a profit of 10 million dollars." (Contains "not" -> negated)
        # Claim 2: "Bananas are yellow." -> low similarity (0.20)
        
        with patch("app.services.answer_verifier.AnswerVerifierService._cosine_similarity") as mock_sim:
            # First claim returns 0.88 similarity, but has negation mismatch compared to context ("did not report" vs "reported")
            # Second claim returns 0.20 similarity
            mock_sim.side_effect = [0.88, 0.20]
            
            res = answer_verifier.verify(
                "The company did not report a profit. Bananas are yellow.",
                chunks
            )
            
            self.assertEqual(res.claim_count, 2)
            self.assertEqual(res.claim_verifications[0].verification_label, "CONTRADICTED")
            self.assertEqual(res.claim_verifications[1].verification_label, "UNSUPPORTED")
            
            # Score: (0 + 0) / 2 = 0.0
            self.assertEqual(res.overall_verification_score, 0.0)
            self.assertFalse(res.verified)

    def test_disabled_bypass_setting(self):
        old_enabled = settings.ANSWER_VERIFICATION_ENABLED
        settings.ANSWER_VERIFICATION_ENABLED = False
        try:
            chunks = [
                {"chunk_id": "c1", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.9, "chunk_text": "Factual statement is valid."}
            ]
            # When disabled, if Gemini API key is missing or we mock verification, it should fallback to rule-based verification since rule-based is always active as a validator.
            # Let's ensure that rule-based works perfectly when LLM verification is bypassed.
            res = answer_verifier.verify("Factual statement is valid.", chunks)
            self.assertEqual(res.claim_count, 1)
        finally:
            settings.ANSWER_VERIFICATION_ENABLED = old_enabled


class AnswerVerificationIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"av_user_{cls.rand_id}@example.com"
        cls.password = "avpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Upload a test document
        doc_content = "Answer Verification verifies every claim in the generated answer."
        files = {"file": ("test_av_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for indexing
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_chat_endpoint_verification_metadata(self):
        chat_req = {
            "question": "What does Answer Verification verify?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify answer_verification field is present in response
        self.assertIn("answer_verification", data)
        av = data["answer_verification"]
        self.assertIsNotNone(av)
        self.assertIn("overall_verification_score", av)
        self.assertIn("claim_verifications", av)
        self.assertIn("claim_count", av)
        self.assertIn("verified_count", av)

    def test_search_endpoint_verification_metadata(self):
        search_req = {
            "query": "Answer Verification"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify answer_verification field is present in search response (even if null/None)
        self.assertIn("answer_verification", data)
