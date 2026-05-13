import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

from src.genai.offline.ollama_client import OllamaClient

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")



from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.core.rate_limiter import limiter
from src.api.agent import router as agent_router
from src.api.auth import router as auth_router
from src.api.routes.analysis import router as analysis_router

from src.core.logging import setup_logging
from src.core.middleware.request_id import RequestIDMiddleware
from src.core.middleware.timing import TimingMiddleware
from src.core.exceptions import global_exception_handler

from src.genai.engine import GenAIEngine
from fastapi.middleware.cors import CORSMiddleware
from src.db.session import engine, SessionLocal
from src.db.base import Base
from fastapi import HTTPException
from datetime import datetime
from src.models.audit_log import AuditLog
from src.genai.model_loader import get_embedding_model
from src.api.routes.health import router as health_router
from src.api.routes.generate import router as generate_router
from src.api.routes.embeddings import router as embeddings_router
from src.api.routes.documents import router as documents_router
from src.api.routes.search import router as search_router
from src.api.routes.rag import router as rag_router
from src.api.routes.ingest import router as ingest_router
from src.api.routes.chat import router as chat_router
from src.api.routes.stream_chat import (
    router as stream_chat_router
)

from src.db.models.document import Document

# 🔥 ADD THIS LINE (VERY IMPORTANT)
import src.models
import logging

logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

setup_logging()

app = FastAPI(title="Agentic Process Intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 👇 Now tables will be created
Base.metadata.create_all(bind=engine)

# Attach limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")

app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)

app.include_router(health_router)
app.include_router(generate_router)
app.include_router(embeddings_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(rag_router)
app.include_router(ingest_router)
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(stream_chat_router)

app.add_exception_handler(Exception, global_exception_handler)

# Routes
app.include_router(agent_router, prefix="/api")

class QueryRequest(BaseModel):
    query: str
    session_id: str

@app.post("/run")
async def run_query(req: QueryRequest):
    db = SessionLocal()
    try:
        print(f" Incoming Query: {req.query}")
        print(f" Session ID: {req.session_id}")

        engine = GenAIEngine(db=db, session_id=req.session_id)
        result = await engine.run_task(req.query)

        print(f" Result: {result}")

        # ✅ Ensure response is JSON serializable
        safe_result = result
        try:
            json.dumps(result)
        except Exception:
            safe_result = str(result)

        # ✅ Audit logging
        log = AuditLog(
            actor_id=req.session_id,
            actor_type="user",
            action="run_query",
            resource="genai",
            details={
                "query": req.query,
                "response": safe_result
            }
        )

        db.add(log)
        db.commit()

        return result

    except Exception as e:
        db.rollback()

        # 🔥 PRINT FULL ERROR (VERY IMPORTANT)
        print("❌ ERROR OCCURRED:")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Internal Error: {str(e)}"
        )

    finally:
        db.close()

@app.post("/run-stream")
async def run_stream(req: QueryRequest):
    db = SessionLocal()
    try:
        engine = GenAIEngine(db=db, session_id=req.session_id)
        result = await engine.run_task(req.query)

        # ✅ Audit log (store final result)
        log = AuditLog(
            actor_id=req.session_id,
            actor_type="user",
            action="run_stream",
            resource="genai",
            details={
                "query": req.query,
                "response": result
            }
        )
        db.add(log)
        db.commit()

        async def stream_generator():
            for chunk in result["answer"].split():
                yield chunk + " "
                await asyncio.sleep(0.03)

        return StreamingResponse(stream_generator(), media_type="text/plain")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()

@app.get("/health")
async def health():

    return {
        "status": "healthy"
    }

@app.on_event("startup")
async def startup_event():

    print("🚀 Backend starting...")

    # Create database tables
    Base.metadata.create_all(bind=engine)

    print("✅ Database connected")

    # Preload embedding model
    get_embedding_model()

    print("✅ Embedding model loaded")

    # Verify Ollama connection
    ollama = OllamaClient()

    try:

        response = await ollama.generate("Hello")

        if response:
            print("✅ Ollama connected")

        else:
            print("❌ Ollama not responding")

    except Exception as e:

        print(f"❌ Ollama connection failed: {e}")

    print("🚀 Backend ready")