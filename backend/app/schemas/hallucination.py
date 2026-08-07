from pydantic import BaseModel, Field
from typing import List

class HallucinationDetectionResult(BaseModel):
    hallucination_status: str = Field(..., description="Grounding validation status: CLEAN, WARNING, or FAILED")
    confidence_score: float = Field(..., description="Fact-checking grounding confidence ratio (0.0 to 1.0)")
    unsupported_claims: List[str] = Field(..., description="Answers claims/sentences unsupported by evidence chunks")
    grounded_claims: List[str] = Field(..., description="Answers claims/sentences verified by evidence chunks")
    reasoning: str = Field(..., description="Explanation detailing the grounding findings")
