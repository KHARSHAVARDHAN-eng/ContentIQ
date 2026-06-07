from pydantic import BaseModel
from typing import List

class ChunkDetail(BaseModel):
    id: int
    page_number: int
    chunk_index: int
    chunk_length: int
    chunk_text: str

class DocumentChunksOverviewResponse(BaseModel):
    total_chunks: int
    average_chunk_size: float
    page_count: int
    chunks: List[ChunkDetail]
