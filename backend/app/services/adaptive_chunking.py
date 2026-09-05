import logging
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger("app.services.adaptive_chunking")

class BaseAdaptiveChunker(ABC):
    @abstractmethod
    def chunk_text(self, text: str, doc_name: str) -> Tuple[List[str], Dict[str, Any]]:
        pass

class RulesBasedAdaptiveChunker(BaseAdaptiveChunker):
    def chunk_text(self, text: str, doc_name: str) -> Tuple[List[str], Dict[str, Any]]:
        if not text or text.strip() in ["[Empty Page]", "[Empty Document]"]:
            return [], {
                "chunk_size": settings.ADAPTIVE_CHUNKING_DEFAULT_SIZE,
                "overlap": settings.ADAPTIVE_CHUNKING_DEFAULT_OVERLAP,
                "chunk_strategy": "empty_bypass",
                "document_type": "empty",
                "chunk_reason": "Empty document text; bypassed chunking."
            }

        # 1. Detect document type and determine size/overlap
        lower_text = text.lower()
        lower_name = doc_name.lower()
        
        if lower_name.endswith(".pptx") or lower_name.endswith(".ppt") or "presentation" in lower_name or "slide" in lower_name or "--- Page " in text:
            doc_type = "presentation slides"
            strategy = "slide_aware"
            size = settings.ADAPTIVE_CHUNKING_SLIDES_SIZE
            overlap = settings.ADAPTIVE_CHUNKING_SLIDES_OVERLAP
            reason = "PPTX/slide presentation detected; executing page-by-page slide-aware splitting."
        elif "abstract" in lower_text or "references" in lower_text or "doi:" in lower_text or "arxiv:" in lower_text or "introduction" in lower_text:
            doc_type = "research paper"
            strategy = "academic_semantic"
            size = settings.ADAPTIVE_CHUNKING_RESEARCH_PAPER_SIZE
            overlap = settings.ADAPTIVE_CHUNKING_RESEARCH_PAPER_OVERLAP
            reason = "Academic marker terms matched; executing tight research-focused parsing limits."
        elif "```" in text or "sdk" in lower_text or "api" in lower_text or "class " in lower_text or "def " in lower_text:
            doc_type = "technical documentation"
            strategy = "code_and_text"
            size = settings.ADAPTIVE_CHUNKING_TECHNICAL_DOC_SIZE
            overlap = settings.ADAPTIVE_CHUNKING_TECHNICAL_DOC_OVERLAP
            reason = "Technical or code block tokens matched; executing code-protective boundaries."
        elif "troubleshooting" in lower_text or "warranty" in lower_text or "user manual" in lower_text or "safety instructions" in lower_text:
            doc_type = "user manual"
            strategy = "large_semantic"
            size = settings.ADAPTIVE_CHUNKING_USER_MANUAL_SIZE
            overlap = settings.ADAPTIVE_CHUNKING_USER_MANUAL_OVERLAP
            reason = "Instructional manual markers matched; executing large paragraph groupings."
        else:
            doc_type = "general document"
            strategy = "default_recursive"
            size = settings.ADAPTIVE_CHUNKING_DEFAULT_SIZE
            overlap = settings.ADAPTIVE_CHUNKING_DEFAULT_OVERLAP
            reason = "Standard general document text; executing standard recursive paragraph layout."

        # 2. Extract structural blocks
        blocks = self._extract_blocks(text)
        
        # 3. Accumulate blocks into chunks respecting size and overlap boundaries
        chunks = []
        current_chunk_blocks = []
        current_length = 0
        
        for block in blocks:
            block_len = len(block)
            
            # If a single block on its own exceeds chunk_size, we split it recursively (unavoidable)
            if block_len > size:
                if current_chunk_blocks:
                    chunks.append("\n\n".join(current_chunk_blocks))
                    current_chunk_blocks = []
                    current_length = 0
                sub_chunks = self._recursive_split(block, size, overlap)
                chunks.extend(sub_chunks)
                continue
                
            # If adding this block exceeds target chunk_size
            if current_length + block_len + 2 > size:
                chunks.append("\n\n".join(current_chunk_blocks))
                
                # Implement block-level overlap window
                overlap_blocks = []
                overlap_len = 0
                for b in reversed(current_chunk_blocks):
                    if overlap_len + len(b) + 2 <= overlap:
                        overlap_blocks.insert(0, b)
                        overlap_len += len(b) + 2
                    else:
                        break
                
                current_chunk_blocks = overlap_blocks + [block]
                current_length = sum(len(b) for b in current_chunk_blocks) + (len(current_chunk_blocks) - 1) * 2
            else:
                current_chunk_blocks.append(block)
                current_length += block_len + 2
                
        if current_chunk_blocks:
            chunks.append("\n\n".join(current_chunk_blocks))

        metadata = {
            "chunk_size": size,
            "overlap": overlap,
            "chunk_strategy": strategy,
            "document_type": doc_type,
            "chunk_reason": reason
        }
        
        return [c.strip() for c in chunks if c.strip()], metadata

    def _extract_blocks(self, text: str) -> List[str]:
        lines = text.split("\n")
        blocks = []
        current_block = []
        in_code_block = False
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            
            # Code block boundaries
            if stripped.startswith("```"):
                if in_code_block:
                    current_block.append(line)
                    blocks.append("\n".join(current_block))
                    current_block = []
                    in_code_block = False
                else:
                    if current_block:
                        blocks.append("\n".join(current_block))
                    current_block = [line]
                    in_code_block = True
                continue
                
            if in_code_block:
                current_block.append(line)
                continue
                
            # Table boundaries
            if stripped.startswith("|"):
                if not in_table:
                    if current_block:
                        blocks.append("\n".join(current_block))
                    current_block = [line]
                    in_table = True
                else:
                    current_block.append(line)
                continue
            else:
                if in_table:
                    blocks.append("\n".join(current_block))
                    current_block = []
                    in_table = False
                    
            # Headings or List Items (start a new block)
            is_heading = stripped.startswith("#") or stripped.startswith("Chapter ") or stripped.startswith("Section ")
            is_list = stripped.startswith("- ") or stripped.startswith("* ") or bool(re.match(r'^\d+\.\s+', stripped))
            
            if is_heading or is_list:
                if current_block:
                    blocks.append("\n".join(current_block))
                current_block = [line]
                if is_heading:
                    blocks.append("\n".join(current_block))
                    current_block = []
                continue
                
            current_block.append(line)
            
        if current_block:
            blocks.append("\n".join(current_block))
            
        return [b for b in blocks if b.strip()]

    def _recursive_split(self, text: str, size: int, overlap: int) -> List[str]:
        # Fallback simple split when a heading/code/table block exceeds the chunk size
        if size <= 0:
            size = 500
        if overlap >= size:
            overlap = size // 2
        step = size - overlap
        if step <= 0:
            step = size
            
        splits = []
        start = 0
        while start < len(text):
            end = start + size
            splits.append(text[start:end])
            start += step
        return splits

class LLMAdaptiveChunker(BaseAdaptiveChunker):
    def __init__(self):
        self.model_name = settings.GEMINI_MODEL

    def chunk_text(self, text: str, doc_name: str) -> Tuple[List[str], Dict[str, Any]]:
        import json
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        genai.configure(api_key=api_key)
        
        system_instruction = (
            "You are an expert document chunking system.\n"
            "Your job is to analyze the text and return the optimal chunk size, overlap, strategy, document type, and reason.\n"
            "Output a JSON object with the following fields:\n"
            "1. 'chunk_size': An integer chunk character limit (e.g., between 200 and 1200).\n"
            "2. 'overlap': An integer chunk overlap character size.\n"
            "3. 'chunk_strategy': A string strategy identifier (e.g. academic_semantic, code_and_text, large_semantic, slide_aware, or default_recursive).\n"
            "4. 'document_type': A string category (e.g. research paper, technical documentation, user manual, presentation slides, or general document).\n"
            "5. 'chunk_reason': A brief reason explaining your decision.\n"
            "\n"
            "Ensure the response is valid JSON and strictly adheres to this schema. Do not add any markdown formatting outside JSON."
        )
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        )
        
        prompt = (
            f"Document Name: '{doc_name}'\n"
            f"Sample text content (first 2000 chars):\n{text[:2000]}\n"
        )
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )
        
        if response and response.text:
            data = json.loads(response.text.strip())
            # Parse parameters
            size = int(data.get("chunk_size", settings.ADAPTIVE_CHUNKING_DEFAULT_SIZE))
            overlap = int(data.get("overlap", settings.ADAPTIVE_CHUNKING_DEFAULT_OVERLAP))
            strategy = data.get("chunk_strategy", "default_recursive").strip()
            doc_type = data.get("document_type", "general document").strip()
            reason = data.get("chunk_reason", "LLM-based document chunking decisions.").strip()
            
            # Execute block splitter using LLM parameters
            rules_splitter = RulesBasedAdaptiveChunker()
            # Modify settings temporarily to force LLM parameters
            old_size = settings.ADAPTIVE_CHUNKING_DEFAULT_SIZE
            old_overlap = settings.ADAPTIVE_CHUNKING_DEFAULT_OVERLAP
            try:
                settings.ADAPTIVE_CHUNKING_DEFAULT_SIZE = size
                settings.ADAPTIVE_CHUNKING_DEFAULT_OVERLAP = overlap
                chunks, _ = rules_splitter.chunk_text(text, "force_default_name_trigger")
            finally:
                settings.ADAPTIVE_CHUNKING_DEFAULT_SIZE = old_size
                settings.ADAPTIVE_CHUNKING_DEFAULT_OVERLAP = old_overlap
                
            return chunks, {
                "chunk_size": size,
                "overlap": overlap,
                "chunk_strategy": strategy,
                "document_type": doc_type,
                "chunk_reason": reason
            }
        else:
            raise ValueError("Empty response from Gemini API during adaptive chunking decisions.")

def _simple_recursive_split(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    separators = ["\n\n", "\n", " ", ""]
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunks.append(text[start:])
            break
        cut = end
        for sep in separators:
            if sep:
                pos = text.rfind(sep, start + chunk_size // 2, end)
                if pos != -1:
                    cut = pos + len(sep)
                    break
        chunks.append(text[start:cut])
        start = cut - chunk_overlap if cut - chunk_overlap > start else cut
    return [c for c in chunks if c.strip()]

class AdaptiveChunkingService:
    def __init__(self):
        self.rules_chunker = RulesBasedAdaptiveChunker()
        
    def chunk_document(self, text: str, doc_name: str) -> Tuple[List[str], Dict[str, Any]]:
        if not settings.ADAPTIVE_CHUNKING_ENABLED:
            logger.info("Adaptive chunking is disabled. Executing standardRecursive splitting.")
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=settings.CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP,
                    length_function=len
                )
                chunks = splitter.split_text(text)
            except Exception:
                chunks = _simple_recursive_split(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)

            metadata = {
                "chunk_size": settings.CHUNK_SIZE,
                "overlap": settings.CHUNK_OVERLAP,
                "chunk_strategy": "disabled_recursive_fallback",
                "document_type": "general document",
                "chunk_reason": "Adaptive chunking is disabled in configuration settings."
            }
            return chunks, metadata
            
        strategy_type = settings.ADAPTIVE_CHUNKING_STRATEGY.lower()
        chunks = []
        metadata = {}
        
        # LLM Chunker
        if strategy_type == "llm":
            try:
                llm_chunker = LLMAdaptiveChunker()
                chunks, metadata = llm_chunker.chunk_text(text, doc_name)
            except Exception as e:
                logger.error(f"Error in LLMAdaptiveChunker: {e}. Falling back to RulesBasedAdaptiveChunker.", exc_info=True)
                chunks, metadata = self.rules_chunker.chunk_text(text, doc_name)
                
        # Rules Chunker
        elif strategy_type == "rules":
            chunks, metadata = self.rules_chunker.chunk_text(text, doc_name)
            
        # Hybrid Chunker (Default)
        else:
            if settings.GEMINI_API_KEY:
                try:
                    llm_chunker = LLMAdaptiveChunker()
                    chunks, metadata = llm_chunker.chunk_text(text, doc_name)
                    logger.info("Successfully executed LLMAdaptiveChunker.")
                except Exception as e:
                    logger.warning(f"LLMAdaptiveChunker failed: {e}. Falling back to RulesBasedAdaptiveChunker.")
                    chunks, metadata = self.rules_chunker.chunk_text(text, doc_name)
            else:
                logger.info("GEMINI_API_KEY not configured. Executing RulesBasedAdaptiveChunker.")
                chunks, metadata = self.rules_chunker.chunk_text(text, doc_name)
                
        # Log detailed adaptive chunking report
        logger.info(
            f"\n--- ADAPTIVE CHUNKING REPORT ---\n"
            f"Document: '{doc_name}'\n"
            f"Detected Type: '{metadata['document_type']}'\n"
            f"Selected Size: {metadata['chunk_size']} | Overlap: {metadata['overlap']}\n"
            f"Strategy: '{metadata['chunk_strategy']}'\n"
            f"Reason: '{metadata['chunk_reason']}'\n"
            f"Total Chunks Generated: {len(chunks)}\n"
            f"---------------------------------\n"
        )
        
        return chunks, metadata

adaptive_chunker = AdaptiveChunkingService()
