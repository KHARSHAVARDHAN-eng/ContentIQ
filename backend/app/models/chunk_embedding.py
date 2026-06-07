from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chunk = relationship("DocumentChunk", back_populates="embedding")
