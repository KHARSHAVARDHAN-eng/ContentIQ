import unittest
import requests
import random
import time
from app.core.config import settings
from app.services.hallucination_detector import hallucination_detector
from app.schemas.hallucination import HallucinationDetectionResult

BASE_URL = "http://localhost:8000/api"

class HallucinationDetectorUnitTest(unittest.TestCase):
    def test_rules_based_grounded_answer(self):
        chunks = [
            {"chunk_text": "ContentIQ v2 is an advanced enterprise search engine built with FastAPI and Qdrant."}
        ]
        
        # Grounded answer
        grounded_ans = "ContentIQ v2 is built with FastAPI. It supports advanced enterprise search."
        res = hallucination_detector.detect("What is ContentIQ?", chunks, grounded_ans)
        
        self.assertEqual(res.hallucination_status, "CLEAN")
        self.assertEqual(res.confidence_score, 1.0)
        self.assertEqual(len(res.unsupported_claims), 0)
        self.assertEqual(len(res.grounded_claims), 2)

    def test_rules_based_hallucinated_answer(self):
        chunks = [
            {"chunk_text": "ContentIQ v2 is an advanced enterprise search engine built with FastAPI and Qdrant."}
        ]
        
        # Hallucinated answer containing Oracle
        hallucinated_ans = "ContentIQ v2 uses Oracle Database as its primary index vector storage."
        res = hallucination_detector.detect("What database does ContentIQ use?", chunks, hallucinated_ans)
        
        self.assertEqual(res.hallucination_status, "FAILED")
        self.assertLess(res.confidence_score, settings.HALLUCINATION_DETECTOR_THRESHOLD)
        self.assertEqual(len(res.unsupported_claims), 1)
        self.assertEqual(res.unsupported_claims[0], hallucinated_ans)

    def test_disabled_bypass_fallback(self):
        old_val = settings.HALLUCINATION_DETECTOR_ENABLED
        try:
            settings.HALLUCINATION_DETECTOR_ENABLED = False
            chunks = [{"chunk_text": "ContentIQ v2 is built with FastAPI."}]
            ans = "It is built with Oracle Database."
            res = hallucination_detector.detect("What is it built with?", chunks, ans)
            
            self.assertEqual(res.hallucination_status, "CLEAN")
            self.assertEqual(res.confidence_score, 1.0)
        finally:
            settings.HALLUCINATION_DETECTOR_ENABLED = old_val

class HallucinationDetectorIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"hd_user_{cls.rand_id}@example.com"
        cls.password = "hdpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Upload a test document
        doc_content = (
            "DocumentIQ is an AI-powered enterprise search and retrieval platform.\n"
            "It features Query Analysis, Query Rewriting, and Adaptive Retrieval.\n"
            "This is a test document for hallucination detector integration tests."
        )
        files = {"file": ("test_hd_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for indexing
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_chat_endpoint_hallucination_metadata(self):
        chat_req = {
            "question": "What are the features of DocumentIQ?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify schema field is present and populated
        self.assertIn("hallucination_detection", data)
        hd = data["hallucination_detection"]
        self.assertIsNotNone(hd)
        self.assertIn("hallucination_status", hd)
        self.assertIn("confidence_score", hd)
        self.assertIn("unsupported_claims", hd)
        self.assertIn("grounded_claims", hd)
        self.assertTrue(len(hd["reasoning"]) > 0)

if __name__ == "__main__":
    unittest.main()
