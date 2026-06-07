from pydantic import BaseModel

class EmbeddingStatsResponse(BaseModel):
    total_chunks: int
    embedded_chunks: int
    model_name: str
    vector_dimension: int
