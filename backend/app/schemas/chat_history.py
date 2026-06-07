from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any

class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    sender: str
    text: str
    citations: List[Dict[str, Any]] | None = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    user_id: int

    class Config:
        from_attributes = True

class SessionRenameRequest(BaseModel):
    title: str
