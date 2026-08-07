import unittest
import requests
import random
from app.core.config import settings
from app.services.query_analyzer import query_analyzer
from app.schemas.query_analysis import QueryAnalysis

BASE_URL = "http://localhost:8000/api"

class QueryAnalysisUnitTest(unittest.TestCase):
    def test_rule_based_intent_classification(self):
        # Test Conversational
        res = query_analyzer._fallback_analyze("Hello, how are you today?")
        self.assertEqual(res.intent, "conversational")
        self.assertEqual(res.complexity, "Simple")
        self.assertGreaterEqual(res.intent_confidence, 0.0)
        self.assertLessEqual(res.intent_confidence, 1.0)
        
        # Test Summarization
        res = query_analyzer._fallback_analyze("Can you please summarize this article for me?")
        self.assertEqual(res.intent, "summarization")
        self.assertEqual(res.complexity, "Medium")

        # Test Comparison
        res = query_analyzer._fallback_analyze("What is the difference between Postgres and MySQL?")
        self.assertEqual(res.intent, "comparison")
        self.assertEqual(res.complexity, "Medium")

        # Test Explanation
        res = query_analyzer._fallback_analyze("Explain why the sky is blue during the daytime.")
        self.assertEqual(res.intent, "explanation")
        self.assertEqual(res.complexity, "Medium")

        # Test Procedural
        res = query_analyzer._fallback_analyze("How to install python dependencies using pip command?")
        self.assertEqual(res.intent, "procedural")
        self.assertEqual(res.complexity, "Medium")

        # Test Analytical
        res = query_analyzer._fallback_analyze("Analyze the average sales increase for last year metrics.")
        self.assertEqual(res.intent, "analytical")
        self.assertEqual(res.complexity, "Medium")

        # Test Factual
        res = query_analyzer._fallback_analyze("What is the capital of France?")
        self.assertEqual(res.intent, "factual")
        self.assertEqual(res.complexity, "Medium")

    def test_multi_intent_classification(self):
        # Procedural and Comparison query
        res = query_analyzer._fallback_analyze("How to write clean FastAPI endpoints and also compare it with Django?")
        self.assertEqual(res.intent, "multi-intent")
        self.assertEqual(res.complexity, "Complex") # multi-intent adds score complexity
        self.assertIn("multiple active query intents", res.reasoning.lower())

    def test_complexity_classification(self):
        # Simple query
        res = query_analyzer._fallback_analyze("What is Python?")
        self.assertEqual(res.complexity, "Simple")
        
        # Medium query
        res = query_analyzer._fallback_analyze("How to configure FastAPI routes for authentication?")
        self.assertEqual(res.complexity, "Medium")

        # Complex query due to multiple factors (long words + reasoning depth + entity count)
        res = query_analyzer._fallback_analyze(
            "What are the structural differences between SQLAlchemy and Django ORM because we need to optimize our database layer for high throughput?"
        )
        self.assertEqual(res.complexity, "Complex")
        self.assertIn("reasoning depth triggers present", res.reasoning.lower())
        self.assertIn("entities", res.reasoning.lower())

    def test_confidence_scores_and_reasoning(self):
        res = query_analyzer._fallback_analyze("Summarize this doc.")
        self.assertEqual(res.intent_confidence, settings.QUERY_ANALYZER_FALLBACK_INTENT_CONF)
        self.assertEqual(res.complexity_confidence, settings.QUERY_ANALYZER_FALLBACK_COMPLEXITY_CONF)
        self.assertTrue(len(res.reasoning) > 0)
        self.assertIn("Intent", res.reasoning)
        self.assertIn("Complexity", res.reasoning)

    def test_configurability(self):
        # Save old values
        old_intent_conf = settings.QUERY_ANALYZER_FALLBACK_INTENT_CONF
        old_complexity_conf = settings.QUERY_ANALYZER_FALLBACK_COMPLEXITY_CONF
        
        try:
            # Modify configurations
            settings.QUERY_ANALYZER_FALLBACK_INTENT_CONF = 0.99
            settings.QUERY_ANALYZER_FALLBACK_COMPLEXITY_CONF = 0.91
            
            res = query_analyzer._fallback_analyze("Summarize this doc.")
            self.assertEqual(res.intent_confidence, 0.99)
            self.assertEqual(res.complexity_confidence, 0.91)
        finally:
            # Restore defaults
            settings.QUERY_ANALYZER_FALLBACK_INTENT_CONF = old_intent_conf
            settings.QUERY_ANALYZER_FALLBACK_COMPLEXITY_CONF = old_complexity_conf

    def test_keyword_extraction(self):
        res = query_analyzer._fallback_analyze("Query for analyzing database indexes.")
        # Stop words like "for" should be filtered out
        self.assertIn("query", res.keywords)
        self.assertIn("analyzing", res.keywords)
        self.assertIn("database", res.keywords)
        self.assertIn("indexes", res.keywords)
        self.assertNotIn("for", res.keywords)

class QueryAnalysisIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user for integration tests
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"qa_user_{cls.rand_id}@example.com"
        cls.password = "qapassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_chat_endpoint_query_analysis(self):
        chat_req = {
            "question": "Can you summarize the main benefits of using FastAPI?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify query_analysis is present and populated
        self.assertIn("query_analysis", data)
        analysis = data["query_analysis"]
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis["raw_query"], chat_req["question"])
        self.assertEqual(analysis["intent"], "summarization")
        self.assertIn("fastapi", analysis["keywords"])
        
        # Verify new fields
        self.assertIn("intent_confidence", analysis)
        self.assertIn("complexity_confidence", analysis)
        self.assertIn("reasoning", analysis)
        self.assertGreaterEqual(analysis["intent_confidence"], 0.0)
        self.assertLessEqual(analysis["intent_confidence"], 1.0)
        self.assertTrue(len(analysis["reasoning"]) > 0)

    def test_search_endpoint_query_analysis(self):
        search_req = {
            "query": "Compare document chunking strategies."
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify query_analysis is present
        self.assertIn("query_analysis", data)
        analysis = data["query_analysis"]
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis["raw_query"], search_req["query"])
        self.assertEqual(analysis["intent"], "comparison")
        self.assertIn("chunking", analysis["keywords"])
        
        # Verify new fields
        self.assertIn("intent_confidence", analysis)
        self.assertIn("complexity_confidence", analysis)
        self.assertIn("reasoning", analysis)
        self.assertGreaterEqual(analysis["intent_confidence"], 0.0)
        self.assertLessEqual(analysis["intent_confidence"], 1.0)
        self.assertTrue(len(analysis["reasoning"]) > 0)

if __name__ == "__main__":
    unittest.main()
