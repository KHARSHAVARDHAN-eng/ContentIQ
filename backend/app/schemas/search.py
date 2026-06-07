from pydantic import BaseModel
from typing import List

class SearchRequest(BaseModel):
    query: str

class SearchHit(BaseModel):
    chunk_text: str
    score: float
    page_number: int
    document_name: str
    document_id: int

class SearchResponse(BaseModel):
    chunks: List[SearchHit]
