import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.document_chunk import DocumentChunk
from app.models.chunk_embedding import ChunkEmbedding
from app.schemas.document import DocumentResponse, DocumentPreviewResponse
from app.schemas.document_chunk import DocumentChunksOverviewResponse
from app.schemas.embedding_stats import EmbeddingStatsResponse
from app.core.config import settings
from app.services.document_processor import process_document_task

router = APIRouter()

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

def format_file_size(size_in_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} TB"

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Use clean path name preventing file collisions
    file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file to disk: {str(e)}"
        )
    
    try:
        size_bytes = os.path.getsize(file_path)
        formatted_size = format_file_size(size_bytes)
    except Exception:
        formatted_size = "Unknown"

    db_doc = Document(
        name=file.filename,
        size=formatted_size,
        path=file_path,
        status="UPLOADED",
        user_id=current_user.id
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # Trigger asynchronous background document extraction pipeline
    background_tasks.add_task(process_document_task, db_doc.id)
    
    return db_doc

@router.get("/", response_model=List[DocumentResponse])
def get_user_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    docs = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.id.desc()).all()
    return docs

@router.get("/{document_id}/preview", response_model=DocumentPreviewResponse)
def get_document_preview(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.user_id == current_user.id
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Retrieve page records ordered by page number
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == doc.id
    ).order_by(DocumentPage.page_number.asc()).all()
    
    page_count = len(pages)
    
    # Aggregate text for preview
    preview_parts = []
    for page in pages:
        preview_parts.append(f"--- Page {page.page_number} ---\n{page.extracted_text}")
    
    full_preview = "\n\n".join(preview_parts)
    
    # Limit preview size to 10000 characters
    if len(full_preview) > 10000:
        full_preview = full_preview[:10000] + "\n\n... [Text Truncated for Preview] ..."
        
    return {
        "id": doc.id,
        "filename": doc.name,
        "size": doc.size,
        "status": doc.status,
        "page_count": page_count,
        "created_at": doc.created_at,
        "extracted_text_preview": full_preview or "No text extracted."
    }

@router.get("/{document_id}/chunks", response_model=DocumentChunksOverviewResponse)
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.user_id == current_user.id
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc.id
    ).order_by(DocumentChunk.chunk_index.asc()).all()
    
    total_chunks = len(chunks)
    avg_size = 0.0
    if total_chunks > 0:
        avg_size = sum(c.chunk_length for c in chunks) / total_chunks
        
    pages_count = db.query(DocumentPage).filter(
        DocumentPage.document_id == doc.id
    ).count()
    
    return {
        "total_chunks": total_chunks,
        "average_chunk_size": round(avg_size, 1),
        "page_count": pages_count,
        "chunks": chunks
    }

@router.get("/{document_id}/embedding-stats", response_model=EmbeddingStatsResponse)
def get_document_embedding_stats(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.user_id == current_user.id
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    total_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    
    embedded_chunks = db.query(ChunkEmbedding).join(DocumentChunk).filter(
        DocumentChunk.document_id == doc.id
    ).count()
    
    first_emb = db.query(ChunkEmbedding).join(DocumentChunk).filter(
        DocumentChunk.document_id == doc.id
    ).first()
    
    vector_dimension = first_emb.embedding_dimension if first_emb else 384
    
    return {
        "total_chunks": total_chunks,
        "embedded_chunks": embedded_chunks,
        "model_name": settings.EMBEDDING_MODEL_NAME,
        "vector_dimension": vector_dimension
    }
