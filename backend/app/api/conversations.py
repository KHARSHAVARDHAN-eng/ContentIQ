from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.chat_history import ChatSession, ChatMessage
from app.schemas.chat_history import ChatSessionResponse, ChatMessageResponse, SessionRenameRequest

router = APIRouter()

@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.created_at.desc()).all()
    return sessions

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify owner separation
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found."
        )
        
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    # Format JSON citations
    formatted_messages = []
    for m in messages:
        citations_list = []
        if m.citations:
            try:
                citations_list = json.loads(m.citations)
            except Exception:
                pass
        formatted_messages.append({
            "id": m.id,
            "session_id": m.session_id,
            "sender": m.sender,
            "text": m.text,
            "citations": citations_list,
            "created_at": m.created_at
        })
    return formatted_messages

@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
def rename_chat_session(
    session_id: int,
    rename_req: SessionRenameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found."
        )
        
    session.title = rename_req.title.strip() or "Untitled Chat"
    db.commit()
    db.refresh(session)
    return session

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found."
        )
        
    db.delete(session)
    db.commit()
    return
