import unittest
import requests
import random
from app.core.config import settings
from app.schemas.query_analysis import QueryAnalysis
from app.services.adaptive_retrieval import adaptive_retriever
from app.schemas.adaptive_retrieval import AdaptiveRetrievalResult

BASE_URL = "http://localhost:8000/api"

class AdaptiveRetrievalUnitTest(unittest.TestCase):
    def test_simple_factual_routing(self):
        analysis = QueryAnalysis(
            raw_query="What is Python?",
            intent="factual",
            complexity="Simple",
            intent_confidence=0.95,
            complexity_confidence=0.85
        )
        res = adaptive_retriever.determine_strategy(analysis)
        self.assertEqual(res.retrieval_strategy, "simple_factual")
        self.assertEqual(res.selected_top_k, settings.ADAPTIVE_RETRIEVAL_SIMPLE_FACTUAL_TOP_K)
        self.assertEqual(res.confidence, 0.85)

    def test_medium_explanation_routing(self):
        analysis = QueryAnalysis(
            raw_query="Explain how python compiles code.",
            intent="explanation",
            complexity="Medium",
            intent_confidence=0.9,
            complexity_confidence=0.8
        )
        res = adaptive_retriever.determine_strategy(analysis)
        self.assertEqual(res.retrieval_strategy, "medium_explanation")
        self.assertEqual(res.selected_top_k, settings.ADAPTIVE_RETRIEVAL_MEDIUM_EXPLANATION_TOP_K)

    def test_complex_analytical_routing(self):
        analysis = QueryAnalysis(
            raw_query="Analyze the performance trends of the databases.",
            intent="analytical",
            complexity="Complex",
            intent_confidence=0.9,
            complexity_confidence=0.9
        )
        res = adaptive_retriever.determine_strategy(analysis)
        self.assertEqual(res.retrieval_strategy, "complex_analytical")
        self.assertEqual(res.selected_top_k, settings.ADAPTIVE_RETRIEVAL_COMPLEX_ANALYTICAL_TOP_K)

    def test_large_comparison_routing(self):
        analysis = QueryAnalysis(
            raw_query="Compare PostgreSQL and MySQL.",
            intent="comparison",
            complexity="Medium",
            intent_confidence=0.9,
            complexity_confidence=0.9
        )
        res = adaptive_retriever.determine_strategy(analysis)
        self.assertEqual(res.retrieval_strategy, "large_comparison")
        self.assertEqual(res.selected_top_k, settings.ADAPTIVE_RETRIEVAL_LARGE_COMPARISON_TOP_K)

    def test_general_fallbacks(self):
        # Complex fallback
        analysis = QueryAnalysis(
            raw_query="Some conversational query that is complex.",
            intent="conversational",
            complexity="Complex",
            intent_confidence=0.9,
            complexity_confidence=0.9
        )
        res = adaptive_retriever.determine_strategy(analysis)
        self.assertEqual(res.retrieval_strategy, "complex_fallback")
        self.assertEqual(res.selected_top_k, settings.ADAPTIVE_RETRIEVAL_COMPLEX_ANALYTICAL_TOP_K)

    def test_configurability_overrides(self):
        # Test disabled
        old_enabled = settings.ADAPTIVE_RETRIEVAL_ENABLED
        old_val = settings.ADAPTIVE_RETRIEVAL_SIMPLE_FACTUAL_TOP_K
        try:
            settings.ADAPTIVE_RETRIEVAL_ENABLED = False
            analysis = QueryAnalysis(
                raw_query="What is Python?",
                intent="factual",
                complexity="Simple",
                intent_confidence=0.9,
                complexity_confidence=0.9
            )
            res = adaptive_retriever.determine_strategy(analysis)
            self.assertEqual(res.selected_top_k, settings.ADAPTIVE_RETRIEVAL_DEFAULT_TOP_K)
            self.assertEqual(res.retrieval_strategy, "disabled_fallback")

            # Test override value
            settings.ADAPTIVE_RETRIEVAL_ENABLED = True
            settings.ADAPTIVE_RETRIEVAL_SIMPLE_FACTUAL_TOP_K = 2
            res = adaptive_retriever.determine_strategy(analysis)
            self.assertEqual(res.selected_top_k, 2)
        finally:
            settings.ADAPTIVE_RETRIEVAL_ENABLED = old_enabled
            settings.ADAPTIVE_RETRIEVAL_SIMPLE_FACTUAL_TOP_K = old_val

class AdaptiveRetrievalIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user for integration tests
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"ar_user_{cls.rand_id}@example.com"
        cls.password = "arpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_chat_endpoint_adaptive_retrieval(self):
        chat_req = {
            "question": "Compare Postgres and MySQL database engines"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify adaptive_retrieval is present and populated
        self.assertIn("adaptive_retrieval", data)
        ar = data["adaptive_retrieval"]
        self.assertIsNotNone(ar)
        self.assertEqual(ar["retrieval_strategy"], "large_comparison")
        self.assertEqual(ar["selected_top_k"], 12)
        self.assertTrue(len(ar["retrieval_reason"]) > 0)
        self.assertGreaterEqual(ar["confidence"], 0.0)

    def test_search_endpoint_adaptive_retrieval(self):
        search_req = {
            "query": "What is Python?"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify adaptive_retrieval is present and populated
        self.assertIn("adaptive_retrieval", data)
        ar = data["adaptive_retrieval"]
        self.assertIsNotNone(ar)
        self.assertEqual(ar["retrieval_strategy"], "simple_factual")
        self.assertEqual(ar["selected_top_k"], 3)

if __name__ == "__main__":
    unittest.main()
