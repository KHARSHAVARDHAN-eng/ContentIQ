from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base

class RAGEvaluation(Base):
    __tablename__ = "rag_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    retrieved_chunks_count = Column(Integer, nullable=False)
    user_feedback = Column(Integer, default=0) # 1 = Thumbs Up, -1 = Thumbs Down, 0 = Unrated
    faithfulness_score = Column(Float, nullable=True)
    answer_relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
