from pydantic import BaseModel
from datetime import datetime

class DocumentBase(BaseModel):
    name: str
    size: str
    status: str
    ocr_confidence: float | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    chunk_strategy: str | None = None
    document_type: str | None = None
    chunk_reason: str | None = None

class DocumentCreate(DocumentBase):
    path: str

class DocumentResponse(DocumentBase):
    id: int
    created_at: datetime
    user_id: int

    class Config:
        from_attributes = True

class DocumentPreviewResponse(BaseModel):
    id: int
    filename: str
    size: str
    status: str
    page_count: int
    ocr_confidence: float | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    chunk_strategy: str | None = None
    document_type: str | None = None
    chunk_reason: str | None = None
    created_at: datetime
    extracted_text_preview: str
