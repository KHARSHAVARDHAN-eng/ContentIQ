import unittest
import requests
import random
import time
from app.core.config import settings
from app.services.adaptive_chunking import adaptive_chunker, RulesBasedAdaptiveChunker

BASE_URL = "http://localhost:8000/api"

class AdaptiveChunkingUnitTest(unittest.TestCase):
    def test_document_classification_and_parameters(self):
        chunker = RulesBasedAdaptiveChunker()
        
        # Test academic paper triggers
        academic_text = "Abstract: This is a deep neural network study.\nIntroduction: We present our findings.\nReferences: [1] Author, 2026.\nDOI:10.1000/xyz123."
        _, meta = chunker.chunk_text(academic_text, "neural_network_paper.txt")
        self.assertEqual(meta["document_type"], "research paper")
        self.assertEqual(meta["chunk_strategy"], "academic_semantic")
        self.assertEqual(meta["chunk_size"], settings.ADAPTIVE_CHUNKING_RESEARCH_PAPER_SIZE)
        self.assertEqual(meta["overlap"], settings.ADAPTIVE_CHUNKING_RESEARCH_PAPER_OVERLAP)

        # Test technical code triggers
        tech_text = "To run this API, run the following script:\n```python\nimport requests\nresp = requests.get('https://api.com')\n```"
        _, meta = chunker.chunk_text(tech_text, "api_setup.md")
        self.assertEqual(meta["document_type"], "technical documentation")
        self.assertEqual(meta["chunk_strategy"], "code_and_text")
        self.assertEqual(meta["chunk_size"], settings.ADAPTIVE_CHUNKING_TECHNICAL_DOC_SIZE)

        # Test manual triggers
        manual_text = "Troubleshooting guide: If indicator light flashes red, refer to warranty statement and safety instructions in user manual."
        _, meta = chunker.chunk_text(manual_text, "user_manual_v3.txt")
        self.assertEqual(meta["document_type"], "user manual")
        self.assertEqual(meta["chunk_strategy"], "large_semantic")
        self.assertEqual(meta["chunk_size"], settings.ADAPTIVE_CHUNKING_USER_MANUAL_SIZE)

        # Test slide triggers
        slide_text = "--- Page 1 ---\nIntroduction to ContentIQ v2\n- Next-Gen RAG Architecture\n--- Page 2 ---\nRetrieval Verification Details"
        _, meta = chunker.chunk_text(slide_text, "slide_deck.txt")
        self.assertEqual(meta["document_type"], "presentation slides")
        self.assertEqual(meta["chunk_strategy"], "slide_aware")
        self.assertEqual(meta["chunk_size"], settings.ADAPTIVE_CHUNKING_SLIDES_SIZE)
        self.assertEqual(meta["overlap"], settings.ADAPTIVE_CHUNKING_SLIDES_OVERLAP)

    def test_semantic_boundary_preservation(self):
        chunker = RulesBasedAdaptiveChunker()
        text = (
            "# Main Heading\n"
            "This is a paragraph outlining the installation instructions.\n"
            "```python\n"
            "import os\n"
            "print(os.getenv('DATABASE_URL'))\n"
            "```\n"
            "Now look at the user options summary table:\n"
            "| Option | Value |\n"
            "| --- | --- |\n"
            "| Enabled | True |\n"
            "| Strategy | Rules |\n"
            "Follow list item guides:\n"
            "- Step 1: Install Python\n"
            "- Step 2: Configure SQLite"
        )
        
        # Split using technical doc size (600 characters)
        chunks, _ = chunker.chunk_text(text, "setup_guide.md")
        
        # Verify that code block is kept in its entirety inside one of the chunks
        code_block = "```python\nimport os\nprint(os.getenv('DATABASE_URL'))\n```"
        table_block = "| Option | Value |\n| --- | --- |\n| Enabled | True |\n| Strategy | Rules |"
        
        self.assertTrue(any(code_block in c for c in chunks), "Code block was split/broken!")
        self.assertTrue(any(table_block in c for c in chunks), "Table structure was split/broken!")

    def test_disabled_bypass_fallback(self):
        old_val = settings.ADAPTIVE_CHUNKING_ENABLED
        try:
            settings.ADAPTIVE_CHUNKING_ENABLED = False
            text = "Abstract: Neural network research introduction. References: [1] Author, 2026. DOI:10.1000/xyz123."
            chunks, meta = adaptive_chunker.chunk_document(text, "paper.txt")
            
            # Should have standard default config parameters
            self.assertEqual(meta["chunk_strategy"], "disabled_recursive_fallback")
            self.assertEqual(meta["chunk_size"], settings.CHUNK_SIZE)
            self.assertEqual(meta["overlap"], settings.CHUNK_OVERLAP)
        finally:
            settings.ADAPTIVE_CHUNKING_ENABLED = old_val

class AdaptiveChunkingIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a test user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"ac_user_{cls.rand_id}@example.com"
        cls.password = "acpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Failed to login: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_document_upload_and_adaptive_chunking_preview(self):
        # Create research paper text
        paper_content = (
            "Abstract: This study presents an adaptive document chunking algorithm designed for RAG pipelines.\n"
            "Introduction: Splitting document structures along semantic lines is critical to preserve vector contexts.\n"
            "We analyze paragraph margins, lists, headings, and tables to optimize retrieval quality.\n"
            "References: [1] Author et al., 2026. [2] NextGen AI, 2025.\n"
            "DOI:10.1234/ac-rag-neural-networks."
        )
        
        files = {"file": ("adaptive_chunking_paper.txt", paper_content, "text/plain")}
        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=self.headers)
        self.assertEqual(up_resp.status_code, 201)
        doc_id = up_resp.json()["id"]

        # Wait for processing/chunking to complete
        status = "PENDING"
        for _ in range(15):
            time.sleep(1)
            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=self.headers)
            if p_resp.status_code == 200:
                status = p_resp.json()["status"]
                if status in ["CHUNKED", "EMBEDDING_GENERATION", "EMBEDDED", "INDEXED"]:
                    break
                    
        # Request preview and assert metadata details
        p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=self.headers)
        self.assertEqual(p_resp.status_code, 200)
        data = p_resp.json()
        
        self.assertEqual(data["document_type"], "research paper")
        self.assertEqual(data["chunk_strategy"], "academic_semantic")
        self.assertEqual(data["chunk_size"], settings.ADAPTIVE_CHUNKING_RESEARCH_PAPER_SIZE)
        self.assertEqual(data["chunk_overlap"], settings.ADAPTIVE_CHUNKING_RESEARCH_PAPER_OVERLAP)
        self.assertTrue(len(data["chunk_reason"]) > 0)

if __name__ == "__main__":
    unittest.main()
