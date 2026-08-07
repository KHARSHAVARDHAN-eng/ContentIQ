from pydantic import BaseModel
from typing import List, Optional
from app.schemas.query_analysis import QueryAnalysis
from app.schemas.query_rewrite import QueryRewriteResult
from app.schemas.adaptive_retrieval import AdaptiveRetrievalResult
from app.schemas.retrieval_verification import RetrievalVerificationResult
from app.schemas.reranking import RerankingResult
from app.schemas.hybrid_retrieval import HybridRetrievalResult
from app.schemas.query_transformation import QueryTransformationResult
from app.schemas.context_compression import ContextCompressionResult
from app.schemas.answer_verification import AnswerVerificationResult
from app.schemas.self_reflection import SelfReflectionResult
from app.schemas.confidence import ConfidenceResult
from app.schemas.evaluation import EvaluationResult
from app.schemas.agentic_rag import AgenticRAGResult

class SearchRequest(BaseModel):
    query: str

class SearchHit(BaseModel):
    chunk_text: str
    score: float
    page_number: int
    document_name: str
    document_id: int

class SearchResponse(BaseModel):
    chunks: List[SearchHit]
    query_analysis: Optional[QueryAnalysis] = None
    query_rewrite: Optional[QueryRewriteResult] = None
    adaptive_retrieval: Optional[AdaptiveRetrievalResult] = None
    retrieval_verification: Optional[RetrievalVerificationResult] = None
    reranking: Optional[RerankingResult] = None
    hybrid_retrieval: Optional[HybridRetrievalResult] = None
    query_transformation: Optional[QueryTransformationResult] = None
    context_compression: Optional[ContextCompressionResult] = None
    answer_verification: Optional[AnswerVerificationResult] = None
    self_reflection: Optional[SelfReflectionResult] = None
    confidence: Optional[ConfidenceResult] = None
    evaluation: Optional[EvaluationResult] = None
    agentic_rag: Optional[AgenticRAGResult] = None
