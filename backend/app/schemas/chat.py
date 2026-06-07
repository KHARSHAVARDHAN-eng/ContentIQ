from pydantic import BaseModel
from typing import List

class ChatRequest(BaseModel):
    question: str

class Citation(BaseModel):
    document_name: str
    page_number: int
    chunk_index: int
    chunk_text: str

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
