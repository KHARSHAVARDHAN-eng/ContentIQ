from pydantic import BaseModel, Field
from typing import List, Optional

class HybridRetrievalHitMetadata(BaseModel):
    chunk_id: str
    source: str  # "dense", "sparse", "hybrid"
    dense_score: float
    sparse_score: float
    normalized_dense_score: float
    normalized_sparse_score: float
    final_score: float
    document_id: int
    page_number: int
    chunk_text: str

class HybridRetrievalResult(BaseModel):
    hits: List[HybridRetrievalHitMetadata] = Field(..., description="Details of the merged hybrid search candidate list")
    original_dense_ranking: List[str] = Field(..., description="Ordered list of chunk IDs from dense retrieval")
    original_sparse_ranking: List[str] = Field(..., description="Ordered list of chunk IDs from sparse retrieval")
    merged_ranking: List[str] = Field(..., description="Ordered list of chunk IDs in final merged hybrid list")
