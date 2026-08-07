from pydantic import BaseModel, Field

class AdaptiveRetrievalResult(BaseModel):
    retrieval_strategy: str = Field(..., description="The chosen retrieval strategy")
    selected_top_k: int = Field(..., description="The dynamic retrieval chunk size (Top-K)")
    retrieval_reason: str = Field(..., description="Detailed explanation/reason justifying the chosen top-k and strategy")
    confidence: float = Field(..., description="Confidence score for the adaptive retrieval decision (0.0 to 1.0)")
