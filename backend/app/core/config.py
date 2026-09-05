from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator
from typing import Any

class Settings(BaseSettings):
    PROJECT_NAME: str = "DocumentIQ"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "supersecretjwtkeychangeinproduction123456789"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Chunking
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    
    # Embeddings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    
    # Qdrant
    QDRANT_URL: str | None = None
    QDRANT_HOST: str | None = None
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None
    QDRANT_PATH: str | None = "./qdrant_data"
    
    # Gemini
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    QUERY_ANALYZER_MODEL: str = "gemini-1.5-flash"
    QUERY_ANALYZER_TEMPERATURE: float = 0.0
    QUERY_ANALYZER_FALLBACK_INTENT_CONF: float = 0.85
    QUERY_ANALYZER_FALLBACK_COMPLEXITY_CONF: float = 0.80
    QUERY_REWRITER_ENABLED: bool = True
    QUERY_REWRITER_TYPE: str = "hybrid"
    QUERY_REWRITER_MODEL: str = "gemini-1.5-flash"
    QUERY_REWRITER_TEMPERATURE: float = 0.0
    ADAPTIVE_RETRIEVAL_ENABLED: bool = True
    ADAPTIVE_RETRIEVAL_POLICY_TYPE: str = "rules"
    ADAPTIVE_RETRIEVAL_DEFAULT_TOP_K: int = 5
    ADAPTIVE_RETRIEVAL_SIMPLE_FACTUAL_TOP_K: int = 3
    ADAPTIVE_RETRIEVAL_MEDIUM_EXPLANATION_TOP_K: int = 5
    ADAPTIVE_RETRIEVAL_COMPLEX_ANALYTICAL_TOP_K: int = 10
    ADAPTIVE_RETRIEVAL_LARGE_COMPARISON_TOP_K: int = 12
    RETRIEVAL_VERIFIER_ENABLED: bool = True
    RETRIEVAL_VERIFIER_TYPE: str = "rules"
    RETRIEVAL_VERIFIER_MIN_PASS_SCORE: float = 0.35
    RETRIEVAL_VERIFIER_MIN_WARNING_SCORE: float = 0.20
    RETRIEVAL_VERIFIER_RETRY_STRATEGY: str = "expand_limit"
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-2-v2"
    RERANK_TOP_K: int = 5
    RERANK_BATCH_SIZE: int = 16
    RERANK_SCORE_THRESHOLD: float = 0.02
    RERANK_DEBUG_LOGGING: bool = True
    
    # Query Transformation Settings
    QUERY_TRANSFORMATION_ENABLED: bool = True
    QUERY_REWRITE_ENABLED: bool = True
    QUERY_EXPANSION_ENABLED: bool = True
    MULTI_QUERY_ENABLED: bool = True
    MAX_GENERATED_QUERIES: int = 3
    AMBIGUITY_THRESHOLD: float = 0.5
    QUERY_TRANSFORMATION_DEBUG: bool = True
    ADAPTIVE_CHUNKING_ENABLED: bool = True
    ADAPTIVE_CHUNKING_STRATEGY: str = "rules"
    ADAPTIVE_CHUNKING_RESEARCH_PAPER_SIZE: int = 300
    ADAPTIVE_CHUNKING_RESEARCH_PAPER_OVERLAP: int = 50
    ADAPTIVE_CHUNKING_TECHNICAL_DOC_SIZE: int = 600
    ADAPTIVE_CHUNKING_TECHNICAL_DOC_OVERLAP: int = 100
    ADAPTIVE_CHUNKING_USER_MANUAL_SIZE: int = 1000
    ADAPTIVE_CHUNKING_USER_MANUAL_OVERLAP: int = 150
    ADAPTIVE_CHUNKING_SLIDES_SIZE: int = 400
    ADAPTIVE_CHUNKING_SLIDES_OVERLAP: int = 0
    ADAPTIVE_CHUNKING_DEFAULT_SIZE: int = 500
    ADAPTIVE_CHUNKING_DEFAULT_OVERLAP: int = 50
    HALLUCINATION_DETECTOR_ENABLED: bool = True
    HALLUCINATION_DETECTOR_TYPE: str = "rules"
    HALLUCINATION_DETECTOR_THRESHOLD: float = 0.70
    HALLUCINATION_DETECTOR_MODEL: str = "gemini-1.5-flash"
    HALLUCINATION_DETECTOR_TEMPERATURE: float = 0.0
    HYBRID_RETRIEVAL_ENABLED: bool = True
    BM25_ENABLED: bool = True
    DENSE_RETRIEVAL_WEIGHT: float = 0.5
    BM25_WEIGHT: float = 0.5
    HYBRID_TOP_K: int = 5
    HYBRID_DEBUG_LOGGING: bool = True
    
    # Context Compression Settings
    CONTEXT_COMPRESSION_ENABLED: bool = True
    EVIDENCE_SELECTION_ENABLED: bool = True
    MAX_CONTEXT_TOKENS: int = 2048
    MAX_CONTEXT_CHUNKS: int = 10
    REDUNDANCY_THRESHOLD: float = 0.85
    SENTENCE_SIMILARITY_THRESHOLD: float = 0.85
    LOW_INFORMATION_THRESHOLD: int = 15
    PRESERVE_CITATIONS: bool = True
    CONTEXT_COMPRESSION_DEBUG: bool = True
    
    # Answer Verification Settings
    ANSWER_VERIFICATION_ENABLED: bool = True
    CLAIM_EXTRACTION_ENABLED: bool = True
    MIN_VERIFICATION_SCORE: float = 0.70
    VERIFICATION_CONFIDENCE_THRESHOLD: float = 0.80
    MAX_CLAIMS_PER_RESPONSE: int = 8
    ANSWER_VERIFICATION_DEBUG: bool = True
    
    # Self-Reflection Settings
    SELF_REFLECTION_ENABLED: bool = True
    SELF_REFLECTION_MODE: str = "analysis"
    ENABLE_ANSWER_REFINEMENT: bool = True
    MAX_REFLECTION_ITERATIONS: int = 1
    REFLECTION_SCORE_THRESHOLD: float = 0.80
    REFLECTION_DEBUG: bool = True
    
    # Confidence Scoring Settings
    CONFIDENCE_SCORING_ENABLED: bool = True
    CONFIDENCE_HIGH_THRESHOLD: float = 80.0
    CONFIDENCE_MEDIUM_THRESHOLD: float = 50.0
    CONFIDENCE_LOW_THRESHOLD: float = 50.0
    CONFIDENCE_DEBUG: bool = True
    CONFIDENCE_WEIGHT_RETRIEVAL: float = 0.15
    CONFIDENCE_WEIGHT_RERANKING: float = 0.15
    CONFIDENCE_WEIGHT_VERIFICATION: float = 0.20
    CONFIDENCE_WEIGHT_HALLUCINATION: float = 0.20
    CONFIDENCE_WEIGHT_REFLECTION: float = 0.15
    CONFIDENCE_WEIGHT_CITATIONS: float = 0.15
    
    # RAG Evaluation Settings
    EVALUATION_ENABLED: bool = True
    AUTO_EVALUATE_RESPONSES: bool = True
    BENCHMARK_DATASET_ENABLED: bool = True
    SAVE_EVALUATION_RESULTS: bool = False
    MIN_ACCEPTABLE_SCORE: float = 0.70
    EVALUATION_DEBUG: bool = True
    EVAL_WEIGHT_FAITHFULNESS: float = 0.25
    EVAL_WEIGHT_RELEVANCY: float = 0.20
    EVAL_WEIGHT_CONTEXT_PRECISION: float = 0.15
    EVAL_WEIGHT_CONTEXT_RECALL: float = 0.15
    EVAL_WEIGHT_CITATION_COVERAGE: float = 0.15
    EVAL_WEIGHT_VERIFICATION_SUCCESS: float = 0.10
    
    # Agentic RAG Settings
    AGENTIC_RAG_ENABLED: bool = False
    AGENTIC_MAX_REASONING_STEPS: int = 3
    AGENTIC_MAX_RETRIEVAL_ATTEMPTS: int = 3
    AGENTIC_EVALUATION_THRESHOLD: float = 0.75
    AGENTIC_DEBUG: bool = True
    
    # GraphRAG Settings
    GRAPHRAG_ENABLED: bool = True
    GRAPHRAG_STORAGE_PATH: str = "graph_store.json"
    GRAPHRAG_EXTRACTION_LIMIT: int = 15
    GRAPHRAG_CONFIDENCE_THRESHOLD: float = 0.50
    GRAPHRAG_TRAVERSAL_DEPTH: int = 2
    GRAPHRAG_HYBRID_WEIGHT: float = 0.30
    GRAPHRAG_MAX_RETRIEVED_CHUNKS: int = 10

    
    # DB configs
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "documentiq"
    DATABASE_URL: str | None = None

    # Storage settings
    STORAGE_TYPE: str = "local" # "local" or "s3"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_S3_ENDPOINT_URL: str | None = None
    AWS_S3_BUCKET_NAME: str | None = None
    AWS_REGION_NAME: str = "us-east-1"

    # CORS configurations
    ALLOWED_ORIGINS: str = "http://localhost:3002,http://localhost:3000,http://localhost:3003,http://localhost:3004,http://127.0.0.1:3002,http://127.0.0.1:3003"


    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:5432/{self.POSTGRES_DB}"
        
        # Sanitize GEMINI_API_KEY to prevent invalid network calls when not set properly
        key = self.GEMINI_API_KEY
        if key:
            if key == "test_key" or key.strip() == "":
                self.GEMINI_API_KEY = None
            elif not key.startswith("AIzaSy") and not key.startswith("dummy"):
                self.GEMINI_API_KEY = None
        return self

    model_config = ConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()
