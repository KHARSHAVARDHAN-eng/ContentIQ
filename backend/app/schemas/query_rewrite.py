from pydantic import BaseModel, Field

class QueryRewriteResult(BaseModel):
    original_query: str = Field(..., description="The original raw user query")
    rewritten_query: str = Field(..., description="The rewritten version of the query for retrieval")
    rewrite_reason: str = Field(..., description="Reason/explanation for the rewriting decision")
    rewrite_applied: bool = Field(..., description="Flag indicating if a rewrite was applied (true) or bypassed (false)")
    rewrite_confidence: float = Field(..., description="Confidence score of the rewrite quality (0.0 to 1.0)")
