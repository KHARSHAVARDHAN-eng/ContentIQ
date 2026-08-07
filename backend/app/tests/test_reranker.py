import unittest
import requests
import random
import time
from unittest.mock import patch, MagicMock
from app.core.config import settings
from app.services.reranker import reranker
from app.schemas.reranking import RerankingResult

BASE_URL = "http://localhost:8000/api"

class RerankerUnitTest(unittest.TestCase):
    def test_reranker_rank_swap_via_mock(self):
        hits = [
            {"score": 0.35, "chunk_text": "This is a text about Java programming.", "chunk_id": "c0", "document_id": 1, "page_number": 1},
            {"score": 0.30, "chunk_text": "This is a text about Python programming.", "chunk_id": "c1", "document_id": 1, "page_number": 1}
        ]
        query = "Python language"
        
        # Mock cross-encoder predict to return logits that swap the order
        # e.g. chunk 1 (Python) score is higher than chunk 0 (Java)
        # Logit 1.0 (sigmoid ~0.73) for Python, Logit -1.0 (sigmoid ~0.26) for Java
        # Since RERANK_SCORE_THRESHOLD default is 0.50, Java will be discarded!
        # Let's adjust mock so both are retained, but swapped:
        # Logit 2.0 (sigmoid ~0.88) for Python, Logit 0.5 (sigmoid ~0.62) for Java
        with patch("app.services.reranker.RerankingService.get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.predict.return_value = [0.5, 2.0]
            mock_get_model.return_value = mock_model
            
            old_threshold = settings.RERANK_SCORE_THRESHOLD
            settings.RERANK_SCORE_THRESHOLD = 0.50
            try:
                sorted_hits, result = reranker.rerank(query, hits)
                
                # Check swap
                self.assertEqual(len(sorted_hits), 2)
                self.assertEqual(sorted_hits[0]["chunk_id"], "c1")
                self.assertEqual(sorted_hits[1]["chunk_id"], "c0")
                
                self.assertEqual(result.original_ranking, ["c0", "c1"])
                self.assertEqual(result.reranked_ranking, ["c1", "c0"])
                
                # Check hit status metadata
                self.assertEqual(result.hits[0].status, "retained")  # c1 has score ~0.88 >= 0.50
                self.assertEqual(result.hits[1].status, "retained")  # c0 has score ~0.62 >= 0.50
            finally:
                settings.RERANK_SCORE_THRESHOLD = old_threshold

    def test_threshold_filtering(self):
        hits = [
            {"score": 0.35, "chunk_text": "Java Programming", "chunk_id": "c0", "document_id": 1, "page_number": 1},
            {"score": 0.30, "chunk_text": "Python Programming", "chunk_id": "c1", "document_id": 1, "page_number": 1}
        ]
        query = "Python language"
        
        # Logit 2.0 (sigmoid ~0.88) for Python, Logit -2.0 (sigmoid ~0.12) for Java
        with patch("app.services.reranker.RerankingService.get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.predict.return_value = [-2.0, 2.0]
            mock_get_model.return_value = mock_model
            
            old_threshold = settings.RERANK_SCORE_THRESHOLD
            settings.RERANK_SCORE_THRESHOLD = 0.50
            try:
                sorted_hits, result = reranker.rerank(query, hits)
                
                # Java chunk (c0) is below threshold and should be discarded (pruned)
                self.assertEqual(len(sorted_hits), 1)
                self.assertEqual(sorted_hits[0]["chunk_id"], "c1")
                
                # Metadata must preserve all candidates and details
                self.assertEqual(result.retained_count, 1)
                self.assertEqual(result.discarded_count, 1)
                self.assertEqual(result.hits[0].chunk_id, "c1")
                self.assertEqual(result.hits[0].status, "retained")
                self.assertEqual(result.hits[1].chunk_id, "c0")
                self.assertEqual(result.hits[1].status, "discarded")
            finally:
                settings.RERANK_SCORE_THRESHOLD = old_threshold

    def test_reranker_disabled_bypass(self):
        old_enabled = settings.RERANKER_ENABLED
        try:
            settings.RERANKER_ENABLED = False
            hits = [
                {"score": 0.30, "chunk_text": "Python programming", "chunk_id": "c1", "document_id": 1, "page_number": 1},
                {"score": 0.35, "chunk_text": "Java programming", "chunk_id": "c0", "document_id": 1, "page_number": 1}
            ]
            query = "Java language"
            sorted_hits, result = reranker.rerank(query, hits)
            
            # Original sequence must be preserved
            self.assertEqual(sorted_hits[0]["chunk_id"], "c1")
            self.assertEqual(sorted_hits[1]["chunk_id"], "c0")
            self.assertEqual(result.original_ranking, ["c1", "c0"])
            self.assertEqual(result.reranked_ranking, ["c1", "c0"])
        finally:
            settings.RERANKER_ENABLED = old_enabled

    def test_empty_candidate_list(self):
        sorted_hits, result = reranker.rerank("query", [])
        self.assertEqual(sorted_hits, [])
        self.assertEqual(result.retained_count, 0)
        self.assertEqual(result.discarded_count, 0)

class RerankerIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user for integration tests
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"rr_user_{cls.rand_id}@example.com"
        cls.password = "rrpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Upload a test document for this user
        doc_content = (
            "DocumentIQ is an AI-powered enterprise search and retrieval platform.\n"
            "It features Query Analysis, Query Rewriting, and Adaptive Retrieval.\n"
            "This is a test document for reranker integration tests."
        )
        files = {"file": ("test_rerank_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for indexing
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_search_endpoint_reranking(self):
        search_req = {
            "query": "DocumentIQ retrieval features"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify schema field is present and populated
        self.assertIn("reranking", data)
        rr = data["reranking"]
        self.assertIsNotNone(rr)
        self.assertIn("original_ranking", rr)
        self.assertIn("reranked_ranking", rr)
        self.assertIn("hits", rr)
        self.assertGreaterEqual(rr["reranking_confidence"], 0.0)
        self.assertTrue(len(rr["reranking_reason"]) > 0)

    def test_chat_endpoint_reranking(self):
        chat_req = {
            "question": "What are the features of DocumentIQ?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify schema field is present and populated
        self.assertIn("reranking", data)
        rr = data["reranking"]
        self.assertIsNotNone(rr)
        self.assertIn("original_ranking", rr)
        self.assertIn("reranked_ranking", rr)

if __name__ == "__main__":
    unittest.main()
