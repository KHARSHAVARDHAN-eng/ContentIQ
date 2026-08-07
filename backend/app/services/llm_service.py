# ==========================================
# PRODUCTION LOCKED - STABLE RAG V1 CORE
# DO NOT MODIFY without explicit regression verification
# ==========================================

import google.generativeai as genai
from typing import List, Dict, Any
from app.core.config import settings

class LLMService:
    def __init__(self):
        # Configure model parameters
        self.model_name = settings.GEMINI_MODEL

    def build_prompt(self, question: str, context_chunks: List[Dict[str, Any]]) -> str:
        # Build prompt string containing context references
        context_text = ""
        for idx, chunk in enumerate(context_chunks):
            context_text += (
                f"--- Source Block {idx + 1} ---\n"
                f"Document Name: {chunk.get('document_name', 'Unknown')}\n"
                f"Page Number: {chunk.get('page_number', 'N/A')}\n"
                f"Chunk ID: {chunk.get('chunk_id', idx)}\n"
                f"Text:\n{chunk.get('chunk_text', '')}\n\n"
            )
        
        prompt = (
            f"Context information:\n"
            f"=====================\n"
            f"{context_text}"
            f"=====================\n"
            f"User Question: {question}\n"
        )
        return prompt

    def generate_answer(self, question: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Handle cases where context is completely empty
        if not context_chunks:
            return {
                "answer": "I could not find sufficient information in the uploaded documents.",
                "sources": [],
                "confidence": 0.0
            }

        # Check for API key configuration
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            # Safe local fallback mode if key is not configured
            print("Warning: GEMINI_API_KEY is not set. Running mock retrieval fallback.")
            mock_answer = self._generate_mock_answer(question, context_chunks)
            sources = self._compile_sources(context_chunks)
            return {
                "answer": mock_answer,
                "sources": sources,
                "confidence": self._calculate_confidence(context_chunks)
            }

        try:
            import time
            import logging
            logger = logging.getLogger("app.services.llm_service")
            
            # Configure genai with key
            genai.configure(api_key=api_key)
            
            system_instruction = (
                "You are an expert document assistant and synthesis engine.\n"
                "Your task is to answer the user's question directly, clearly, and concisely in complete, natural English sentences.\n"
                "Follow these strict response synthesis principles:\n"
                "1. Direct Answer First: State the core factual answer directly in the very first sentence.\n"
                "2. Synthesize Evidence: Combine relevant facts from the provided context blocks smoothly into coherent prose.\n"
                "3. Clean Sentences: Every sentence must be a complete, well-formed sentence. Never copy broken word fragments, leading partial sentences, or raw context headers.\n"
                "4. Strict Grounding: Rely ONLY on facts stated in the provided context. Never invent or extrapolate information.\n"
                "5. Fallback Rule: If the answer cannot be determined from the provided context, state exactly:\n"
                "'I could not find sufficient information in the uploaded documents.'\n"
                "6. No Duplication: Eliminate duplicate facts or repeated sentences."
            )
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            
            prompt = self.build_prompt(question, context_chunks)
            
            # Request response from model with retry and exponential backoff
            max_retries = 3
            backoff_factor = 2
            initial_delay = 1.0 # seconds
            
            response = None
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.0,  # Minimize creativity to enforce grounding
                        )
                    )
                    break
                except Exception as ex:
                    last_exception = ex
                    logger.warning(f"Gemini API generation attempt {attempt + 1} failed: {ex}. Retrying...")
                    if attempt < max_retries - 1:
                        sleep_time = initial_delay * (backoff_factor ** attempt)
                        time.sleep(sleep_time)
            
            if response is None:
                raise last_exception
            
            answer = response.text.strip() if response.text else "I could not find sufficient information in the uploaded documents."
            sources = self._compile_sources(context_chunks)
            confidence = self._calculate_confidence(context_chunks)
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": confidence
            }
            
        except Exception as e:
            # Backend logging for Gemini failures
            import logging
            logger = logging.getLogger("app.services.llm_service")
            logger.error(f"Gemini generation error: {e}", exc_info=True)
            
            err_msg = str(e).lower()
            is_quota_or_timeout = (
                "429" in err_msg or
                "quota" in err_msg or
                "exhausted" in err_msg or
                "limit" in err_msg or
                "timeout" in err_msg or
                "deadline" in err_msg or
                "rate" in err_msg or
                "temporarily unavailable" in err_msg
            )
            
            if is_quota_or_timeout:
                friendly_message = "AI generation is temporarily unavailable due to API quota limits. Relevant document sources are shown below."
            else:
                friendly_message = "AI generation is temporarily unavailable. Relevant document sources are shown below."
            
            # Fallback mode that returns top retrieved chunks formatted cleanly
            fallback_answer = friendly_message + "\n\n"
            for idx, chunk in enumerate(context_chunks[:3]):
                doc_name = chunk.get("document_name", "Unknown")
                page_num = chunk.get("page_number", "N/A")
                text = chunk.get("chunk_text", "").strip()
                fallback_answer += f"[{idx + 1}] Source: {doc_name} (Page {page_num}):\n{text}\n\n"
            
            return {
                "answer": fallback_answer,
                "sources": self._compile_sources(context_chunks),
                "confidence": self._calculate_confidence(context_chunks)
            }

    def _compile_sources(self, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sources = []
        for idx, chunk in enumerate(context_chunks):
            chunk_id_val = chunk.get("chunk_id", 0)
            try:
                chunk_idx_val = int(chunk_id_val)
            except (ValueError, TypeError):
                chunk_idx_val = idx
            sources.append({
                "document_name": chunk.get("document_name", "Unknown"),
                "page_number": chunk.get("page_number", 1),
                "chunk_index": chunk_idx_val,
                "chunk_text": chunk.get("chunk_text", "")
            })
        return sources

    def _calculate_confidence(self, context_chunks: List[Dict[str, Any]]) -> float:
        # Use top score as representative confidence proxy (clamped 0.0 - 1.0)
        scores = [chunk.get("score", 0.0) for chunk in context_chunks if "score" in chunk]
        if not scores:
            return 0.0
        top_score = max(scores)
        return round(float(top_score), 4)

    def _generate_mock_answer(self, question: str, context_chunks: List[Dict[str, Any]]) -> str:
        if not context_chunks:
            return "I could not find sufficient information in the uploaded documents."
        
        import re
        cleaned_sentences = []
        seen_lower = set()
        
        for chunk in context_chunks[:3]:
            text = chunk.get("chunk_text", "").strip()
            if not text:
                continue
            
            # Apply boundary cleaning to strip incomplete leading/trailing fragments
            from app.services.context_compressor import context_compressor
            text = context_compressor._clean_chunk_boundaries(text)
            
            # Extract complete grammatical sentences ending in punctuation (. ! ?)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            chunk_sentence_count = 0
            
            for s in sentences:
                # Append terminal period if sentence lacks ending punctuation (e.g. OCR outputs or list headers)
                if not re.search(r'[.!?]$', s):
                    s = s + "."
                
                norm = re.sub(r'[^\w\s]', '', s.lower()).strip()
                if not norm or len(s.split()) < 3:
                    continue

                # Check for substring / overlap sentence duplication
                is_dup = False
                for existing in list(seen_lower):
                    if norm in existing or existing in norm:
                        is_dup = True
                        break
                
                if not is_dup:
                    seen_lower.add(norm)
                    cleaned_sentences.append(s)
                    chunk_sentence_count += 1
                    if chunk_sentence_count >= 2:
                        break
        
        if not cleaned_sentences:
            return "I could not find sufficient information in the uploaded documents."
        
        # Synthesize clean sentences into a natural response paragraph
        synthesized_text = " ".join(cleaned_sentences[:4]).strip()
        return synthesized_text

llm_service = LLMService()
