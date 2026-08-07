import unittest
import requests
import random
from app.core.config import settings
from app.services.query_analyzer import query_analyzer
from app.services.query_rewriter import query_rewriter
from app.schemas.query_rewrite import QueryRewriteResult

BASE_URL = "http://localhost:8000/api"

class QueryRewriterUnitTest(unittest.TestCase):
    def test_acronym_expansion(self):
        analysis = query_analyzer._fallback_analyze("What is RAG?")
        res = query_rewriter.rewrite(analysis)
        self.assertTrue(res.rewrite_applied)
        self.assertEqual(res.rewritten_query, "What is Retrieval-Augmented Generation?")
        self.assertIn("RAG", res.rewrite_reason)
        self.assertEqual(res.rewrite_confidence, 0.9)

    def test_comparison_template(self):
        analysis = query_analyzer._fallback_analyze("Compare PostgreSQL and MySQL")
        res = query_rewriter.rewrite(analysis)
        self.assertTrue(res.rewrite_applied)
        self.assertEqual(res.rewritten_query, "Comparison between PostgreSQL and MySQL database systems")
        self.assertIn("comparison", res.rewrite_reason.lower())

    def test_summarization_template(self):
        analysis = query_analyzer._fallback_analyze("Summarize this PDF")
        res = query_rewriter.rewrite(analysis)
        self.assertTrue(res.rewrite_applied)
        self.assertEqual(res.rewritten_query, "Generate a concise summary of the uploaded document")
        self.assertIn("summarization", res.rewrite_reason.lower())

    def test_procedural_template(self):
        analysis = query_analyzer._fallback_analyze("How does authentication work?")
        res = query_rewriter.rewrite(analysis)
        self.assertTrue(res.rewrite_applied)
        self.assertEqual(res.rewritten_query, "Explain authentication workflow")
        self.assertIn("procedural", res.rewrite_reason.lower())

    def test_clear_query_no_rewrite(self):
        analysis = query_analyzer._fallback_analyze("What is the capital of France?")
        res = query_rewriter.rewrite(analysis)
        self.assertFalse(res.rewrite_applied)
        self.assertEqual(res.rewritten_query, "What is the capital of France?")
        self.assertIn("already clear", res.rewrite_reason.lower())

    def test_rewriter_disabled_config(self):
        old_val = settings.QUERY_REWRITER_ENABLED
        try:
            settings.QUERY_REWRITER_ENABLED = False
            analysis = query_analyzer._fallback_analyze("What is RAG?")
            res = query_rewriter.rewrite(analysis)
            self.assertFalse(res.rewrite_applied)
            self.assertEqual(res.rewritten_query, "What is RAG?")
            self.assertIn("disabled", res.rewrite_reason.lower())
        finally:
            settings.QUERY_REWRITER_ENABLED = old_val

class QueryRewriterIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user for integration tests
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"qr_user_{cls.rand_id}@example.com"
        cls.password = "qrpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_chat_endpoint_rewriting(self):
        chat_req = {
            "question": "What is RAG?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify query_rewrite is present and populated
        self.assertIn("query_rewrite", data)
        rewrite = data["query_rewrite"]
        self.assertIsNotNone(rewrite)
        self.assertEqual(rewrite["original_query"], chat_req["question"])
        self.assertEqual(rewrite["rewritten_query"], "What is Retrieval-Augmented Generation?")
        self.assertTrue(rewrite["rewrite_applied"])
        self.assertEqual(rewrite["rewrite_confidence"], 0.9)

    def test_search_endpoint_rewriting(self):
        search_req = {
            "query": "Compare PostgreSQL and MySQL"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify query_rewrite is present and populated
        self.assertIn("query_rewrite", data)
        rewrite = data["query_rewrite"]
        self.assertIsNotNone(rewrite)
        self.assertEqual(rewrite["original_query"], search_req["query"])
        self.assertEqual(rewrite["rewritten_query"], "Comparison between PostgreSQL and MySQL database systems")
        self.assertTrue(rewrite["rewrite_applied"])

if __name__ == "__main__":
    unittest.main()
