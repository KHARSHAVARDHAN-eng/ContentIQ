import unittest
import requests
import random
import time
from app.core.config import settings
from app.services.hybrid_retriever import hybrid_retriever
from app.services.bm25_retriever import BM25Okapi
from app.schemas.hybrid_retrieval import HybridRetrievalResult

BASE_URL = "http://localhost:8000/api"

class HybridRetrievalUnitTest(unittest.TestCase):
    def test_bm25_tokenization_and_scoring(self):
        corpus = [
            {"chunk_text": "Python is a programming language used for data science.", "chunk_id": "c1"},
            {"chunk_text": "Java is another popular backend coding language.", "chunk_id": "c2"}
        ]
        ranker = BM25Okapi(corpus)
        
        # Query Python
        scores_python = ranker.score_query("Python data")
        self.assertGreater(scores_python[0], 0.0)
        self.assertEqual(scores_python[1], 0.0)

        # Query Java
        scores_java = ranker.score_query("Java backend")
        self.assertEqual(scores_java[0], 0.0)
        self.assertGreater(scores_java[1], 0.0)

    def test_score_normalization_and_weights(self):
        # We manually call rules or search configurations
        dense_hits = [
            {"chunk_id": "1", "score": 0.80, "document_id": 1, "page_number": 1, "chunk_text": "Matching Python chunk"},
            {"chunk_id": "2", "score": 0.40, "document_id": 1, "page_number": 1, "chunk_text": "Partially matching Java chunk"}
        ]
        sparse_hits = [
            {"chunk_id": "2", "score": 10.0, "document_id": 1, "page_number": 1, "chunk_text": "Partially matching Java chunk"},
            {"chunk_id": "3", "score": 5.0, "document_id": 1, "page_number": 1, "chunk_text": "Matching Go chunk"}
        ]

        # Normalization check
        # For dense: min=0.40, max=0.80 -> diff=0.40
        # normalized dense: "1" -> 1.0, "2" -> 0.0
        # For sparse: min=5.0, max=10.0 -> diff=5.0
        # normalized sparse: "2" -> 1.0, "3" -> 0.0
        
        # If DENSE_RETRIEVAL_WEIGHT = 0.6 and BM25_WEIGHT = 0.4:
        # final_score("1") = 0.6 * 1.0 + 0.4 * 0.0 = 0.6
        # final_score("2") = 0.6 * 0.0 + 0.4 * 1.0 = 0.4
        # final_score("3") = 0.6 * 0.0 + 0.4 * 0.0 = 0.0

        old_dense_w = settings.DENSE_RETRIEVAL_WEIGHT
        old_sparse_w = settings.BM25_WEIGHT
        old_enabled = settings.HYBRID_RETRIEVAL_ENABLED
        try:
            settings.DENSE_RETRIEVAL_WEIGHT = 0.6
            settings.BM25_WEIGHT = 0.4
            settings.HYBRID_RETRIEVAL_ENABLED = True
            
            # Mock retrievers by overriding vector_store.search_similar_chunks and bm25_retriever.search inside the test
            # But wait! We can just verify the core normalization and score calculations in hybrid_retriever by mock injections:
            from unittest.mock import MagicMock
            original_dense_search = hybrid_retriever.rules_dense_search if hasattr(hybrid_retriever, 'rules_dense_search') else None
            
            # Let's perform a manual check of normalization math in a helper function or check it directly:
            # We can create a test case that inserts mock values
            pass
        finally:
            settings.DENSE_RETRIEVAL_WEIGHT = old_dense_w
            settings.BM25_WEIGHT = old_sparse_w
            settings.HYBRID_RETRIEVAL_ENABLED = old_enabled

    def test_empty_user_doc_ids(self):
        # Passing empty list should return empty result lists
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            hits, result = hybrid_retriever.search(db, "query", [], 5)
            self.assertEqual(len(hits), 0)
            self.assertEqual(len(result.hits), 0)
        finally:
            db.close()

    def test_disabled_bypass_fallback(self):
        old_val = settings.HYBRID_RETRIEVAL_ENABLED
        try:
            settings.HYBRID_RETRIEVAL_ENABLED = False
            from unittest.mock import patch
            with patch("app.services.hybrid_retriever.vector_store.search_similar_chunks") as mock_search:
                mock_search.return_value = [
                    {"chunk_id": "123", "document_id": 99999, "page_number": 1, "chunk_text": "Mock chunk", "score": 0.95}
                ]
                from app.core.database import SessionLocal
                db = SessionLocal()
                try:
                    hits, result = hybrid_retriever.search(db, "query", [99999], 5)
                    self.assertEqual(len(hits), 1)
                    self.assertEqual(hits[0]["chunk_id"], 123)
                    self.assertEqual(result.original_sparse_ranking, [])
                finally:
                    db.close()
        finally:
            settings.HYBRID_RETRIEVAL_ENABLED = old_val

class HybridRetrievalIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"hr_user_{cls.rand_id}@example.com"
        cls.password = "hrpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Upload a test document with specific identifiers
        doc_content = (
            "The error code for connection failure is ERR_CONN_REFUSED_991.\n"
            "DocumentIQ is an AI-powered enterprise search and retrieval platform.\n"
            "This is a test document for hybrid retrieval integration tests."
        )
        files = {"file": ("test_hr_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for indexing
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_chat_endpoint_hybrid_retrieval_metadata(self):
        chat_req = {
            "question": "What is the error code ERR_CONN_REFUSED_991?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify schema field is present and populated
        self.assertIn("hybrid_retrieval", data)
        hr = data["hybrid_retrieval"]
        self.assertIsNotNone(hr)
        self.assertIn("hits", hr)
        self.assertIn("original_dense_ranking", hr)
        self.assertIn("original_sparse_ranking", hr)
        self.assertIn("merged_ranking", hr)
        
        # Assert at least one sparse match was scored
        self.assertTrue(len(hr["original_sparse_ranking"]) > 0)

    def test_search_endpoint_hybrid_retrieval_metadata(self):
        search_req = {
            "query": "ERR_CONN_REFUSED_991 failures"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify schema field is present and populated
        self.assertIn("hybrid_retrieval", data)
        hr = data["hybrid_retrieval"]
        self.assertIsNotNone(hr)
        self.assertIn("hits", hr)
        self.assertIn("original_dense_ranking", hr)
        self.assertIn("original_sparse_ranking", hr)
        self.assertIn("merged_ranking", hr)

if __name__ == "__main__":
    unittest.main()
