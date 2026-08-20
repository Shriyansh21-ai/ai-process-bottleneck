import asyncio

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from src.db.session import SessionLocal
from src.models.genai_task_log import GenAITaskLog
from src.genai.jobs.manager import run_agent_job
from src.genai.sessions.session_manager import SessionManager
from fastapi.responses import StreamingResponse
from src.genai.services.llm_service import generate_response
import time

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_agent_sync(query: str, db):
    """
    Safe wrapper to call async engine synchronously
    """

    from genai.engine import GenAIEngine

    engine = GenAIEngine(db=db, session_id="stream-session")

    # Run async function safely
    result = asyncio.run(engine.run_task(query))

    # Extract final answer properly
    return result["answer"]




# 🚀 Submit Agent Job (Session-aware)
@router.post("/agent/job")
def submit_agent_job(
    task: str,
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    session_manager = SessionManager(db)
    session = session_manager.get_session(session_id)

    if not session:
        return {"error": "Invalid session"}

    job = GenAITaskLog(
        task=task,
        session_id=session_id,
        status="PENDING",
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # 🚀 Run job in background with session context
    background_tasks.add_task(
        run_agent_job,
        job.id,
        session_id,
    )

    return {
        "job_id": job.id,
        "session_id": session_id,
        "status": job.status,
    }


# 🔍 Get Job Status / Result
@router.get("/agent/job/{job_id}")
def get_agent_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(GenAITaskLog).filter(
        GenAITaskLog.id == job_id
    ).first()

    if not job:
        return {"error": "Job not found"}

    return {
        "job_id": job.id,
        "session_id": job.session_id,
        "task": job.task,
        "status": job.status,
        "response": job.response,
        "error": job.error,
        "execution_time_seconds": job.execution_time_seconds,
        "created_at": job.created_at,
    }

@router.post("/run-stream")
def run_stream(
    query: dict,
    db: Session = Depends(get_db)
):
    user_query = query.get("query")

    if not isinstance(user_query, str) or not user_query.strip():
        raise HTTPException(status_code=422, detail="'query' is required")
    if len(user_query) > 8000:
        raise HTTPException(status_code=422, detail="'query' is too long")

    # ✅ Use NEW function
    response_text = run_agent_sync(user_query, db)

    def stream_generator():
        for word in response_text.split():
            yield word + " "
            time.sleep(0.03)

    return StreamingResponse(
        stream_generator(),
        media_type="text/plain"
    )

@router.post("/chat")
async def chat(query: dict):

    user_message = query.get("message")

    if not isinstance(user_message, str) or not user_message.strip():
        raise HTTPException(status_code=422, detail="'message' is required")
    if len(user_message) > 8000:
        raise HTTPException(status_code=422, detail="'message' is too long")

    response = await generate_response(user_message)

    return {
        "response": response
    }

