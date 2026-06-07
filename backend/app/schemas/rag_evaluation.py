from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional

class FeedbackRequest(BaseModel):
    feedback: int = Field(..., description="1 = Thumbs Up, -1 = Thumbs Down, 0 = Clear")

class EvaluationLogResponse(BaseModel):
    id: int
    query: str
    answer: str
    latency_ms: int
    retrieved_chunks_count: int
    user_feedback: int
    faithfulness_score: Optional[float] = None
    answer_relevance_score: Optional[float] = None
    created_at: datetime
    user_id: int
    document_id: Optional[int] = None
    document_name: Optional[str] = None

    class Config:
        from_attributes = True

class DailyMetric(BaseModel):
    date: str
    avg_latency: float
    avg_faithfulness: float
    avg_relevance: float
    total_queries: int
    positive_feedback_pct: float

class EvaluationStatsResponse(BaseModel):
    total_queries: int
    avg_latency_ms: float
    avg_faithfulness: float
    avg_relevance: float
    thumbs_up_count: int
    thumbs_down_count: int
    positive_feedback_pct: float
    daily_metrics: List[DailyMetric]
