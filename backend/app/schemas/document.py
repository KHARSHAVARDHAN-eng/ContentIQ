from pydantic import BaseModel
from datetime import datetime

class DocumentBase(BaseModel):
    name: str
    size: str
    status: str
    ocr_confidence: float | None = None

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
    created_at: datetime
    extracted_text_preview: str

