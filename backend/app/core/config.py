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
    ALLOWED_ORIGINS: str = "http://localhost:3002,http://localhost:3000"


    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:5432/{self.POSTGRES_DB}"
        return self

    model_config = ConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()
