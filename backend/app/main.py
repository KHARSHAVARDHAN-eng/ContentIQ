import time
import json
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, users, documents, search, chat, evaluations, conversations, study_tools, graph
from app.models.user import User

from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.document_chunk import DocumentChunk
from app.models.chunk_embedding import ChunkEmbedding
from app.models.rag_evaluation import RAGEvaluation
from app.models.chat_history import ChatSession, ChatMessage
from app.models.study_tool import FlashCardDeck, FlashCard, StudyPack

# Automatically create database tables (useful for fast setup, Docker run, local testing)
try:
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE documents ADD COLUMN ocr_confidence FLOAT"))
            conn.commit()
            print("Added column ocr_confidence to documents table")
        except Exception as e:
            print(f"Documents alter column status: {e}")
        try:
            conn.execute(text("ALTER TABLE document_pages ADD COLUMN ocr_confidence FLOAT"))
            conn.commit()
            print("Added column ocr_confidence to document_pages table")
        except Exception as e:
            print(f"Document_pages alter column status: {e}")
            
        for col, col_type in [("chunk_size", "INTEGER"), ("chunk_overlap", "INTEGER"), ("chunk_strategy", "VARCHAR"), ("document_type", "VARCHAR"), ("chunk_reason", "VARCHAR")]:
            try:
                conn.execute(text(f"ALTER TABLE documents ADD COLUMN {col} {col_type}"))
                conn.commit()
                print(f"Added column {col} to documents table")
            except Exception as e:
                pass
except Exception as e:
    print(f"Error creating database tables: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if "*" in origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True if "*" not in origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def evaluation_logging_middleware(request: Request, call_next):
    # Log only POST requests to /api/chat
    if request.url.path == f"{settings.API_V1_STR}/chat" and request.method == "POST":
        start_time = time.time()
        
        # Read request body
        req_body_bytes = await request.body()
        async def receive():
            return {"type": "http.request", "body": req_body_bytes}
        request._receive = receive
        
        # Determine User ID from Token
        auth_header = request.headers.get("Authorization")
        user_id = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                import jwt
                from app.core.config import settings as app_settings
                from app.core.security import ALGORITHM
                payload = jwt.decode(token, app_settings.SECRET_KEY, algorithms=[ALGORITHM])
                user_id = int(payload.get("sub"))
            except Exception:
                pass
                
        # Handle session creation/validation before request runs
        session_id = None
        if user_id:
            try:
                req_json = json.loads(req_body_bytes.decode('utf-8'))
                raw_sess = req_json.get("session_id") or request.headers.get("X-Session-ID")
                from app.core.database import SessionLocal
                from app.models.chat_history import ChatSession
                db = SessionLocal()
                try:
                    if raw_sess:
                        sess = db.query(ChatSession).filter(
                            ChatSession.id == int(raw_sess),
                            ChatSession.user_id == user_id
                        ).first()
                        if sess:
                            session_id = sess.id
                    
                    if not session_id:
                        # Create new session based on question
                        q_text = req_json.get("question", "").strip()
                        title = q_text[:35] + "..." if len(q_text) > 35 else (q_text or "New Conversation")
                        sess = ChatSession(user_id=user_id, title=title)
                        db.add(sess)
                        db.commit()
                        db.refresh(sess)
                        session_id = sess.id
                finally:
                    db.close()
            except Exception as e:
                print(f"Error preparing chat session: {e}")
        
        response = await call_next(request)
        
        try:
            latency_ms = int((time.time() - start_time) * 1000)
            
            resp_body_bytes = b""
            async for chunk in response.body_iterator:
                resp_body_bytes += chunk
                
            resp_headers = dict(response.headers)
            resp_headers.pop("content-length", None)
            
            new_response = Response(
                content=resp_body_bytes,
                status_code=response.status_code,
                headers=resp_headers,
                media_type=response.media_type
            )
            
            if response.status_code == 200:
                req_json = json.loads(req_body_bytes.decode('utf-8'))
                resp_json = json.loads(resp_body_bytes.decode('utf-8'))
                
                if user_id and session_id:
                    from app.core.database import SessionLocal
                    from app.models.chat_history import ChatMessage
                    db = SessionLocal()
                    try:
                        # Log message history (User)
                        user_msg = ChatMessage(
                            session_id=session_id,
                            sender="user",
                            text=req_json.get("question", "")
                        )
                        db.add(user_msg)
                        
                        # Log message history (Bot)
                        citations_str = json.dumps(resp_json.get("citations", []))
                        bot_msg = ChatMessage(
                            session_id=session_id,
                            sender="bot",
                            text=resp_json.get("answer", ""),
                            citations=citations_str
                        )
                        db.add(bot_msg)
                        db.commit()
                    except Exception as history_err:
                        print(f"Failed to persist history: {history_err}")
                    finally:
                        db.close()
                
                if user_id:
                    # Log evaluation
                    from app.services.eval_service import eval_service
                    eval_id = eval_service.log_chat_event(
                        user_id=user_id,
                        query=req_json.get("question", ""),
                        answer=resp_json.get("answer", ""),
                        latency_ms=latency_ms,
                        citations=resp_json.get("citations", [])
                    )
                    
                    # Inject variables
                    modified = False
                    if eval_id:
                        resp_json["evaluation_id"] = eval_id
                        modified = True
                    if session_id:
                        resp_json["session_id"] = session_id
                        modified = True
                        
                    if modified:
                        resp_body_bytes = json.dumps(resp_json).encode('utf-8')
                        new_response = Response(
                            content=resp_body_bytes,
                            status_code=response.status_code,
                            headers=resp_headers,
                            media_type=response.media_type
                        )
            return new_response
        except Exception as e:
            print(f"Error logging chat evaluation: {e}")
            return response
            
    return await call_next(request)

# Register routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["documents"])
app.include_router(search.router, prefix=f"{settings.API_V1_STR}", tags=["search"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}", tags=["chat"])
app.include_router(evaluations.router, prefix=f"{settings.API_V1_STR}/evaluations", tags=["evaluations"])
app.include_router(conversations.router, prefix=f"{settings.API_V1_STR}/conversations", tags=["conversations"])
app.include_router(study_tools.router, prefix=f"{settings.API_V1_STR}/study-tools", tags=["study-tools"])
app.include_router(graph.router, prefix=f"{settings.API_V1_STR}/graph", tags=["graph"])

@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}
