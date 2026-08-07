import unittest
import requests
import random
import time
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.services.context_compressor import context_compressor
from app.schemas.context_compression import ContextCompressionResult

BASE_URL = "http://localhost:8000/api"

class ContextCompressionUnitTest(unittest.TestCase):
    def test_duplicate_chunk_removal(self):
        # 1. Exact Duplicate
        chunks = [
            {"chunk_id": "c1", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.9, "chunk_text": "This is unique text."},
            {"chunk_id": "c2", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.8, "chunk_text": "This is unique text."}
        ]
        res = context_compressor.compress("test query", chunks)
        self.assertEqual(res.original_chunk_count, 2)
        self.assertEqual(res.compressed_chunk_count, 1)
        self.assertEqual(res.removed_chunks[0].chunk_id, "c2")
        self.assertEqual(res.removed_chunks[0].reason, "exact_duplicate")

    def test_semantic_duplicate_chunk_removal(self):
        # 2. Semantic Duplicate
        chunks = [
            {"chunk_id": "c1", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.9, "chunk_text": "Sentence Transformers model encodes text into vector embeddings."},
            {"chunk_id": "c2", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.8, "chunk_text": "Embedding models convert text paragraphs into vectors."}
        ]
        
        # Mock embeddings to be semantically similar (e.g. cosine sim >= 0.85)
        with patch("app.services.context_compressor.ContextCompressorService._cosine_similarity") as mock_sim:
            mock_sim.return_value = 0.90 # high similarity trigger
            res = context_compressor.compress("test query", chunks)
            
            self.assertEqual(res.original_chunk_count, 2)
            self.assertEqual(res.compressed_chunk_count, 1)
            self.assertEqual(res.removed_chunks[0].chunk_id, "c2")
            self.assertIn("semantic_duplicate", res.removed_chunks[0].reason)

    def test_overlap_merging(self):
        # 3. Overlap Merging (same doc, same page)
        chunks = [
            {"chunk_id": "c1", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.9, "chunk_text": "The quick brown fox jumps"},
            {"chunk_id": "c2", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.8, "chunk_text": "brown fox jumps over the lazy dog"}
        ]
        
        res = context_compressor.compress("test query", chunks)
        
        # Should be merged
        self.assertEqual(res.compressed_chunk_count, 1)
        self.assertEqual(res.compressed_chunks[0].chunk_text, "The quick brown fox jumps over the lazy dog")
        self.assertEqual(len(res.merged_chunks), 1)
        self.assertEqual(res.merged_chunks[0].primary_chunk_id, "c1")
        self.assertEqual(res.merged_chunks[0].merged_chunk_ids, ["c2"])

    def test_sentence_deduplication_and_boilerplate_removal(self):
        # 4. Boilerplate and duplicate sentence removal
        chunks = [
            {
                "chunk_id": "c1", 
                "document_id": 1, 
                "document_name": "doc1.pdf", 
                "page_number": 1, 
                "score": 0.9, 
                "chunk_text": "First unique statement. Copyright © 2026. All rights reserved. Short."
            },
            {
                "chunk_id": "c2", 
                "document_id": 1, 
                "document_name": "doc1.pdf", 
                "page_number": 1, 
                "score": 0.8, 
                "chunk_text": "First unique statement. This is a completely unrelated statement about computers."
            }
        ]
        
        old_val = settings.LOW_INFORMATION_THRESHOLD
        settings.LOW_INFORMATION_THRESHOLD = 10
        try:
            res = context_compressor.compress("test query", chunks)
            
            # c1 should filter out copyright boilerplate and the "Short." sentence (len < 10)
            # c2 should filter out the exact duplicate "First unique statement." sentence
            self.assertEqual(res.compressed_chunks[0].chunk_text, "First unique statement.")
            self.assertEqual(res.compressed_chunks[1].chunk_text, "This is a completely unrelated statement about computers.")
            
            # Check reasons
            boilerplate_removed = [rs for rs in res.removed_sentences if rs.reason == "boilerplate"]
            low_info_removed = [rs for rs in res.removed_sentences if rs.reason == "low_information"]
            dup_removed = [rs for rs in res.removed_sentences if rs.reason == "duplicate_sentence_exact"]
            
            self.assertEqual(len(boilerplate_removed), 2)  # Two boilerplate sentences removed
            self.assertEqual(len(low_info_removed), 1)
            self.assertEqual(len(dup_removed), 1)
        finally:
            settings.LOW_INFORMATION_THRESHOLD = old_val

    def test_empty_and_single_chunk_edge_cases(self):
        # Empty
        res = context_compressor.compress("test query", [])
        self.assertEqual(res.original_chunk_count, 0)
        self.assertEqual(res.compressed_chunk_count, 0)
        
        # Single chunk
        chunks = [{"chunk_id": "c1", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.9, "chunk_text": "Just one chunk."}]
        res = context_compressor.compress("test query", chunks)
        self.assertEqual(res.original_chunk_count, 1)
        self.assertEqual(res.compressed_chunk_count, 1)
        self.assertEqual(res.compressed_chunks[0].chunk_text, "Just one chunk.")

    def test_token_limit_truncation(self):
        chunks = [
            {"chunk_id": "c1", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.9, "chunk_text": "First chunk text discussing the layout of database columns."},
            {"chunk_id": "c2", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.8, "chunk_text": "Second chunk text discussing animal behavior in the wild."}
        ]
        
        old_limit = settings.MAX_CONTEXT_TOKENS
        # c1 is 59 chars -> 14 tokens
        # c2 is 58 chars -> 14 tokens
        # Let's limit budget to 20 tokens (so c1 fits, c2 is truncated)
        settings.MAX_CONTEXT_TOKENS = 20
        try:
            res = context_compressor.compress("test query", chunks)
            self.assertEqual(res.compressed_chunk_count, 1)
            self.assertEqual(res.compressed_chunks[0].chunk_id, "c1")
            self.assertEqual(res.removed_chunks[0].chunk_id, "c2")
            self.assertIn("Exceeded MAX_CONTEXT_TOKENS", res.removed_chunks[0].reason)
        finally:
            settings.MAX_CONTEXT_TOKENS = old_limit

    def test_disabled_bypass(self):
        old_val = settings.CONTEXT_COMPRESSION_ENABLED
        settings.CONTEXT_COMPRESSION_ENABLED = False
        try:
            chunks = [
                {"chunk_id": "c1", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.9, "chunk_text": "Duplicate"},
                {"chunk_id": "c2", "document_id": 1, "document_name": "doc1.pdf", "page_number": 1, "score": 0.8, "chunk_text": "Duplicate"}
            ]
            res = context_compressor.compress("test query", chunks)
            # Should bypass deduplication
            self.assertEqual(res.compressed_chunk_count, 2)
            self.assertFalse(res.enabled)
        finally:
            settings.CONTEXT_COMPRESSION_ENABLED = old_val


class ContextCompressionIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"cc_user_{cls.rand_id}@example.com"
        cls.password = "ccpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Upload a test document containing duplicate/overlapping paragraphs
        doc_content = (
            "Paragraph One: Context Compression removes redundant text.\n\n"
            "Paragraph Two: Context Compression removes redundant text.\n\n"
            "Paragraph Three: It also merges overlapping sections of documents.\n"
            "Paragraph Four: merging overlapping sections of documents to improve token utility."
        )
        files = {"file": ("test_cc_doc.txt", doc_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=cls.headers)
        assert up_resp.status_code == 201, f"Upload document failed: {up_resp.text}"
        doc_id = up_resp.json()["id"]

        # Wait for indexing
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=cls.headers)
            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                break

    def test_chat_endpoint_compression_metadata(self):
        chat_req = {
            "question": "What does Context Compression do?"
        }
        resp = requests.post(f"{BASE_URL}/chat", json=chat_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify context_compression field is present
        self.assertIn("context_compression", data)
        cc = data["context_compression"]
        self.assertIsNotNone(cc)
        self.assertTrue(cc["enabled"])
        self.assertIn("original_chunk_count", cc)
        self.assertIn("compressed_chunk_count", cc)
        self.assertIn("compression_ratio", cc)
        self.assertIn("compressed_chunks", cc)

    def test_search_endpoint_compression_metadata(self):
        search_req = {
            "query": "merging overlapping sections of documents"
        }
        resp = requests.post(f"{BASE_URL}/search", json=search_req, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Verify context_compression field is present
        self.assertIn("context_compression", data)
        cc = data["context_compression"]
        self.assertIsNotNone(cc)
        self.assertTrue(cc["enabled"])
        self.assertIn("original_chunk_count", cc)
        self.assertIn("compressed_chunk_count", cc)
        self.assertIn("compression_ratio", cc)
        self.assertIn("compressed_chunks", cc)
