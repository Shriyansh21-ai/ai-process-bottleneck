import asyncio
from sqlalchemy.orm import Session

from genai.engine import GenAIEngine
from genai.jobs.service import update_job_status

async def run_job(db: Session, job_id: int, query: str):
    engine = GenAIEngine(db)

    try:
        update_job_status(db, job_id, status="running")

        result = await engine.run_task(query)

        update_job_status(
            db,
            job_id,
            status="completed",
            result=result["answer"],
            metadata={
                "execution_time": result["execution_time_sec"],
                "agents_used": result["agents_used"],
            },
        )

    except Exception as e:
        update_job_status(
            db,
            job_id,
            status="failed",
            error=str(e),
        )
