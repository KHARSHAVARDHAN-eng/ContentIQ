import json
import re
import logging
from typing import List, Dict, Any
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger("app.services.claim_extractor")

class ClaimExtractorService:
    def extract_claims(self, answer: str) -> List[Dict[str, Any]]:
        if not answer:
            return []

        # Bypass claim extraction for refusal/out-of-domain messages
        lower_ans = answer.lower()
        if any(refusal in lower_ans for refusal in ["couldn't find information", "could not find", "not supported by retrieved evidence"]):
            return []
            
        api_key = settings.GEMINI_API_KEY
        if api_key and settings.CLAIM_EXTRACTION_ENABLED:
            try:
                return self._extract_with_llm(answer, api_key)
            except Exception as e:
                logger.warning(f"LLM claim extraction failed: {e}. Falling back to rule-based parser.")
                return self._extract_with_rules(answer)
        else:
            return self._extract_with_rules(answer)

    def _extract_with_llm(self, answer: str, api_key: str) -> List[Dict[str, Any]]:
        genai.configure(api_key=api_key)
        
        system_instruction = (
            "You are a factual claim extraction agent. Your task is to extract a list of independent, factual claims from the provided text.\n"
            "Ignore any conversational greetings, filler statements, introductions (e.g. 'Sure, here is the information:'), or polite conclusions.\n"
            "Each extracted claim must be self-contained and represent a single factual assertion.\n"
            "Return a JSON object with a single field 'claims' containing a list of strings.\n"
            "Adhere strictly to valid JSON format."
        )

        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_instruction
        )

        response = model.generate_content(
            f"Extract factual claims from the following text:\n'{answer}'",
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )

        if response and response.text:
            try:
                data = json.loads(response.text.strip())
                claims_list = data.get("claims", [])
                if isinstance(claims_list, list):
                    # Filter and structure the claims
                    formatted_claims = []
                    claim_idx = 1
                    for c in claims_list:
                        c_str = str(c).strip()
                        if c_str:
                            formatted_claims.append({
                                "claim_id": f"claim_{claim_idx}",
                                "claim_text": c_str
                            })
                            claim_idx += 1
                    # Enforce max claims configuration
                    return formatted_claims[:settings.MAX_CLAIMS_PER_RESPONSE]
            except Exception as parse_err:
                logger.warning(f"Failed to parse LLM claim extraction JSON: {parse_err}")
                raise parse_err
                
        raise ValueError("Empty or invalid response from Gemini API for claim extraction")

    def _extract_with_rules(self, answer: str) -> List[Dict[str, Any]]:
        # Split text into sentences using simple punctuation check
        raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if s.strip()]
        
        # Greetings and conversational phrases to exclude
        skip_patterns = [
            r"^hello", r"^hi\b", r"^dear\b", r"^greetings", r"^sure\b", r"^here\s+is\b", 
            r"^here\s+are\b", r"^below\s+is\b", r"^below\s+are\b", r"^i\s+hope\b", 
            r"^thank\s+you", r"^thanks\b", r"^please\b", r"\?$"
        ]

        claims = []
        claim_idx = 1

        for s in raw_sentences:
            lower_s = s.lower()
            
            # Check length/words
            if len(s) < 15 or len(s.split()) < 3:
                continue
                
            # Check if it matches conversational patterns
            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, lower_s):
                    should_skip = True
                    break
                    
            if should_skip:
                continue

            claims.append({
                "claim_id": f"claim_{claim_idx}",
                "claim_text": s
            })
            claim_idx += 1

        # Enforce max claims configuration
        return claims[:settings.MAX_CLAIMS_PER_RESPONSE]

claim_extractor = ClaimExtractorService()
