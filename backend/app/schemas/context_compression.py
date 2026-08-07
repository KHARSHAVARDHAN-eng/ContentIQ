from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: int
    document_name: str
    page_number: int
    chunk_text: str
    score: float

class RemovedChunkInfo(BaseModel):
    chunk_id: str
    document_id: int
    document_name: str
    page_number: int
    score: float
    reason: str

class MergedChunkInfo(BaseModel):
    primary_chunk_id: str
    merged_chunk_ids: List[str]
    document_id: int
    document_name: str
    page_number: int
    overlap_length: int

class RemovedSentenceInfo(BaseModel):
    chunk_id: str
    sentence: str
    reason: str

class ContextCompressionResult(BaseModel):
    enabled: bool = True
    original_chunk_count: int
    compressed_chunk_count: int
    original_token_estimate: int
    compressed_token_estimate: int
    estimated_token_reduction: int
    compression_ratio: float
    compressed_chunks: List[ChunkMetadata]
    removed_chunks: List[RemovedChunkInfo]
    merged_chunks: List[MergedChunkInfo]
    removed_sentences: List[RemovedSentenceInfo]
    latency_ms: int
    metadata: Dict[str, Any] = {}
