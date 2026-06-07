from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from qdrant_client.http import models as qdrant_models

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def grounded_chat(
    chat_req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = chat_req.question.strip()
    if not question:
        return {
            "answer": "Please ask a valid question.",
            "citations": []
        }

    # Retrieve all documents owned by the logged-in user to enforce security boundary
    user_docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    if not user_docs:
        return {
            "answer": "I could not find sufficient information in the uploaded documents.",
            "citations": []
        }

    user_doc_ids = [doc.id for doc in user_docs]
    doc_id_to_name = {doc.id: doc.name for doc in user_docs}

    # Generate query embedding vector
    try:
        query_vector = embedding_service.get_embedding(question)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {str(e)}"
        )

    # Build Qdrant FieldCondition security filter matching user's documents
    qdrant_filter = qdrant_models.Filter(
        must=[
            qdrant_models.FieldCondition(
                key="document_id",
                match=qdrant_models.MatchAny(any=user_doc_ids)
            )
        ]
    )

    # Retrieve top 5 semantic chunks from Qdrant
    try:
        raw_hits = vector_store.search_similar_chunks(
            query_vector=query_vector,
            limit=5,
            query_filter=qdrant_filter
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}"
        )

    # Compile context list including document names for LLM grounding prompt
    context_chunks = []
    for hit in raw_hits:
        doc_id = hit["document_id"]
        context_chunks.append({
            "chunk_id": hit["chunk_id"],
            "document_id": doc_id,
            "document_name": doc_id_to_name.get(doc_id, "Unknown"),
            "page_number": hit["page_number"],
            "chunk_text": hit["chunk_text"],
            "score": hit["score"]
        })

    # Call LLM service to compile prompts, call Gemini, and format grounding outputs
    res = llm_service.generate_answer(question, context_chunks)

    # Format output citations conforming strictly to Citation schema
    citations = []
    for source in res["sources"]:
        citations.append(
            Citation(
                document_name=source["document_name"],
                page_number=source["page_number"],
                chunk_index=source["chunk_index"],
                chunk_text=source["chunk_text"]
            )
        )

    return {
        "answer": res["answer"],
        "citations": citations
    }
