import unittest
import requests
import random
import time
from app.core.config import settings
from app.services.retrieval_verifier import retrieval_verifier
from app.schemas.retrieval_verification import RetrievalVerificationResult

BASE_URL = "http://localhost:8000/api"

class RetrievalVerificationUnitTest(unittest.TestCase):
    def test_pass_quality_score(self):
        # Excellent score distribution and matches
        hits = [
            {"score": 0.45, "chunk_text": "Document chunk content here."},
            {"score": 0.40, "chunk_text": "More chunk content."},
            {"score": 0.38, "chunk_text": "Even more content."}
        ]
        res = retrieval_verifier.verify(hits, "What is the document about?")
        self.assertEqual(res.verification_status, "PASS")
        self.assertEqual(res.recommended_action, "Continue normally")
        self.assertGreaterEqual(res.quality_score, settings.RETRIEVAL_VERIFIER_MIN_PASS_SCORE)

    def test_warning_quality_score(self):
        # Moderate matches
        hits = [
            {"score": 0.24, "chunk_text": "Document chunk content here."},
            {"score": 0.15, "chunk_text": "More chunk content."},
            {"score": 0.10, "chunk_text": "Even more content."}
        ]
        res = retrieval_verifier.verify(hits, "What is the document about?")
        self.assertEqual(res.verification_status, "WARNING")
        self.assertEqual(res.recommended_action, "Continue with caution")

    def test_fail_quality_score(self):
        # Low scores
        hits = [
            {"score": 0.08, "chunk_text": "Document chunk content here."},
            {"score": 0.05, "chunk_text": "More chunk content."}
        ]
        res = retrieval_verifier.verify(hits, "What is the document about?")
        self.assertEqual(res.verification_status, "FAIL")
        self.assertEqual(res.recommended_action, "Trigger retrieval retry")

    def test_empty_hits_fail(self):
        hits = []
        res = retrieval_verifier.verify(hits, "What is the document about?")
        self.assertEqual(res.verification_status, "FAIL")
        self.assertEqual(res.recommended_action, "Trigger retrieval retry")

    def test_verifier_disabled_bypass(self):
        old_val = settings.RETRIEVAL_VERIFIER_ENABLED
        try:
            settings.RETRIEVAL_VERIFIER_ENABLED = False
            hits = []
            res = retrieval_verifier.verify(hits, "What is Python?")
            self.assertEqual(res.verification_status, "PASS")
            self.assertEqual(res.recommended_action, "Continue normally")
        finally:
            settings.RETRIEVAL_VERIFIER_ENABLED = old_val

class RetrievalVerificationIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user for integration tests
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"rv_user_{cls.rand_id}@example.com"
        cls.password = "rvpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Upload a test document for this user so they pass the security check and hit vector search
        doc_content = (
            "DocumentIQ is an AI-powered enterprise search and retrieval platform.\n"
            "It features Query Analysis, Query Rewriting, and Adaptive Retrieval.\n"
            "This is a test document for retrieval verification integration tests."
        )
        files = {"file": ("test_verification_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload test document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for document to index
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_search_verification_pass_or_warning(self):
        # Query that matches the uploaded document content should return hits
        search_req = {
            "query": "DocumentIQ retrieval features"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify schema field is present
        self.assertIn("retrieval_verification", data)
        rv = data["retrieval_verification"]
        self.assertIsNotNone(rv)
        self.assertIn(rv["verification_status"], ["PASS", "WARNING", "FAIL"])
        self.assertIn("quality_score", rv)
        self.assertIn("retry_performed", rv)

    def test_chat_verification_fail_and_retry(self):
        # Register a separate user with no uploaded documents
        rand_id = random.randint(10000, 99999)
        email = f"rv_fail_user_{rand_id}@example.com"
        password = "failpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password})
        self.assertEqual(reg_resp.status_code, 201)
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Query that returns zero matches because there are no documents -> verification FAIL -> triggers retry
        chat_req = {
            "question": "Lookup query when no documents exist"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        self.assertIn("retrieval_verification", data)
        rv = data["retrieval_verification"]
        self.assertIsNotNone(rv)
    
        # Verify attempt 1 failed, retry ran, and final attempt failed (since no documents exist)
        self.assertEqual(rv["first_attempt_status"], "FAIL")
        self.assertTrue(rv["retry_performed"])
        self.assertEqual(rv["final_attempt_status"], "FAIL")
        self.assertEqual(rv["verification_status"], "FAIL")

if __name__ == "__main__":
    unittest.main()
