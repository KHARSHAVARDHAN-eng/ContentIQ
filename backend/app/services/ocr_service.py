import numpy as np
from PIL import Image

class OCRService:
    def __init__(self):
        self._reader = None

    def get_reader(self):
        if self._reader is None:
            import easyocr
            # Initialize EasyOCR reader for English language on CPU
            print("Initializing EasyOCR reader (CPU mode)...")
            self._reader = easyocr.Reader(['en'], gpu=False)
        return self._reader

    def clean_ocr_text(self, text: str) -> str:
        if not text:
            return ""
        import re
        cleaned = text

        # 1. Fix mixed-case noise inside words like 'sOrrow' -> 'sorrow', 'tO' -> 'to'
        def fix_mixed_case(m):
            w = m.group(0)
            if w.isupper() or w.islower() or w.istitle():
                return w
            return w.lower()
        cleaned = re.sub(r'\b[a-zA-Z]+\b', fix_mixed_case, cleaned)

        # 2. Fix 0 inside words like 'g0' -> 'go', 't0' -> 'to'
        cleaned = re.sub(r'\b([a-zA-Z]+)0([a-zA-Z]*)\b', r'\1o\2', cleaned)
        cleaned = re.sub(r'\b0([a-zA-Z]+)\b', r'o\1', cleaned)

        # 3. Fix possessive OCR noise: "Sita $" or "Sita _" before a word -> "Sita's"
        cleaned = re.sub(r'(\b[a-zA-Z]{2,})\s+[\$|_]\s+(?=[a-zA-Z])', r"\1's ", cleaned)

        # 4. Clean trailing/leading underscores or noise symbols around words (e.g. "abduction_" -> "abduction")
        cleaned = re.sub(r'(?<=\w)[_]+', '', cleaned)
        cleaned = re.sub(r'[_]+(?=\w)', '', cleaned)
        cleaned = re.sub(r'\s+[\$|_~^\\@]+\s+', ' ', cleaned)

        # 5. Normalize multiple whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def extract_text_from_image(self, pil_image: Image.Image) -> tuple[str, float]:
        """
        Extracts text content and average confidence from a PIL Image.
        First tries EasyOCR, then falls back to Tesseract if EasyOCR fails.
        Returns a tuple of (extracted_text, confidence_score) where confidence_score is between 0.0 and 1.0.
        """
        # Ensure image is in RGB format
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        try:
            # Convert PIL image to numpy array for EasyOCR
            img_np = np.array(pil_image)
            reader = self.get_reader()
            results = reader.readtext(img_np)

            if results:
                texts = []
                confidences = []
                for bbox, text, conf in results:
                    text_str = text.strip() if text else ""
                    if text_str:
                        texts.append(text_str)
                        confidences.append(float(conf))
                
                raw_extracted_text = " ".join(texts)
                cleaned_text = self.clean_ocr_text(raw_extracted_text)
                avg_confidence = float(np.mean(confidences)) if confidences else 1.0
                return cleaned_text, avg_confidence
            else:
                return "", 1.0

        except Exception as e:
            print(f"EasyOCR extraction failed: {e}. Falling back to Tesseract...")
            try:
                import pytesseract
                # Fallback to Tesseract
                extracted_text = pytesseract.image_to_string(pil_image).strip()
                
                # Get confidence scores using image_to_data
                data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
                confidences = []
                if "conf" in data:
                    confidences = [float(c) for c in data["conf"] if c != -1]
                
                # Pytesseract returns scores 0-100, normalize to 0.0-1.0
                avg_confidence = (float(np.mean(confidences)) / 100.0) if confidences else 0.5
                return extracted_text, avg_confidence
            except Exception as t_err:
                print(f"Tesseract fallback extraction failed: {t_err}")
                # Return empty result if all engines failed
                return "", 0.0

ocr_service = OCRService()
