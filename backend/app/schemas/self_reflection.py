from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class SelfReflectionResult(BaseModel):
    reflection_summary: str
    detected_issues: List[str]
    improvement_suggestions: List[str]
    quality_score: float
    refinement_performed: bool
    original_answer: str
    refined_answer: Optional[str] = None
    confidence: float
    metadata: Dict[str, Any] = {}
