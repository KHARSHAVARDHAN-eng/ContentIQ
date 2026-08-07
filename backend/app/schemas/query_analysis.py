from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class QueryAnalysis(BaseModel):
    raw_query: str = Field(..., description="The original raw user query")
    intent: str = Field(..., description="Classified intent (factual, summarization, explanation, comparison, analytical, procedural, conversational, multi-intent)")
    complexity: str = Field(..., description="Estimated complexity (Simple, Medium, Complex)")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    suggested_filters: Optional[Dict[str, Any]] = Field(default=None, description="Suggested filters")
    intent_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score for the detected intent")
    complexity_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score for the detected complexity")
    reasoning: Optional[str] = Field(default=None, description="Justification explaining the classification decisions")
    query_classification: Optional[str] = Field(default="informational", description="Query type (informational, keyword, conversational)")
    ambiguity_score: Optional[float] = Field(default=0.0, description="The ambiguity score between 0.0 and 1.0")
    missing_context: Optional[bool] = Field(default=False, description="Flag indicating if some context is missing")
    detected_entities: Optional[List[str]] = Field(default_factory=list, description="Important entities extracted from the query")
    technical_keywords: Optional[List[str]] = Field(default_factory=list, description="Technical keywords detected in the query")
