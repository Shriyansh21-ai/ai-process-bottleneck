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
from pydantic import BaseModel, Field
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.core.rate_limiter import limiter
from src.api.agent import router as agent_router
from src.api.auth import router as auth_router
from src.api.routes.analysis import router as analysis_router

from src.core.logging import setup_logging
from src.core.middleware.request_id import RequestIDMiddleware
from src.core.middleware.timing import TimingMiddleware
from src.core.middleware.body_size import BodySizeLimitMiddleware
from src.core.exceptions import (
    global_exception_handler,
    validation_exception_handler,
)
from src.config import (
    validate_config,
    get_cors_origins,
    cors_allow_credentials,
    get_run_rate_limit,
    is_production,
)
from src.core.auth import get_current_active_user
from src.db.models.user import User
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.genai.engine import GenAIEngine
from fastapi.middleware.cors import CORSMiddleware
from src.db.session import engine, SessionLocal
from src.agent.controller import AgentController
from src.db.base import Base
from fastapi import HTTPException, Depends
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
from src.api.routes.inspection import (
    router as inspection_router
)
from src.api.routes.chat import router as chat_router
from src.api.routes.stream_chat import (
    router as stream_chat_router
)
from src.db.init_qdrant import (
    init_qdrant
)
from src.api.routes.approval import (
    router as approval_router
)

from src.api.routes.agent_runs import (
    router as agent_runs_router
)

from src.api.routes.agent_observability import (
    router as agent_observability_router
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
init_qdrant()

app = FastAPI(title="Agentic Process Intelligence")

# CORS is environment-driven (see src.config.get_cors_origins). Defaults to a
# permissive "*" for local dev; set CORS_ALLOW_ORIGINS in production to lock it
# down. Credentials are only enabled when origins are explicitly allow-listed
# (a wildcard + credentials is unsafe and browser-invalid).
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=cors_allow_credentials(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# 👇 Now tables will be created
Base.metadata.create_all(bind=engine)

# Attach limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Auth dependency applied at router-inclusion time. These LLM/RAG/ingest/agent
# endpoints drive paid model calls, embeddings and file ingestion; leaving them
# open is a cost/resource-exhaustion (DoS) and data-exposure risk. The frontend
# dashboard uses none of them, so requiring a valid access token is a safe,
# backward-compatible hardening. /health and /auth stay public by design;
# /runs and /observability already enforce their own (owner/admin) auth.
_auth = [Depends(get_current_active_user)]

# Auth endpoints live at /auth/* (register, login, me).
app.include_router(auth_router)
app.include_router(analysis_router, prefix="/api", dependencies=_auth)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(BodySizeLimitMiddleware)

app.include_router(health_router)
app.include_router(generate_router, dependencies=_auth)
app.include_router(embeddings_router, dependencies=_auth)
app.include_router(documents_router, dependencies=_auth)
app.include_router(search_router, dependencies=_auth)
app.include_router(rag_router, dependencies=_auth)
app.include_router(ingest_router, dependencies=_auth)
# MRPL Phase 2: inspection document intelligence (upload -> extract -> RAG).
# Authenticated like the other ingest/RAG endpoints — it accepts confidential
# file uploads and can drive embeddings/ingestion.
app.include_router(inspection_router, dependencies=_auth)
app.include_router(chat_router, prefix="/chat", tags=["Chat"], dependencies=_auth)
app.include_router(stream_chat_router, dependencies=_auth)
app.include_router(
    approval_router,
    dependencies=_auth,
)
app.include_router(
    agent_runs_router
)
app.include_router(
    agent_observability_router
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Routes
app.include_router(agent_router, prefix="/api", dependencies=_auth)

class QueryRequest(BaseModel):
    # Bound the prompt so a single request cannot drive unbounded LLM token
    # cost / memory. 8k chars is generous for an agent task description.
    query: str = Field(..., min_length=1, max_length=8000)
    session_id: str = Field(..., min_length=1, max_length=200)

@app.post("/run")
@limiter.limit(get_run_rate_limit())
async def run_query(
    req: QueryRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    db = SessionLocal()
    logger = getattr(request.state, "logger", logging.getLogger("run"))
    try:
        # Do NOT log full query/result bodies at INFO — they can contain PII /
        # sensitive content. Metadata only at INFO; full body at DEBUG.
        logger.info(
            "run_query received",
            extra={"session_id": req.session_id, "query_len": len(req.query)},
        )

        # The authenticated user owns this run. Identity is injected at the API
        # boundary; the agent execution flow itself is unchanged.
        controller = AgentController(
            db=db,
            session_id=req.session_id,
            user_id=current_user.id,
        )

        result = await controller.run(
            user_query=req.query
        )

        logger.debug("run_query completed", extra={"session_id": req.session_id})

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

    except Exception:
        db.rollback()

        # Full detail is logged server-side only — never returned to clients.
        request_id = getattr(request.state, "request_id", None)
        logger = getattr(request.state, "logger", logging.getLogger("error"))
        logger.exception("run_query failed")

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "request_id": request_id,
            },
        )

    finally:
        db.close()

@app.post("/run-stream")
@limiter.limit(get_run_rate_limit())
async def run_stream(
    req: QueryRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
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

    except Exception:
        db.rollback()

        request_id = getattr(request.state, "request_id", None)
        logger = getattr(request.state, "logger", logging.getLogger("error"))
        logger.exception("run_stream failed")

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "request_id": request_id,
            },
        )

    finally:
        db.close()


# NOTE: /health and /health/ready are served by src.api.routes.health (included
# above). The previous inline /health handler was removed to avoid a duplicate.


@app.on_event("startup")
async def startup_event():

    logger = logging.getLogger("startup")
    logger.info("Backend starting")

    # Validate configuration early. In production a missing required key
    # (DATABASE_URL / JWT_SECRET_KEY) must HARD-FAIL startup so a misconfigured
    # instance never comes up "healthy" and serves broken/unauthenticated
    # traffic. In dev/staging we only warn so local iteration stays easy.
    validate_config(raise_on_error=is_production())

    # Create database tables. NOTE: production schema is managed by Alembic
    # (entrypoint runs `alembic upgrade head`); this create_all is a dev/test
    # convenience and a safety net.
    Base.metadata.create_all(bind=engine)

    logger.info("Database connected")

    # Preload embedding model
    get_embedding_model()

    logger.info("Embedding model loaded")

    # Verify Ollama connection
    ollama = OllamaClient()

    try:

        response = await ollama.generate("Hello")

        if response:
            logger.info("Ollama connected")

        else:
            logger.warning("Ollama not responding")

    except Exception as e:

        logger.warning("Ollama connection failed: %s", e)

    logger.info("Backend ready")