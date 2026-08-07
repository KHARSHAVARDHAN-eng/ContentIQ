import unittest
import requests
import random
import time
from unittest.mock import patch, MagicMock
from app.core.config import settings
from app.services.query_transformation import query_transformer

BASE_URL = "http://localhost:8000/api"

class DummyMessage:
    def __init__(self, sender, text):
        self.sender = sender
        self.text = text

class QueryTransformationUnitTest(unittest.TestCase):
    def test_fallback_resolve_history(self):
        # Resolve 'it' referring to 'hybrid retrieval'
        history = [
            DummyMessage("user", "Tell me about hybrid retrieval."),
            DummyMessage("bot", "Hybrid retrieval combines dense and sparse vector searches.")
        ]
        resolved = query_transformer._fallback_resolve_history("How does it work?", history)
        self.assertIn("Hybrid Retrieval", resolved)
        self.assertEqual(resolved, "How does Hybrid Retrieval work?")

        # Resolve when no matching topic in history
        history_empty = []
        resolved_same = query_transformer._fallback_resolve_history("How does it work?", history_empty)
        self.assertEqual(resolved_same, "How does it work?")

    def test_fallback_expand_query(self):
        # Specific synonym vocabulary expansion
        expansions = query_transformer._fallback_expand_query("vector database")
        self.assertIn("embedding database", expansions)
        self.assertIn("Qdrant vector database", expansions)

        # Basic fallback word-splitting expansion for general query
        general_expansions = query_transformer._fallback_expand_query("python code programming helper")
        self.assertGreater(len(general_expansions), 0)
        self.assertEqual(general_expansions[0], "python code")

    def test_configuration_toggles(self):
        # 1. Bypassed transformation entirely
        old_trans = settings.QUERY_TRANSFORMATION_ENABLED
        settings.QUERY_TRANSFORMATION_ENABLED = False
        try:
            res = query_transformer.transform("vector database")
            self.assertEqual(res.original_query, "vector database")
            self.assertEqual(res.rewritten_query, "vector database")
            self.assertEqual(res.expanded_queries, [])
            self.assertEqual(res.generated_retrieval_queries, ["vector database"])
            self.assertTrue(res.transformation_metadata.get("bypassed", False))
        finally:
            settings.QUERY_TRANSFORMATION_ENABLED = old_trans

        # 2. Rewrite disabled but expansion enabled
        old_rewrite = settings.QUERY_REWRITE_ENABLED
        old_expansion = settings.QUERY_EXPANSION_ENABLED
        settings.QUERY_REWRITE_ENABLED = False
        settings.QUERY_EXPANSION_ENABLED = True
        try:
            res = query_transformer.transform("vector database")
            self.assertEqual(res.rewritten_query, "vector database")
            self.assertGreater(len(res.expanded_queries), 0)
        finally:
            settings.QUERY_REWRITE_ENABLED = old_rewrite
            settings.QUERY_EXPANSION_ENABLED = old_expansion

        # 3. Multi-query disabled
        old_mq = settings.MULTI_QUERY_ENABLED
        settings.MULTI_QUERY_ENABLED = False
        try:
            res = query_transformer.transform("vector database")
            self.assertEqual(len(res.generated_retrieval_queries), 1)
            self.assertEqual(res.generated_retrieval_queries[0], "vector database")
        finally:
            settings.MULTI_QUERY_ENABLED = old_mq

    def test_edge_cases(self):
        # Empty query
        res_empty = query_transformer.transform("")
        self.assertEqual(res_empty.original_query, "")
        
        # Single-word query
        res_single = query_transformer.transform("rag")
        self.assertEqual(res_single.original_query, "rag")
        self.assertIn("retrieval-augmented generation", [q.lower() for q in res_single.expanded_queries])
        
        # Long query
        long_q = "this is a very long query that checks if the query transformer service handles large inputs without throwing any exceptions or overflows in memory"
        res_long = query_transformer.transform(long_q)
        self.assertEqual(res_long.original_query, long_q)

class QueryTransformationIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register and login a user to test API endpoints
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"trans_user_{cls.rand_id}@example.com"
        cls.password = "transpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Register failed: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_chat_transformation_integration(self):
        chat_payload = {
            "question": "What is RAG?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        self.assertIn("query_transformation", data)
        trans = data["query_transformation"]
        self.assertIsNotNone(trans)
        self.assertEqual(trans["original_query"], "What is RAG?")
        self.assertIn("expanded_queries", trans)
        self.assertIn("generated_retrieval_queries", trans)

    def test_search_transformation_integration(self):
        search_payload = {
            "query": "vector database"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        self.assertIn("query_transformation", data)
        trans = data["query_transformation"]
        self.assertIsNotNone(trans)
        self.assertEqual(trans["original_query"], "vector database")
        self.assertIn("expanded_queries", trans)
        self.assertIn("generated_retrieval_queries", trans)

if __name__ == "__main__":
    unittest.main()
