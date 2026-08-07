from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class FactorScore(BaseModel):
    factor_name: str
    raw_value: float
    normalized_score: float
    weight: float
    contribution: float

class ConfidenceResult(BaseModel):
    overall_score: float  # 0.0 to 100.0
    confidence_level: str  # "HIGH", "MEDIUM", "LOW"
    factor_breakdown: List[FactorScore]
    explanation: str
    recommendations: List[str]
    metadata: Dict[str, Any] = {}
