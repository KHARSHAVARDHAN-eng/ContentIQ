from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class FlashCardDeck(Base):
    __tablename__ = "flashcard_decks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cards = relationship("FlashCard", back_populates="deck", cascade="all, delete-orphan")
    document = relationship("Document")

class FlashCard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    deck_id = Column(Integer, ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    deck = relationship("FlashCardDeck", back_populates="cards")

class StudyPack(Base):
    __tablename__ = "study_packs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)  # Stores summary text and takeaways list as JSON string
    flashcards = Column(Text, nullable=False)  # Stores flashcards list as JSON string
    mcqs = Column(Text, nullable=False)  # Stores MCQs list as JSON string
    mindmap = Column(Text, nullable=False)  # Stores mindmap structure as JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document")

