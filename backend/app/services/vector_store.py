import os
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.core.config import settings

class VectorStoreService:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            # Determine connection mode based on settings
            if settings.QDRANT_HOST:
                print(f"Connecting to Qdrant server at http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}...")
                self._client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            elif settings.QDRANT_PATH:
                # Resolve relative paths relative to current backend workspace
                resolved_path = os.path.abspath(settings.QDRANT_PATH)
                os.makedirs(resolved_path, exist_ok=True)
                print(f"Initializing Qdrant local client with storage path: {resolved_path}...")
                self._client = QdrantClient(path=resolved_path)
            else:
                print("Initializing Qdrant client in-memory fallback...")
                self._client = QdrantClient(":memory:")
        return self._client


    def create_collection(self, collection_name: str = "document_chunks", vector_size: int = 384):
        try:
            self.client.get_collection(collection_name)
            print(f"Qdrant: Collection '{collection_name}' already exists.")
        except Exception:
            print(f"Qdrant: Creating collection '{collection_name}' with vector size {vector_size}...")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE
                )
            )
            print(f"Qdrant: Collection '{collection_name}' created successfully.")

    def upsert_chunk(
        self,
        chunk_id: int,
        document_id: int,
        page_number: int,
        chunk_text: str,
        vector: List[float],
        collection_name: str = "document_chunks"
    ):
        print(f"Qdrant: Upserting chunk {chunk_id} for document {document_id}...")
        self.client.upsert(
            collection_name=collection_name,
            points=[
                qdrant_models.PointStruct(
                    id=chunk_id,
                    vector=vector,
                    payload={
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "page_number": page_number,
                        "chunk_text": chunk_text
                    }
                )
            ]
        )

    def upsert_chunks_bulk(
        self,
        points_data: List[Dict[str, Any]],
        collection_name: str = "document_chunks"
    ):
        """
        Upsert multiple chunk points in a single request for high performance.
        Each item in points_data should have keys: chunk_id, document_id, page_number, chunk_text, vector.
        """
        if not points_data:
            return
            
        print(f"Qdrant: Bulk upserting {len(points_data)} chunks to collection '{collection_name}'...")
        points = []
        for item in points_data:
            points.append(
                qdrant_models.PointStruct(
                    id=item["chunk_id"],
                    vector=item["vector"],
                    payload={
                        "chunk_id": item["chunk_id"],
                        "document_id": item["document_id"],
                        "page_number": item["page_number"],
                        "chunk_text": item["chunk_text"]
                    }
                )
            )
            
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )

    def delete_document_vectors(self, document_id: int, collection_name: str = "document_chunks"):
        print(f"Qdrant: Deleting vectors for document {document_id} from collection '{collection_name}'...")
        self.client.delete(
            collection_name=collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="document_id",
                            match=qdrant_models.MatchValue(value=document_id)
                        )
                    ]
                )
            )
        )

    def search_similar_chunks(
        self,
        query_vector: List[float],
        limit: int = 5,
        query_filter: Any = None,
        collection_name: str = "document_chunks"
    ) -> List[Dict[str, Any]]:
        print(f"Qdrant: Searching top {limit} matches in collection '{collection_name}' with filter: {query_filter}...")
        response = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit
        )
        
        hits = []
        for hit in response.points:
            hits.append({
                "chunk_id": hit.payload.get("chunk_id"),
                "document_id": hit.payload.get("document_id"),
                "page_number": hit.payload.get("page_number"),
                "chunk_text": hit.payload.get("chunk_text"),
                "score": hit.score
            })
        return hits

vector_store = VectorStoreService()
