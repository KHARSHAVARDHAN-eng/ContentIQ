from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.search import SearchRequest, SearchResponse, SearchHit
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from qdrant_client.http import models as qdrant_models

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
def semantic_search(
    search_req: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = search_req.query.strip()
    if not query:
        return {"chunks": []}

    # Generate query embedding vector
    try:
        query_vector = embedding_service.get_embedding(query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {str(e)}"
        )

    # Enforce security filter: retrieve only documents owned by the logged-in user
    user_docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    if not user_docs:
        return {"chunks": []}

    user_doc_ids = [doc.id for doc in user_docs]
    doc_id_to_name = {doc.id: doc.name for doc in user_docs}

    # Build Qdrant FieldCondition security filter matching user's documents
    qdrant_filter = qdrant_models.Filter(
        must=[
            qdrant_models.FieldCondition(
                key="document_id",
                match=qdrant_models.MatchAny(any=user_doc_ids)
            )
        ]
    )

    # Search similar vectors in Qdrant
    try:
        raw_hits = vector_store.search_similar_chunks(
            query_vector=query_vector,
            limit=5,
            query_filter=qdrant_filter
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector similarity search failed: {str(e)}"
        )


    # Format output hits
    hits = []
    for hit in raw_hits:
        doc_id = hit["document_id"]
        hits.append(
            SearchHit(
                chunk_text=hit["chunk_text"],
                score=round(hit["score"], 4),
                page_number=hit["page_number"],
                document_id=doc_id,
                document_name=doc_id_to_name.get(doc_id, "Unknown Document")
            )
        )

    return {"chunks": hits}
