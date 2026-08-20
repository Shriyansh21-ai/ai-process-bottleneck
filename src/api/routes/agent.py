import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.db.session import SessionLocal
from src.genai.agent_runner import AgentRunner

logger = logging.getLogger("agent")


# ✅ Request schema
class RunRequest(BaseModel):
    # Bound the prompt length so a single request cannot drive unbounded LLM
    # token cost / memory usage.
    query: str = Field(..., min_length=1, max_length=8000)
    session_id: str = Field(..., min_length=1, max_length=200)

# ✅ Router
router = APIRouter(prefix="/agent", tags=["Agent"])

# ✅ DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Main Run Endpoint
@router.post("/run")
async def run_agent(request: RunRequest, db: Session = Depends(get_db)):
    try:
        runner = AgentRunner(db)

        response = await runner.run(
            request.query,
            request.session_id
        )

        return {
            "status": "success",
            "data": response
        }

    except Exception:
        # Log full detail server-side only; never return tracebacks or raw
        # exception strings to the client (they can leak internal paths,
        # connection details, etc.).
        logger.exception("agent /run failed")

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "Internal server error",
            },
        )