import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

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

# 🔥 ADD THIS LINE (VERY IMPORTANT)
import src.models

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
async def load_models():
    print("🚀 Preloading embedding model...")
    get_embedding_model()