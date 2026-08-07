from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class MetricResult(BaseModel):
    metric_name: str
    score: float  # 0.0 to 1.0
    description: str
    metadata: Dict[str, Any] = {}

class EvaluationResult(BaseModel):
    overall_score: float  # 0.0 to 1.0
    quality_grade: str  # "A", "B", "C", "F"
    metrics: Dict[str, MetricResult]
    passed: bool
    suggestions: List[str]
    evaluation_summary: str
    recommendations: List[str]
    metadata: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []

class BenchmarkStats(BaseModel):
    dataset_name: str
    run_timestamp: float
    total_queries: int
    average_overall_score: float
    metric_averages: Dict[str, float]
    quality_grade_distribution: Dict[str, int]
    pass_rate: float
    regression_warnings: List[str] = []
