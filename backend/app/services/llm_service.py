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
            # Configure genai with key
            genai.configure(api_key=api_key)
            
            system_instruction = (
                "You are a document assistant.\n"
                "Answer ONLY using the provided context.\n"
                "If the answer is not found in the context, say exactly:\n"
                "'I could not find sufficient information in the uploaded documents.'\n"
                "Never invent information. Maintain factual alignment to context."
            )
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            
            prompt = self.build_prompt(question, context_chunks)
            
            # Request response from model
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,  # Minimize creativity to enforce grounding
                )
            )
            
            answer = response.text.strip() if response.text else "I could not find sufficient information in the uploaded documents."
            sources = self._compile_sources(context_chunks)
            confidence = self._calculate_confidence(context_chunks)
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": confidence
            }
            
        except Exception as e:
            print(f"Gemini generation error: {e}")
            # Fallback to local mock on failure to avoid API down issues
            mock_answer = f"[LLM Call Failed: {e}] fallback: " + self._generate_mock_answer(question, context_chunks)
            return {
                "answer": mock_answer,
                "sources": self._compile_sources(context_chunks),
                "confidence": self._calculate_confidence(context_chunks)
            }

    def _compile_sources(self, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sources = []
        for chunk in context_chunks:
            sources.append({
                "document_name": chunk.get("document_name", "Unknown"),
                "page_number": chunk.get("page_number", 1),
                "chunk_index": chunk.get("chunk_id", 0),
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
        # Search question keywords in chunks to formulate a dummy grounded answer
        # Strip common punctuation first
        clean_q = question.replace("?", "").replace(",", "").replace(".", "").lower()
        q_words = [w for w in clean_q.split() if len(w) > 2]
        
        best_chunk = None
        best_matches = 0
        
        for chunk in context_chunks:
            text = chunk.get("chunk_text", "").lower()
            matches = sum(1 for w in q_words if w in text)
            if matches > best_matches:
                best_matches = matches
                best_chunk = chunk
                
        if best_chunk and best_matches > 0:
            text = best_chunk.get('chunk_text')
            return f"According to {best_chunk.get('document_name')} (Page {best_chunk.get('page_number')}):\n{text}"
            
        return "I could not find sufficient information in the uploaded documents."

llm_service = LLMService()
