import unittest
import requests
import random
import time
from unittest.mock import MagicMock

from app.core.config import settings
from app.services.agentic_orchestrator import agentic_orchestrator
from app.schemas.agentic_rag import AgenticRAGResult, AgentStep

BASE_URL = "http://localhost:8000/api"

class AgenticRAGUnitTest(unittest.TestCase):
    def test_rule_based_fallback(self):
        # Verify fallback query refinement when API key is missing
        old_key = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = ""
        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = []
        mock_user = MagicMock()
        mock_user.id = 999
        
        try:
            res = agentic_orchestrator.execute_agentic_flow(
                db=mock_db,
                question="Where is France?",
                session_id=None,
                current_user=mock_user
            )
            # Should fall back to rule-based evaluation and complete successfully
            self.assertIsNotNone(res)
            self.assertFalse(res["agentic_rag"].loop_prevented)
        finally:
            settings.GEMINI_API_KEY = old_key

    def test_loop_prevention_identical_query(self):
        # We test that execute_agentic_flow stops when query remains identical
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = 1
        mock_doc.name = "doc1.txt"
        mock_db.query().filter().all.return_value = [mock_doc]
        
        mock_user = MagicMock()
        mock_user.id = 1
        
        old_attempts = settings.AGENTIC_MAX_RETRIEVAL_ATTEMPTS
        settings.AGENTIC_MAX_RETRIEVAL_ATTEMPTS = 3
        old_key = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = "dummy_key"
        
        try:
            # We mock the search to return a non-empty chunk list so LLM evaluation is triggered
            dummy_chunk = {"chunk_id": "c1", "document_id": 1, "document_name": "doc1.txt", "page_number": 1, "chunk_text": "France content", "score": 0.9}
            
            mock_trans = MagicMock()
            mock_trans.rewritten_query = "France capital"
            mock_trans.transformation_metadata = {}
            
            mock_comp = MagicMock()
            mock_chunk = MagicMock()
            mock_chunk.chunk_id = "c1"
            mock_chunk.document_id = 1
            mock_chunk.document_name = "doc1.txt"
            mock_chunk.page_number = 1
            mock_chunk.chunk_text = "France content"
            mock_chunk.score = 0.9
            mock_comp.compressed_chunks = [mock_chunk]

            with unittest.mock.patch("app.services.query_transformation.query_transformer.transform", return_value=mock_trans):
                with unittest.mock.patch("app.services.hybrid_retriever.hybrid_retriever.search", return_value=([dummy_chunk], MagicMock())):
                    with unittest.mock.patch("app.services.context_compressor.context_compressor.compress", return_value=mock_comp):
                        # We mock evaluate_with_llm to return the same query
                        with unittest.mock.patch.object(agentic_orchestrator, '_evaluate_with_llm', return_value=(False, 0.5, "France capital")):
                            res = agentic_orchestrator.execute_agentic_flow(
                                db=mock_db,
                                question="France capital",
                                session_id=None,
                                current_user=mock_user
                            )
                        
                        # Check that loop prevention is activated
                        self.assertTrue(res["agentic_rag"].loop_prevented)
                        self.assertEqual(res["agentic_rag"].total_steps, 2)  # planning + 1 retrieval attempt
        finally:
            settings.AGENTIC_MAX_RETRIEVAL_ATTEMPTS = old_attempts
            settings.GEMINI_API_KEY = old_key


class AgenticRAGIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"agent_user_{cls.rand_id}@example.com"
        cls.password = "agentpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}", "x-agentic-rag": "true"}

        # Upload a test document
        doc_content = "Autonomous agents optimize RAG systems iteratively."
        files = {"file": ("test_agent_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for indexing
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_chat_endpoint_agentic_rag_metadata(self):
        chat_req = {
            "question": "How do agents optimize systems?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify agentic_rag field is present in response
        self.assertIn("agentic_rag", data)
        ar = data["agentic_rag"]
        self.assertIsNotNone(ar)
        self.assertTrue(ar["agent_enabled"])
        self.assertIn("steps", ar)
        self.assertIn("reasoning_path", ar)
        self.assertIn("merged_context_chunks_count", ar)

    def test_search_endpoint_agentic_rag_metadata(self):
        search_req = {
            "query": "Agents optimize RAG"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify agentic_rag field is present in search response (even if null/None)
        self.assertIn("agentic_rag", data)
        self.assertIsNone(data["agentic_rag"])
