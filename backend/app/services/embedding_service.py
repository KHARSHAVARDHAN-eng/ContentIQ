# ==========================================
# PRODUCTION LOCKED - STABLE RAG V1 CORE
# DO NOT MODIFY without explicit regression verification
# ==========================================

from sentence_transformers import SentenceTransformer
from app.core.config import settings
from typing import List

class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            print(f"Initializing Embedding Model: {settings.EMBEDDING_MODEL_NAME}...")
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            print("Embedding Model Loaded Successfully.")
        return cls._model

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self.get_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def get_embedding(self, text: str) -> List[float]:
        model = self.get_model()
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()

embedding_service = EmbeddingService()
