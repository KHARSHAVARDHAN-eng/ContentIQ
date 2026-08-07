from pydantic import BaseModel, Field
from typing import List

class RerankedHitMetadata(BaseModel):
    chunk_id: str
    original_rank: int
    reranked_position: int
    reranker_score: float
    status: str  # "retained" or "discarded"
    chunk_text: str

class RerankingResult(BaseModel):
    hits: List[RerankedHitMetadata] = Field(..., description="Details of reranking evaluation")
    model_name: str = Field(..., description="Name of the cross-encoder model used")
    retained_count: int = Field(..., description="Number of chunks kept above threshold")
    discarded_count: int = Field(..., description="Number of chunks discarded below threshold")
    original_ranking: List[str] = Field(..., description="Chunk IDs before reranking")
    reranked_ranking: List[str] = Field(..., description="Chunk IDs after reranking")
    reranking_confidence: float = Field(0.9, description="Confidence of the reranking decision")
    reranking_reason: str = Field("Cross-encoder scoring and pruning completed.", description="Details explaining reranking result")
