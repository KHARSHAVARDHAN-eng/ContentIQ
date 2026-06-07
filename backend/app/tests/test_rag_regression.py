import unittest
import requests
import time
import os
import random

# Core configuration
BASE_URL = "http://localhost:8000/api"

class DocumentIQRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clean test setup: Register a new test user to perform ingestion and search
        cls.rand_id = random.randint(10000, 99999)
        cls.test_email = f"regression_user_{cls.rand_id}@example.com"
        cls.test_password = "securepassword123"
        
        # 1. Test Authentication - Registration
        reg_url = f"{BASE_URL}/auth/register"
        resp = requests.post(reg_url, json={"email": cls.test_email, "password": cls.test_password})
        assert resp.status_code == 201, f"Registration failed: {resp.text}"
        
        # 2. Test Authentication - Login
        login_url = f"{BASE_URL}/auth/login"
        resp = requests.post(login_url, json={"email": cls.test_email, "password": cls.test_password})
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        cls.token = resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_01_protected_route_access(self):
        # Test Authentication - Protected routes check
        me_url = f"{BASE_URL}/users/me"
        resp = requests.get(me_url, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["email"], self.test_email)

    def test_02_upload_and_ingestion_pipeline(self):
        # 3. Test Upload API
        upload_url = f"{BASE_URL}/documents/upload"
        
        # Create a temp text file for upload test
        temp_filename = f"reg_test_{self.rand_id}.txt"
        temp_content = "This is a regression test document for DocumentIQ. The system must index this txt file and return it during search queries. Security filters must keep it isolated."
        
        # Perform Upload
        files = {"file": (temp_filename, temp_content, "text/plain")}
        resp = requests.post(upload_url, files=files, headers=self.headers)
        self.assertEqual(resp.status_code, 201, f"Upload failed: {resp.text}") # 201 Created
        doc_data = resp.json()
        doc_id = doc_data["id"]
        self.assertEqual(doc_data["name"], temp_filename)
        self.assertEqual(doc_data["status"], "UPLOADED")

        # Wait for asynchronous ingestion background task to complete (extract, chunk, embed, index)
        print("Waiting for ingestion pipeline to process document...")
        status = "UPLOADED"
        for _ in range(15): # wait up to 15 seconds
            time.sleep(1)
            preview_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=self.headers)
            if preview_resp.status_code == 200:
                status = preview_resp.json()["status"]
                if status == "INDEXED":
                    break
        self.assertEqual(status, "INDEXED", "Ingestion task failed to complete or status is not INDEXED")

        # 4. Test Text Extraction (Pages)
        preview_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=self.headers)
        self.assertEqual(preview_resp.status_code, 200)
        self.assertIn("This is a regression test document for DocumentIQ", preview_resp.json()["extracted_text_preview"])
        self.assertEqual(preview_resp.json()["page_count"], 1)

        # 5. Test Chunking Logic
        chunks_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/chunks", headers=self.headers)
        self.assertEqual(chunks_resp.status_code, 200)
        chunks_data = chunks_resp.json()
        self.assertGreater(chunks_data["total_chunks"], 0)
        self.assertEqual(chunks_data["chunks"][0]["chunk_text"], temp_content)

        # 6. Test Embedding Counts
        stats_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/embedding-stats", headers=self.headers)
        self.assertEqual(stats_resp.status_code, 200)
        stats_data = stats_resp.json()
        self.assertEqual(stats_data["embedded_chunks"], chunks_data["total_chunks"])
        self.assertEqual(stats_data["vector_dimension"], 384)
        self.assertEqual(stats_data["model_name"], "all-MiniLM-L6-v2")

        # 7. Test Retrieval (Search)
        search_resp = requests.post(f"{BASE_URL}/search", json={"query": "regression test document"}, headers=self.headers)
        self.assertEqual(search_resp.status_code, 200)
        hits = search_resp.json().get("chunks", [])
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0]["document_name"], temp_filename)
        self.assertGreater(hits[0]["score"], 0.2)

        # 8. Test Chat (RAG generation + Citations)
        chat_resp = requests.post(f"{BASE_URL}/chat", json={"question": "What is this regression test document about?"}, headers=self.headers)
        self.assertEqual(chat_resp.status_code, 200)
        chat_data = chat_resp.json()
        self.assertIn("DocumentIQ", chat_data["answer"])
        self.assertGreater(len(chat_data["citations"]), 0)
        self.assertEqual(chat_data["citations"][0]["document_name"], temp_filename)

    def test_03_offer_letter_accuracy(self):
        # We need token for User ID 2 (who owns the offer letter document)
        import sys
        sys.path.append("/Users/harsha/Desktop/Major 1/backend")
        from app.core.security import create_access_token
        token_u2 = create_access_token(subject=2)
        headers_u2 = {"Authorization": f"Bearer {token_u2}"}

        # Check search on offer letter
        search_resp = requests.post(f"{BASE_URL}/search", json={"query": "Data Analyst Intern duration"}, headers=headers_u2)
        self.assertEqual(search_resp.status_code, 200)
        hits = search_resp.json().get("chunks", [])
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0]["document_name"], "offerLetter.pdf")

        # Check Chat answer accuracy for offerLetter.pdf
        chat_resp = requests.post(f"{BASE_URL}/chat", json={"question": "What is the position offered and duration of internship?"}, headers=headers_u2)
        self.assertEqual(chat_resp.status_code, 200)
        chat_data = chat_resp.json()
        self.assertIn("Data Analyst Intern", chat_data["answer"])
        self.assertIn("4 month", chat_data["answer"].lower())
        self.assertEqual(chat_data["citations"][0]["document_name"], "offerLetter.pdf")

    def test_04_story_accuracy(self):
        # We need token for User ID 2 (who owns the test story document)
        import sys
        sys.path.append("/Users/harsha/Desktop/Major 1/backend")
        from app.core.security import create_access_token
        token_u2 = create_access_token(subject=2)
        headers_u2 = {"Authorization": f"Bearer {token_u2}"}

        # Check search on DocumentIQ_Test_Story.pdf
        search_resp = requests.post(f"{BASE_URL}/search", json={"query": "Raman Iyer Starlight-7"}, headers=headers_u2)
        self.assertEqual(search_resp.status_code, 200)
        hits = search_resp.json().get("chunks", [])
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0]["document_name"], "DocumentIQ_Test_Story.pdf")

        # Check Chat answer accuracy for DocumentIQ_Test_Story.pdf
        chat_resp = requests.post(f"{BASE_URL}/chat", json={"question": "What is the name of the brass telescope Raman Iyer used?"}, headers=headers_u2)
        self.assertEqual(chat_resp.status_code, 200)
        chat_data = chat_resp.json()
        self.assertIn("Starlight-7", chat_data["answer"])
        self.assertEqual(chat_data["citations"][0]["document_name"], "DocumentIQ_Test_Story.pdf")

if __name__ == "__main__":
    unittest.main()
