from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class FlashCardBase(BaseModel):
    question: str
    answer: str

class FlashCardCreate(FlashCardBase):
    pass

class FlashCardResponse(FlashCardBase):
    id: int
    deck_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class FlashCardDeckBase(BaseModel):
    title: str
    document_id: Optional[int] = None

class FlashCardGenerateRequest(BaseModel):
    document_id: int

class FlashCardDeckCreate(FlashCardDeckBase):
    pass

class FlashCardDeckResponse(FlashCardDeckBase):
    id: int
    user_id: int
    created_at: datetime
    cards: List[FlashCardResponse] = []

    class Config:
        from_attributes = True

# MCQ generator schemas
class MCQBase(BaseModel):
    question: str
    options: List[str]
    correct_answer: str  # e.g., 'A', 'B', 'C', 'D'
    explanation: str

class MCQRequest(BaseModel):
    document_id: int
    difficulty: str  # "Easy", "Medium", "Hard"
    count: Optional[int] = 5

class MCQResponse(BaseModel):
    mcqs: List[MCQBase]

# Mind Map schemas
class MindMapNode(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    children: List["MindMapNode"] = []

class MindMapRequest(BaseModel):
    document_id: int

class MindMapResponse(BaseModel):
    title: str
    root: MindMapNode

MindMapNode.model_rebuild()

# Study Pack schemas
class StudyPackRequest(BaseModel):
    document_id: int

class StudyPackResponse(BaseModel):
    id: int
    document_id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


