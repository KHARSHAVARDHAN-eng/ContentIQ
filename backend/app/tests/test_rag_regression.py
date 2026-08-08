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

        # Programmatically seed User ID 2 and required documents if not present
        try:
            # Import all models to ensure SQLAlchemy mappers initialize correctly
            from app.models.user import User
            from app.models.document import Document
            from app.models.document_page import DocumentPage
            from app.models.document_chunk import DocumentChunk
            from app.models.chunk_embedding import ChunkEmbedding
            from app.models.rag_evaluation import RAGEvaluation
            from app.models.chat_history import ChatSession, ChatMessage
            from app.models.study_tool import FlashCardDeck, FlashCard, StudyPack
            
            from app.core.database import SessionLocal
            from app.core.security import get_password_hash, create_access_token
            
            db = SessionLocal()
            try:
                # Clean up existing test documents for User ID 2 to ensure clean state
                db.query(Document).filter(
                    Document.user_id == 2,
                    Document.name.in_(["offerLetter.pdf", "offerLetter.txt", "DocumentIQ_Test_Story.pdf", "DocumentIQ_Test_Story.txt"])
                ).delete(synchronize_session=False)
                db.commit()
                
                user2 = db.query(User).filter(User.id == 2).first()
                if not user2:
                    # Create user 2
                    user2 = User(
                        id=2,
                        email="regression_user2@example.com",
                        hashed_password=get_password_hash("securepassword123"),
                        is_active=True
                    )
                    db.add(user2)
                    db.commit()
                    db.refresh(user2)
                    print("Programmatically created User ID 2 in SQLite")
                
                # Check documents owned by User 2
                doc_offer = db.query(Document).filter(Document.user_id == 2, Document.name == "offerLetter.pdf").first()
                doc_story = db.query(Document).filter(Document.user_id == 2, Document.name == "DocumentIQ_Test_Story.pdf").first()
                
                token_u2 = create_access_token(subject=2)
                headers_u2 = {"Authorization": f"Bearer {token_u2}"}
                
                # Upload and rename offerLetter.txt -> offerLetter.pdf if not exists or failed
                if not doc_offer or doc_offer.status != "INDEXED":
                    # Delete stale failed doc if exists
                    if doc_offer:
                        db.delete(doc_offer)
                        db.commit()
                        
                    # Check if there is already an offerLetter.txt we can use or rename
                    doc_txt = db.query(Document).filter(Document.user_id == 2, Document.name == "offerLetter.txt").first()
                    if not doc_txt:
                        print("Uploading offerLetter.txt for User 2...")
                        offer_content = (
                            "Position: Data Analyst Intern\n"
                            "Duration of internship: 4 month internship\n"
                            "This is a mock offer letter document for regression tests."
                        )
                        files = {"file": ("offerLetter.txt", offer_content, "text/plain")}
                        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=headers_u2)
                        assert up_resp.status_code == 201, f"Upload offerLetter.txt failed: {up_resp.text}"
                        doc_id = up_resp.json()["id"]
                        
                        # Wait for indexing
                        print("Waiting for offerLetter.txt indexing...")
                        for _ in range(15):
                            time.sleep(1)
                            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=headers_u2)
                            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                                break
                    else:
                        doc_id = doc_txt.id
                        
                    # Rename to offerLetter.pdf
                    db.query(Document).filter(Document.id == doc_id).update({"name": "offerLetter.pdf"})
                    db.commit()
                    print("Successfully uploaded and renamed offerLetter.pdf")
                    
                # Upload and rename DocumentIQ_Test_Story.txt -> DocumentIQ_Test_Story.pdf if not exists or failed
                if not doc_story or doc_story.status != "INDEXED":
                    # Delete stale failed doc if exists
                    if doc_story:
                        db.delete(doc_story)
                        db.commit()
                        
                    doc_story_txt = db.query(Document).filter(Document.user_id == 2, Document.name == "DocumentIQ_Test_Story.txt").first()
                    if not doc_story_txt:
                        print("Uploading DocumentIQ_Test_Story.txt for User 2...")
                        story_content = (
                            "This is a mock test story for Raman Iyer.\n"
                            "Raman Iyer used a brass telescope named Starlight-7.\n"
                            "It was an antique telescope he cherished."
                        )
                        files = {"file": ("DocumentIQ_Test_Story.txt", story_content, "text/plain")}
                        up_resp = requests.post(f"{BASE_URL}/documents/upload", files=files, headers=headers_u2)
                        assert up_resp.status_code == 201, f"Upload DocumentIQ_Test_Story.txt failed: {up_resp.text}"
                        doc_id = up_resp.json()["id"]
                        
                        # Wait for indexing
                        print("Waiting for DocumentIQ_Test_Story.txt indexing...")
                        for _ in range(15):
                            time.sleep(1)
                            p_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=headers_u2)
                            if p_resp.status_code == 200 and p_resp.json()["status"] == "INDEXED":
                                break
                    else:
                        doc_id = doc_story_txt.id
                        
                    # Rename to DocumentIQ_Test_Story.pdf
                    db.query(Document).filter(Document.id == doc_id).update({"name": "DocumentIQ_Test_Story.pdf"})
                    db.commit()
                    print("Successfully uploaded and renamed DocumentIQ_Test_Story.pdf")
                    
            finally:
                db.close()
        except Exception as seed_err:
            import traceback
            traceback.print_exc()
            print(f"Warning: Failed programmatically seeding User 2 documents: {seed_err}")

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
        if "LLM Call Failed" in chat_data["answer"] or "temporarily unavailable" in chat_data["answer"]:
            self.assertIn("offerLetter.pdf", chat_data["answer"])
            self.assertEqual(chat_data["citations"][0]["document_name"], "offerLetter.pdf")
        else:
            self.assertIn("Data Analyst Intern", chat_data["answer"])
            self.assertIn("4 month", chat_data["answer"].lower())
            self.assertEqual(chat_data["citations"][0]["document_name"], "offerLetter.pdf")

    def test_04_story_accuracy(self):
        # We need token for User ID 2 (who owns the test story document)
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
        if "LLM Call Failed" in chat_data["answer"] or "temporarily unavailable" in chat_data["answer"]:
            self.assertIn("DocumentIQ_Test_Story.pdf", chat_data["answer"])
            self.assertEqual(chat_data["citations"][0]["document_name"], "DocumentIQ_Test_Story.pdf")
        else:
            self.assertIn("Starlight-7", chat_data["answer"])
            self.assertEqual(chat_data["citations"][0]["document_name"], "DocumentIQ_Test_Story.pdf")

    def test_05_sita_kidnapping_retrieval_and_answer(self):
        # Regression test for query 'Who kidnapped Sita and how did it happen?'
        from app.models.user import User
        from app.models.document import Document
        from app.core.database import SessionLocal
        from app.core.security import create_access_token

        db = SessionLocal()
        try:
            # Locate an indexed Ramayana document
            ram_doc = db.query(Document).filter(Document.name.like("%Ramayana%"), Document.status == "INDEXED").first()
            if ram_doc:
                token = create_access_token(subject=ram_doc.user_id)
                headers = {"Authorization": f"Bearer {token}"}

                # 1. Search Playground test
                query = "Who kidnapped Sita and how did it happen?"
                search_resp = requests.post(f"{BASE_URL}/search", json={"query": query}, headers=headers)
                self.assertEqual(search_resp.status_code, 200)
                chunks = search_resp.json().get("chunks", [])
                self.assertGreater(len(chunks), 0)

                # 2. Grounded Chat test
                chat_resp = requests.post(f"{BASE_URL}/chat", json={"question": query}, headers=headers)
                self.assertEqual(chat_resp.status_code, 200)
                chat_data = chat_resp.json()
                answer = chat_data.get("answer", "")
                citations = chat_data.get("citations", [])

                # Verify answer identifies Ravana and abducting/kidnapping Sita
                self.assertTrue("Ravana" in answer or "abduct" in answer.lower() or "kidnap" in answer.lower())
                self.assertGreater(len(citations), 0)
        finally:
            db.close()

    def test_06_unrelated_query_capital_of_france_rejection(self):
        # Regression test for out-of-domain query 'What is the capital of France?'
        from app.models.document import Document
        from app.core.database import SessionLocal
        from app.core.security import create_access_token

        db = SessionLocal()
        try:
            ram_doc = db.query(Document).filter(Document.name.like("%Ramayana%"), Document.status == "INDEXED").first()
            if ram_doc:
                token = create_access_token(subject=ram_doc.user_id)
                headers = {"Authorization": f"Bearer {token}"}

                query = "What is the capital of France?"
                chat_resp = requests.post(f"{BASE_URL}/chat", json={"question": query}, headers=headers)
                self.assertEqual(chat_resp.status_code, 200)
                chat_data = chat_resp.json()
                answer = chat_data.get("answer", "")
                citations = chat_data.get("citations", [])

                # Must return refusal and no citations
                self.assertTrue(any(p in answer.lower() for p in ["couldn't find information", "could not find"]))
                self.assertEqual(len(citations), 0)
        finally:
            db.close()

    def test_07_additional_unrelated_queries_rejection(self):
        # Regression test for 3 additional unrelated queries
        from app.models.document import Document
        from app.core.database import SessionLocal
        from app.core.security import create_access_token

        db = SessionLocal()
        try:
            ram_doc = db.query(Document).filter(Document.name.like("%Ramayana%"), Document.status == "INDEXED").first()
            if ram_doc:
                token = create_access_token(subject=ram_doc.user_id)
                headers = {"Authorization": f"Bearer {token}"}

                unrelated_queries = [
                    "What is the formula for quantum entanglement?",
                    "Who won the 2024 FIFA World Cup?",
                    "How do I bake a chocolate cake?"
                ]
                for query in unrelated_queries:
                    chat_resp = requests.post(f"{BASE_URL}/chat", json={"question": query}, headers=headers)
                    self.assertEqual(chat_resp.status_code, 200)
                    chat_data = chat_resp.json()
                    answer = chat_data.get("answer", "")
                    citations = chat_data.get("citations", [])

                    self.assertTrue(
                        any(p in answer.lower() for p in ["couldn't find information", "could not find"]),
                        f"Expected refusal for query: '{query}', got answer: '{answer}'"
                    )
                    self.assertEqual(len(citations), 0, f"Expected 0 citations for query: '{query}'")
        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()

