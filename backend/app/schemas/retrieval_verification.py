from pydantic import BaseModel, Field
from typing import Optional

class RetrievalVerificationResult(BaseModel):
    verification_status: str = Field(..., description="The verification status: PASS, WARNING, or FAIL")
    retrieval_confidence: float = Field(..., description="Calculated retrieval confidence score (0.0 to 1.0)")
    quality_score: float = Field(..., description="Calculated retrieval quality score (0.0 to 1.0)")
    verification_reason: str = Field(..., description="Detailed explanation/reason justifying the verification decision")
    recommended_action: str = Field(..., description="The recommended action: Continue normally, Continue with caution, or Trigger retrieval retry")
    first_attempt_status: Optional[str] = Field(default=None, description="The verification status of the first retrieval attempt")
    first_attempt_score: Optional[float] = Field(default=None, description="The quality score of the first retrieval attempt")
    retry_performed: bool = Field(default=False, description="Flag indicating if a retrieval retry was executed")
    final_attempt_status: Optional[str] = Field(default=None, description="The verification status of the final retrieval attempt")
    final_attempt_score: Optional[float] = Field(default=None, description="The quality score of the final retrieval attempt")
