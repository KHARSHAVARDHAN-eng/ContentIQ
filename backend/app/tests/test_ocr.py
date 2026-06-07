import unittest
import requests
import time
import random
import os
from PIL import Image, ImageDraw

BASE_URL = "http://localhost:8000/api"

class OCRPipelineE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate test files programmatically
        cls.img_filename = "test_ocr_asset.png"
        cls.img_text = "Secret OCR Code: Antigravity RAG works!"
        cls.generate_test_image(cls.img_filename, cls.img_text)

        cls.pdf_filename = "test_scanned_pdf.pdf"
        cls.pdf_text = "Scanned PDF secret message: Qdrant matches!"
        cls.generate_scanned_pdf(cls.pdf_filename, cls.pdf_text)

        # Create user
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"ocr_user_{cls.rand_id}@example.com"
        cls.password = "ocrpassword123"
        
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
        
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        # Clean up files
        if os.path.exists(cls.img_filename):
            os.remove(cls.img_filename)
        if os.path.exists(cls.pdf_filename):
            os.remove(cls.pdf_filename)

    @staticmethod
    def generate_test_image(filename: str, text: str):
        from PIL import ImageFont
        img = Image.new("RGB", (800, 200), color="white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("Arial.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
        d.text((30, 80), text, fill="black", font=font)
        img.save(filename)

    @staticmethod
    def generate_scanned_pdf(filename: str, text: str):
        from PIL import ImageFont
        img = Image.new("RGB", (800, 200), color="white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("Arial.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
        d.text((30, 80), text, fill="black", font=font)
        img.save(filename, "PDF", resolution=150.0)

    def test_image_ocr_ingestion_and_retrieval(self):
        print("\n--- Testing PNG Image Ingestion with OCR ---")
        
        # 1. Upload the image file
        with open(self.img_filename, "rb") as f:
            upload_resp = requests.post(
                f"{BASE_URL}/documents/upload",
                files={"file": (self.img_filename, f, "image/png")},
                headers=self.headers
            )
        self.assertEqual(upload_resp.status_code, 201)
        doc_id = upload_resp.json()["id"]
        
        # 2. Poll document status, verifying status changes
        status_transitions = set()
        doc_data = {}
        for _ in range(30): # Wait up to 30 seconds
            time.sleep(1.0)
            preview_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=self.headers)
            self.assertEqual(preview_resp.status_code, 200)
            doc_data = preview_resp.json()
            status = doc_data["status"]
            status_transitions.add(status)
            if status == "INDEXED":
                break
        
        print(f"Recorded status transitions: {status_transitions}")
        self.assertEqual(doc_data["status"], "INDEXED", "Document status failed to transition to INDEXED")
        
        # Verify ocr_confidence was saved (indicates OCR was run)
        self.assertIsNotNone(doc_data["ocr_confidence"])
        self.assertGreater(doc_data["ocr_confidence"], 0.0)

        # 3. Retrieve document stats and verify ocr_confidence columns (using metadata verification or preview)
        self.assertIn("Antigravity", doc_data["extracted_text_preview"])

        # 4. Query chat to ensure context retrieval answers successfully
        chat_resp = requests.post(
            f"{BASE_URL}/chat",
            json={"question": "What is the secret code name?"},
            headers=self.headers
        )
        self.assertEqual(chat_resp.status_code, 200)
        answer = chat_resp.json()["answer"]
        print(f"RAG Answer for Image OCR: '{answer}'")
        self.assertIn("Antigravity", answer)
        self.assertGreater(len(chat_resp.json()["citations"]), 0, "No citations returned from OCR query")

    def test_scanned_pdf_ocr_ingestion_and_retrieval(self):
        print("\n--- Testing Scanned PDF Ingestion with OCR ---")
        
        # 1. Upload scanned PDF
        with open(self.pdf_filename, "rb") as f:
            upload_resp = requests.post(
                f"{BASE_URL}/documents/upload",
                files={"file": (self.pdf_filename, f, "application/pdf")},
                headers=self.headers
            )
        self.assertEqual(upload_resp.status_code, 201)
        doc_id = upload_resp.json()["id"]

        # 2. Poll document status
        status_transitions = set()
        doc_data = {}
        for _ in range(30):
            time.sleep(1.0)
            preview_resp = requests.get(f"{BASE_URL}/documents/{doc_id}/preview", headers=self.headers)
            self.assertEqual(preview_resp.status_code, 200)
            doc_data = preview_resp.json()
            status = doc_data["status"]
            status_transitions.add(status)
            if status == "INDEXED":
                break

        print(f"Recorded status transitions: {status_transitions}")
        self.assertEqual(doc_data["status"], "INDEXED", "Scanned PDF failed to index")
        
        # Verify ocr_confidence was saved (indicates OCR was run)
        self.assertIsNotNone(doc_data["ocr_confidence"])
        self.assertGreater(doc_data["ocr_confidence"], 0.0)

        self.assertIn("Qdrant", doc_data["extracted_text_preview"])

        # 3. Query chat
        chat_resp = requests.post(
            f"{BASE_URL}/chat",
            json={"question": "What is the scanned PDF secret message?"},
            headers=self.headers
        )
        self.assertEqual(chat_resp.status_code, 200)
        answer = chat_resp.json()["answer"]
        print(f"RAG Answer for PDF OCR: '{answer}'")
        self.assertIn("Qdrant", answer)
        self.assertGreater(len(chat_resp.json()["citations"]), 0, "No citations returned from OCR query")

if __name__ == "__main__":
    unittest.main()
