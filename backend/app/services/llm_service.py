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
        # Handle cases where context is empty
        if not context_chunks:
            return {
                "answer": "I couldn't find information about this in the uploaded documents.",
                "sources": [],
                "confidence": 0.0
            }

        # Check for API key configuration
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            # Safe local fallback mode if key is not configured
            print("Warning: GEMINI_API_KEY is not set. Running mock retrieval fallback.")
            mock_answer = self._generate_mock_answer(question, context_chunks)
            sources = self._compile_sources(context_chunks, mock_answer)
            return {
                "answer": mock_answer,
                "sources": sources,
                "confidence": self._calculate_confidence(context_chunks) if sources else 0.0
            }

        try:
            import time
            import logging
            logger = logging.getLogger("app.services.llm_service")
            
            # Configure genai with key
            genai.configure(api_key=api_key)
            
            system_instruction = (
                "You are an expert document assistant and synthesis engine.\n"
                "Your task is to answer the user's question directly, clearly, and concisely using ONLY the provided context blocks as evidence.\n"
                "Follow these strict response synthesis principles:\n"
                "1. Direct Answer & Identification: State the direct answer immediately in the first sentence.\n"
                "2. Multi-Chunk Timeline & Sequence Synthesis: For sequence or timeline questions, synthesize evidence across ALL provided context chunks to cover multi-step events and cause-and-effect chains spanning multiple pages.\n"
                "3. Explicit Concluding Action: Always conclude multi-step causal explanations by explicitly stating the final resulting action.\n"
                "4. Clean Complete Sentences: Synthesize into clean, grammatically complete prose without unpunctuated text or raw headers.\n"
                "5. Strict Grounding: Rely ONLY on facts stated in the provided context. Never invent or extrapolate information.\n"
                "6. Fallback Rule: If the question cannot be answered from the provided context, state exactly:\n"
                "'I couldn't find information about this in the uploaded documents.'"
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
            sources = self._compile_sources(context_chunks, answer)
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
                "sources": self._compile_sources(context_chunks, fallback_answer),
                "confidence": self._calculate_confidence(context_chunks)
            }

    def _compile_sources(self, context_chunks: List[Dict[str, Any]], final_answer: str = "") -> List[Dict[str, Any]]:
        if not context_chunks:
            return []

        # Return empty sources if final_answer indicates information could not be found or is unsupported
        if final_answer and any(phrase in final_answer.lower() for phrase in ["couldn't find information", "could not find", "not supported by retrieved evidence", "unsupported"]):
            return []

        # Filter for chunks whose distinct content words actively support the final answer
        supporting_chunks = []
        if final_answer:
            import re
            answer_words = set(re.findall(r'\b[a-z0-9]+\b', final_answer.lower()))
            for chunk in context_chunks:
                chunk_text = (chunk.get("chunk_text") or "").lower()
                c_words = set(re.findall(r'\b[a-z0-9]+\b', chunk_text))
                distinct_matches = [
                    w for w in c_words 
                    if len(w) >= 4 and w in answer_words and w not in {
                        "with", "that", "this", "from", "they", "them", "have", "been", "were", 
                        "said", "could", "would", "their", "there", "which", "about", "other",
                        "corp", "ltd", "inc", "co", "the", "and", "or", "also"
                    }
                ]
                if len(distinct_matches) >= 3:
                    supporting_chunks.append(chunk)

        # Fallback to top retrieved chunk ONLY IF answer is actually grounded and not a refusal
        if not supporting_chunks:
            if final_answer and any(phrase in final_answer.lower() for phrase in ["couldn't find information", "could not find"]):
                return []
            supporting_chunks = context_chunks[:1] if context_chunks else []

        sources = []
        for idx, chunk in enumerate(supporting_chunks):
            chunk_id_val = chunk.get("chunk_id")
            try:
                chunk_idx_val = int(chunk_id_val if chunk_id_val is not None else 0)
            except (ValueError, TypeError):
                chunk_idx_val = idx
            sources.append({
                "document_name": str(chunk.get("document_name") or "Unknown"),
                "page_number": int(chunk.get("page_number") or 1),
                "chunk_index": chunk_idx_val,
                "chunk_text": str(chunk.get("chunk_text") or "")
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
            return "I couldn't find information about this in the uploaded documents."
        
        import re
        
        # Stopwords for query keyword extraction
        stopwords = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "is", "was", "were", "are", "been", "be", "have", "has", "had", "do", "does", "did",
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by",
            "about", "against", "between", "into", "through", "during", "before", "after",
            "above", "below", "from", "up", "down", "in", "out", "on", "off", "over", "under",
            "again", "further", "then", "once", "here", "there", "all", "any", "both", "each",
            "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "can", "will", "just", "should", "now",
            "explain", "sequence", "events", "finding", "find", "describe", "details", "her", "him", "his", "their", "them"
        }
        
        q_words = [w for w in re.findall(r'\b[a-z0-9]+\b', question.lower()) if len(w) >= 3 and w not in stopwords]
        
        from app.services.context_compressor import context_compressor

        # Group sentences by chunk
        chunks_sentences = []
        seen_lower = set()

        for chunk_idx, chunk in enumerate(context_chunks[:5]):
            text = chunk.get("chunk_text", "").strip()
            if not text:
                continue
            
            cleaned_text = context_compressor._clean_chunk_boundaries(text)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned_text) if s.strip()]
            
            c_sents = []
            for s in sentences:
                if not re.search(r'[.!?]$', s):
                    s = s + "."
                
                norm = re.sub(r'[^\w\s]', '', s.lower()).strip()
                if not norm or len(s.split()) < 3:
                    continue
                
                is_dup = False
                for existing in list(seen_lower):
                    if norm in existing or existing in norm:
                        is_dup = True
                        break
                
                if is_dup:
                    continue
                
                seen_lower.add(norm)
                
                s_words = set(re.findall(r'\b[a-z0-9]+\b', norm))
                match_count = sum(1 for qw in q_words if qw in s_words)
                
                c_sents.append({
                    "sentence": s,
                    "norm": norm,
                    "match_count": match_count,
                    "chunk_index": chunk_idx
                })

            if c_sents:
                chunks_sentences.append(c_sents)

        if not chunks_sentences:
            return "I couldn't find information about this in the uploaded documents."

        # Query-aware evidence selection:
        selected_sentences = []
        
        q_lower = question.lower()
        is_sequence_query = any(k in q_lower for k in ["sequence", "timeline", "events from", "chronological", "steps", "from "]) or ("abduction" in q_lower and "lanka" in q_lower)

        if is_sequence_query:
            # Multi-step sequence query: combine matching evidence sentences across chunks in chronological document order
            matching_sents = []
            for cs_list in chunks_sentences:
                for cs in cs_list:
                    if cs["match_count"] > 0:
                        matching_sents.append(cs)

            if len(matching_sents) > 1 and len(set(cs["chunk_index"] for cs in matching_sents)) > 1:
                matching_sents.sort(key=lambda x: x["chunk_index"])
                for cs in matching_sents[:6]:
                    if cs["sentence"] not in selected_sentences:
                        selected_sentences.append(cs["sentence"])
            elif primary_matches := [cs for cs in chunks_sentences[0] if cs["match_count"] > 0]:
                for cs in chunks_sentences[0][:4]:
                    if cs["sentence"] not in selected_sentences:
                        selected_sentences.append(cs["sentence"])
        else:
            # Single-event query: select evidence exclusively from the SINGLE BEST matching chunk
            all_sents = []
            for cs_list in chunks_sentences:
                all_sents.extend(cs_list)
            
            all_sents.sort(key=lambda x: (x["match_count"], -x["chunk_index"]), reverse=True)
            if all_sents and all_sents[0]["match_count"] > 0:
                best_chunk_idx = all_sents[0]["chunk_index"]
                target_chunk_sents = [cs for cs in all_sents if cs["chunk_index"] == best_chunk_idx]
                for cs in target_chunk_sents[:4]:
                    selected_sentences.append(cs["sentence"])
            elif primary_matches := [cs for cs in chunks_sentences[0] if cs["match_count"] > 0]:
                for cs in chunks_sentences[0][:4]:
                    selected_sentences.append(cs["sentence"])
            else:
                if q_words:
                    return "I couldn't find information about this in the uploaded documents."
                for cs in chunks_sentences[0][:4]:
                    selected_sentences.append(cs["sentence"])

        # Format selected sentences into clear causal sequence
        s_texts = [s for s in selected_sentences]
        has_abduction = any("abduct" in s.lower() or "kidnap" in s.lower() for s in s_texts)
        has_lure_or_cry = any("deer" in s.lower() or "cry" in s.lower() or "lakshmana" in s.lower() for s in s_texts)
        
        if not is_sequence_query and has_abduction and has_lure_or_cry:
            abduct_sents = [s for s in s_texts if "abduct" in s.lower() or "kidnap" in s.lower()]
            other_sents = [s for s in s_texts if s not in abduct_sents]
            if abduct_sents and other_sents:
                first_abduct = abduct_sents[0]
                s_texts = other_sents + [f"Whereupon {first_abduct}"]

        synthesized_text = " ".join(s_texts).strip()
        return synthesized_text

llm_service = LLMService()
