from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.genai_task_log import GenAITaskLog
from genai.jobs.manager import run_agent_job
from genai.sessions.session_manager import SessionManager

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
