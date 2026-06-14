import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path so app modules are importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base
from app.core.config import settings

# Import all models to ensure metadata registration
from app.models.user import User
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.document_chunk import DocumentChunk
from app.models.chunk_embedding import ChunkEmbedding
from app.models.study_tool import FlashCardDeck, FlashCard, StudyPack
from app.models.chat_history import ChatSession, ChatMessage
from app.models.rag_evaluation import RAGEvaluation

def migrate(sqlite_url: str, postgres_url: str):
    print("Initializing migration...")
    print(f"Source SQLite: {sqlite_url}")
    print(f"Target PostgreSQL: {postgres_url}")
    
    # Fix dialect in postgres connection string if needed
    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)
        
    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(postgres_url)
    
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)
    
    sqlite_db = SqliteSession()
    postgres_db = PostgresSession()
    
    try:
        # Create all tables on PostgreSQL target
        print("Creating tables on PostgreSQL if they do not exist...")
        Base.metadata.create_all(bind=postgres_engine)
        
        # Order of tables to migrate (dependency order)
        tables = [
            User,
            Document,
            DocumentPage,
            DocumentChunk,
            ChunkEmbedding,
            FlashCardDeck,
            FlashCard,
            StudyPack,
            ChatSession,
            ChatMessage,
            RAGEvaluation
        ]
        
        for model in tables:
            print(f"Migrating {model.__name__}...")
            sqlite_rows = sqlite_db.query(model).all()
            print(f"Found {len(sqlite_rows)} records in SQLite.")
            
            count = 0
            for row in sqlite_rows:
                # Extract dictionary of values from sqlite object
                data = {c.name: getattr(row, c.name) for c in model.__table__.columns}
                new_row = model(**data)
                
                try:
                    postgres_db.merge(new_row)
                    count += 1
                except Exception as row_err:
                    print(f"Failed to merge row {data.get('id')} for {model.__name__}: {row_err}")
            
            postgres_db.commit()
            print(f"Successfully migrated {count}/{len(sqlite_rows)} records for {model.__name__}.")
            
        # ----------------------------------------------------
        # S3 / QDRANT RE-INDEX MIGRATION
        # ----------------------------------------------------
        # Check if STORAGE_TYPE is s3. If so, we migrate files to S3
        is_s3 = settings.STORAGE_TYPE.lower() == "s3"
        postgres_docs = postgres_db.query(Document).all()
        
        if is_s3:
            print("\nProduction STORAGE_TYPE=s3 configured. Syncing local files to S3 bucket...")
            from app.services.storage_service import storage_service
            
            for doc in postgres_docs:
                if not doc.path:
                    continue
                if doc.path.startswith("http://") or doc.path.startswith("https://"):
                    print(f"Document #{doc.id} ('{doc.name}') already has a remote path: {doc.path}. Skipping upload.")
                    continue
                
                filename = os.path.basename(doc.path)
                # Find local path
                local_path = doc.path
                if not os.path.exists(local_path):
                    # Look in backend/uploads/ relative to the script location
                    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
                    alt_path = os.path.join(uploads_dir, filename)
                    if os.path.exists(alt_path):
                        local_path = alt_path
                    else:
                        print(f"WARNING: Local file not found for document #{doc.id} ('{doc.name}') at {doc.path} or {alt_path}.")
                        continue
                
                print(f"Uploading '{filename}' to production S3 storage...")
                try:
                    with open(local_path, "rb") as f:
                        file_bytes = f.read()
                    
                    ext = os.path.splitext(filename)[1].lower()
                    content_type = "application/pdf"
                    if ext == ".docx":
                        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    elif ext == ".txt":
                        content_type = "text/plain"
                    elif ext in [".jpg", ".jpeg"]:
                        content_type = "image/jpeg"
                    elif ext == ".png":
                        content_type = "image/png"
                        
                    remote_url = storage_service.upload_file(file_bytes, filename, content_type)
                    print(f"Uploaded successfully. URL: {remote_url}")
                    
                    # Update database entry
                    doc.path = remote_url
                except Exception as upload_err:
                    print(f"ERROR: S3 upload failed for '{filename}': {upload_err}")
            
            postgres_db.commit()
            
        print("\nRe-indexing documents in production Qdrant vector database...")
        from app.services.document_processor import process_document_task
        
        for doc in postgres_docs:
            print(f"Re-indexing Document #{doc.id} ('{doc.name}')...")
            try:
                process_document_task(doc.id)
                print(f"Successfully re-indexed Document #{doc.id}.")
            except Exception as task_err:
                print(f"ERROR: Failed to re-index Document #{doc.id}: {task_err}")
                
        print("\nDatabase migration and vector re-indexing finished successfully!")
        
    except Exception as e:
        postgres_db.rollback()
        print(f"\nMigration failed: {e}")
        raise e
    finally:
        sqlite_db.close()
        postgres_db.close()

if __name__ == "__main__":
    sqlite_default = "sqlite:///./documentiq.db"
    
    # Use database URL from settings if it's a PostgreSQL URL
    postgres_default = settings.DATABASE_URL if settings.DATABASE_URL and "sqlite" not in settings.DATABASE_URL else ""
    
    # Allow overriding from CLI arguments
    sqlite_arg = sys.argv[1] if len(sys.argv) > 1 else sqlite_default
    postgres_arg = sys.argv[2] if len(sys.argv) > 2 else postgres_default
    
    if not postgres_arg:
        print("ERROR: Target PostgreSQL connection string not provided.")
        print("Usage: python migrate_db.py [sqlite_url] [postgres_url]")
        print("Or set DATABASE_URL environment variable to your PostgreSQL target.")
        sys.exit(1)
        
    migrate(sqlite_arg, postgres_arg)
