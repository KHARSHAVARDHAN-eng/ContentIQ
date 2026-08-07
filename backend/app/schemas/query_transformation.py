from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class QueryTransformationResult(BaseModel):
    original_query: str = Field(..., description="The original raw user query")
    rewritten_query: str = Field(..., description="The rewritten version of the query")
    expanded_queries: List[str] = Field(default_factory=list, description="List of generated query expansions/synonyms")
    generated_retrieval_queries: List[str] = Field(default_factory=list, description="All variations of queries generated for retrieval")
    query_intent: str = Field(..., description="The primary detected query intent")
    ambiguity_score: float = Field(default=0.0, description="The ambiguity score between 0.0 and 1.0")
    confidence_score: float = Field(default=1.0, description="Overall transformation confidence score")
    detected_entities: List[str] = Field(default_factory=list, description="Important entities extracted from the query")
    detected_keywords: List[str] = Field(default_factory=list, description="Technical keywords extracted from the query")
    transformation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary for the transformations performed")
