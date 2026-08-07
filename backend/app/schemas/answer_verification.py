from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ClaimVerificationResult(BaseModel):
    claim_id: str
    claim_text: str
    verification_label: str  # "VERIFIED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "CONTRADICTED"
    confidence_score: float
    supporting_chunks: List[str]
    evidence_text: str
    explanation: str

class AnswerVerificationResult(BaseModel):
    verified: bool = True
    overall_verification_score: float
    claim_verifications: List[ClaimVerificationResult]
    verification_summary: str
    claim_count: int
    verified_count: int
    partially_supported_count: int
    unsupported_count: int
    contradicted_count: int
    latency_ms: int
    metadata: Dict[str, Any] = {}
