import time
import re
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from app.core.config import settings
from app.services.embedding_service import embedding_service
from app.schemas.context_compression import (
    ContextCompressionResult,
    ChunkMetadata,
    RemovedChunkInfo,
    MergedChunkInfo,
    RemovedSentenceInfo
)

logger = logging.getLogger("app.services.context_compressor")

class ContextCompressorService:
    def compress(self, query: str, chunks: List[Dict[str, Any]]) -> ContextCompressionResult:
        start_time = time.time()
        
        # Normalize chunk_id to string for all chunks to avoid pydantic validation errors
        normalized_input_chunks = []
        for c in chunks:
            normalized_c = dict(c)
            if "chunk_id" in normalized_c:
                normalized_c["chunk_id"] = str(normalized_c["chunk_id"])
            normalized_input_chunks.append(normalized_c)
        chunks = normalized_input_chunks
        
        if not chunks:
            return ContextCompressionResult(
                enabled=settings.CONTEXT_COMPRESSION_ENABLED,
                original_chunk_count=0,
                compressed_chunk_count=0,
                original_token_estimate=0,
                compressed_token_estimate=0,
                estimated_token_reduction=0,
                compression_ratio=1.0,
                compressed_chunks=[],
                removed_chunks=[],
                merged_chunks=[],
                removed_sentences=[],
                latency_ms=0,
                metadata={"reason": "Empty input chunks"}
            )
            
        original_text = " ".join([c.get("chunk_text", "") for c in chunks])
        original_token_estimate = self._estimate_tokens(original_text)
        original_chunk_count = len(chunks)
        
        if not settings.CONTEXT_COMPRESSION_ENABLED:
            logger.info("Context Compression is disabled. Bypassing engine.")
            compressed_chunks = [
                ChunkMetadata(
                    chunk_id=c.get("chunk_id", ""),
                    document_id=c.get("document_id", 0),
                    document_name=c.get("document_name", "Unknown"),
                    page_number=c.get("page_number", 1),
                    chunk_text=c.get("chunk_text", ""),
                    score=c.get("score", 0.0)
                ) for c in chunks[:settings.MAX_CONTEXT_CHUNKS]
            ]
            return ContextCompressionResult(
                enabled=False,
                original_chunk_count=original_chunk_count,
                compressed_chunk_count=len(compressed_chunks),
                original_token_estimate=original_token_estimate,
                compressed_token_estimate=original_token_estimate,
                estimated_token_reduction=0,
                compression_ratio=1.0,
                compressed_chunks=compressed_chunks,
                removed_chunks=[],
                merged_chunks=[],
                removed_sentences=[],
                latency_ms=0,
                metadata={"bypassed": True}
            )

        # Apply MAX_CONTEXT_CHUNKS limit first on input
        working_chunks = chunks[:settings.MAX_CONTEXT_CHUNKS]
        
        removed_chunks = []
        merged_chunks = []
        removed_sentences = []
        
        # 1. Overlap Detection & Chunk Merging (run first so overlapping sliding-window chunks unify unique content)
        merged_working_chunks = self._merge_overlapping_chunks(
            working_chunks, 
            merged_chunks
        )
        
        # 2. Exact & Semantic Duplicate Chunk Detection
        deduplicated_chunks = self._remove_duplicate_chunks(
            merged_working_chunks, 
            removed_chunks, 
            settings.REDUNDANCY_THRESHOLD
        )
        
        # 3. Sentence-Level Deduplication & Boilerplate Filtering
        final_chunks = self._deduplicate_and_filter_sentences(
            merged_working_chunks, 
            removed_sentences,
            settings.SENTENCE_SIMILARITY_THRESHOLD,
            settings.LOW_INFORMATION_THRESHOLD
        )
        
        # 4. Enforce MAX_CONTEXT_TOKENS limit by dropping lowest ranked chunks
        compressed_chunks = []
        current_token_count = 0
        for chunk in final_chunks:
            chunk_tokens = self._estimate_tokens(chunk.chunk_text)
            if current_token_count + chunk_tokens <= settings.MAX_CONTEXT_TOKENS:
                compressed_chunks.append(chunk)
                current_token_count += chunk_tokens
            else:
                # Discard because it exceeds token budget
                removed_chunks.append(
                    RemovedChunkInfo(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        document_name=chunk.document_name,
                        page_number=chunk.page_number,
                        score=chunk.score,
                        reason=f"Exceeded MAX_CONTEXT_TOKENS ({settings.MAX_CONTEXT_TOKENS})"
                    )
                )

        compressed_text = " ".join([c.chunk_text for c in compressed_chunks])
        compressed_token_estimate = self._estimate_tokens(compressed_text)
        estimated_token_reduction = max(0, original_token_estimate - compressed_token_estimate)
        compression_ratio = round(compressed_token_estimate / max(1, original_token_estimate), 4)
        latency_ms = int((time.time() - start_time) * 1000)

        result = ContextCompressionResult(
            enabled=True,
            original_chunk_count=original_chunk_count,
            compressed_chunk_count=len(compressed_chunks),
            original_token_estimate=original_token_estimate,
            compressed_token_estimate=compressed_token_estimate,
            estimated_token_reduction=estimated_token_reduction,
            compression_ratio=compression_ratio,
            compressed_chunks=compressed_chunks,
            removed_chunks=removed_chunks,
            merged_chunks=merged_chunks,
            removed_sentences=removed_sentences,
            latency_ms=latency_ms,
            metadata={
                "original_chunk_count": original_chunk_count,
                "compressed_chunk_count": len(compressed_chunks),
                "original_token_estimate": original_token_estimate,
                "compressed_token_estimate": compressed_token_estimate,
                "latency_ms": latency_ms
            }
        )

        if settings.CONTEXT_COMPRESSION_DEBUG:
            logger.info(
                f"\n=== CONTEXT COMPRESSION REPORT ===\n"
                f"Original Chunks: {original_chunk_count} | Compressed Chunks: {len(compressed_chunks)}\n"
                f"Original Tokens: {original_token_estimate} | Compressed Tokens: {compressed_token_estimate}\n"
                f"Token Reduction: {estimated_token_reduction} ({round((1 - compression_ratio) * 100, 2)}% reduction)\n"
                f"Removed Chunks: {len(removed_chunks)} | Merged: {len(merged_chunks)}\n"
                f"Removed Sentences: {len(removed_sentences)}\n"
                f"Latency: {latency_ms} ms\n"
                f"=================================="
            )

        return result

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / 4.0))

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        arr1 = np.array(v1)
        arr2 = np.array(v2)
        dot = np.dot(arr1, arr2)
        n1 = np.linalg.norm(arr1)
        n2 = np.linalg.norm(arr2)
        if n1 == 0.0 or n2 == 0.0:
            return 0.0
        return float(dot / (n1 * n2))

    def _remove_duplicate_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        removed_list: List[RemovedChunkInfo],
        threshold: float
    ) -> List[Dict[str, Any]]:
        kept_chunks = []
        kept_embeddings = []

        for c in chunks:
            text = c.get("chunk_text", "").strip()
            chunk_id = c.get("chunk_id", "")
            doc_id = c.get("document_id", 0)
            doc_name = c.get("document_name", "Unknown")
            page_num = c.get("page_number", 1)
            score = c.get("score", 0.0)

            if not text:
                removed_list.append(
                    RemovedChunkInfo(
                        chunk_id=chunk_id,
                        document_id=doc_id,
                        document_name=doc_name,
                        page_number=page_num,
                        score=score,
                        reason="empty_text"
                    )
                )
                continue

            # Exact match check
            exact_duplicate = False
            for kc in kept_chunks:
                if text == kc.get("chunk_text", "").strip():
                    removed_list.append(
                        RemovedChunkInfo(
                            chunk_id=chunk_id,
                            document_id=doc_id,
                            document_name=doc_name,
                            page_number=page_num,
                            score=score,
                            reason="exact_duplicate"
                        )
                    )
                    exact_duplicate = True
                    break
            
            if exact_duplicate:
                continue

            # Semantic match check
            embedding = embedding_service.get_embedding(text)
            semantic_duplicate = False
            for idx, ke in enumerate(kept_embeddings):
                sim = self._cosine_similarity(embedding, ke)
                if sim >= threshold:
                    removed_list.append(
                        RemovedChunkInfo(
                            chunk_id=chunk_id,
                            document_id=doc_id,
                            document_name=doc_name,
                            page_number=page_num,
                            score=score,
                            reason=f"semantic_duplicate (similarity: {round(sim, 4)} with {kept_chunks[idx].get('chunk_id')})"
                        )
                    )
                    semantic_duplicate = True
                    break

            if not semantic_duplicate:
                kept_chunks.append(c)
                kept_embeddings.append(embedding)

        return kept_chunks

    def _merge_overlapping_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        merged_list: List[MergedChunkInfo]
    ) -> List[Dict[str, Any]]:
        # Merged working copy. We will keep checking and updating.
        active_chunks = [dict(c) for c in chunks]
        merged_ids = set()

        i = 0
        while i < len(active_chunks):
            if active_chunks[i]["chunk_id"] in merged_ids:
                i += 1
                continue

            j = i + 1
            while j < len(active_chunks):
                if active_chunks[j]["chunk_id"] in merged_ids:
                    j += 1
                    continue

                c1 = active_chunks[i]
                c2 = active_chunks[j]

                # Merge if from the same document and on the same or adjacent page
                if c1.get("document_id") == c2.get("document_id") and abs(c1.get("page_number", 0) - c2.get("page_number", 0)) <= 1:
                    text1 = c1.get("chunk_text", "")
                    text2 = c2.get("chunk_text", "")

                    merged_text = self._check_overlap_and_merge(text1, text2, min_chars=15)
                    if merged_text:
                        # Update primary chunk text & score
                        c1["chunk_text"] = merged_text
                        c1["score"] = max(c1.get("score", 0.0), c2.get("score", 0.0))
                        
                        # Calculate overlap length
                        overlap_len = (len(text1) + len(text2)) - len(merged_text)

                        merged_list.append(
                            MergedChunkInfo(
                                primary_chunk_id=c1["chunk_id"],
                                merged_chunk_ids=[c2["chunk_id"]],
                                document_id=c1.get("document_id", 0),
                                document_name=c1.get("document_name", "Unknown"),
                                page_number=c1.get("page_number", 1),
                                overlap_length=max(0, overlap_len)
                            )
                        )
                        
                        # Mark second chunk as merged
                        merged_ids.add(c2["chunk_id"])
                        
                        # Reset search to check if we can merge the newly updated chunk i with anything else
                        j = i + 1
                        continue
                j += 1
            i += 1

        return [c for c in active_chunks if c["chunk_id"] not in merged_ids]

    def _check_overlap_and_merge(self, text1: str, text2: str, min_chars: int = 15) -> Optional[str]:
        t1 = text1.strip()
        t2 = text2.strip()

        # If identical or full substring, let duplicate detection handle removal
        if t2 == t1 or t2 in t1 or t1 in t2:
            return None

        max_check = min(len(t1), len(t2))
        # Case A: Suffix of text1 matches prefix of text2
        for l in range(max_check - 1, min_chars - 1, -1):
            if t1[-l:] == t2[:l]:
                return t1 + t2[l:]

        # Case B: Suffix of text2 matches prefix of text1
        for l in range(max_check - 1, min_chars - 1, -1):
            if t2[-l:] == t1[:l]:
                return t2 + t1[l:]

        return None

    def _deduplicate_and_filter_sentences(
        self, 
        chunks: List[Dict[str, Any]], 
        removed_sentences_list: List[RemovedSentenceInfo],
        similarity_threshold: float,
        low_info_threshold: int
    ) -> List[ChunkMetadata]:
        processed_chunks = []
        seen_sentences = []
        seen_embeddings = []

        # Common boilerplate phrases to filter out
        boilerplate_patterns = [
            r"copyright\s+©",
            r"all\s+rights\s+reserved",
            r"page\s+\d+",
            r"^draft$",
            r"^confidential$"
        ]

        for c in chunks:
            chunk_id = c.get("chunk_id", "")
            doc_id = c.get("document_id", 0)
            doc_name = c.get("document_name", "Unknown")
            page_num = c.get("page_number", 1)
            score = c.get("score", 0.0)
            text = c.get("chunk_text", "")

            # Split into sentences using a regex
            raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            kept_chunk_sentences = []

            for s in raw_sentences:
                # Boilerplate / low information validation
                is_boilerplate = False
                lower_s = s.lower()
                for pattern in boilerplate_patterns:
                    if re.search(pattern, lower_s):
                        is_boilerplate = True
                        break

                if is_boilerplate:
                    removed_sentences_list.append(
                        RemovedSentenceInfo(
                            chunk_id=chunk_id,
                            sentence=s,
                            reason="boilerplate"
                        )
                    )
                    continue

                if len(s) < low_info_threshold or len(s.split()) < 3:
                    removed_sentences_list.append(
                        RemovedSentenceInfo(
                            chunk_id=chunk_id,
                            sentence=s,
                            reason="low_information"
                        )
                    )
                    continue

                # Duplicate check (exact match first)
                exact_dup = False
                normalized_s = re.sub(r'[^\w\s]', '', lower_s).strip()
                for ss in seen_sentences:
                    normalized_ss = re.sub(r'[^\w\s]', '', ss.lower()).strip()
                    if normalized_s == normalized_ss:
                        removed_sentences_list.append(
                            RemovedSentenceInfo(
                                chunk_id=chunk_id,
                                sentence=s,
                                reason="duplicate_sentence_exact"
                            )
                        )
                        exact_dup = True
                        break

                if exact_dup:
                    continue

                # Semantic duplicate check (batch embeddings of kept sentences is better, but here we embed one-by-one)
                s_embedding = embedding_service.get_embedding(s)
                semantic_dup = False
                for idx, se in enumerate(seen_embeddings):
                    sim = self._cosine_similarity(s_embedding, se)
                    if sim >= similarity_threshold:
                        removed_sentences_list.append(
                            RemovedSentenceInfo(
                                chunk_id=chunk_id,
                                sentence=s,
                                reason=f"duplicate_sentence_semantic (similarity: {round(sim, 4)})"
                            )
                        )
                        semantic_dup = True
                        break

                if not semantic_dup:
                    kept_chunk_sentences.append(s)
                    seen_sentences.append(s)
                    seen_embeddings.append(s_embedding)

            # Reconstruct chunk text
            new_text = " ".join(kept_chunk_sentences).strip()
            if new_text:
                processed_chunks.append(
                    ChunkMetadata(
                        chunk_id=chunk_id,
                        document_id=doc_id,
                        document_name=doc_name,
                        page_number=page_num,
                        chunk_text=new_text,
                        score=score
                    )
                )

        return processed_chunks

context_compressor = ContextCompressorService()
