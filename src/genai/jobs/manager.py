import time
from db.session import SessionLocal
from genai.engine import GenAIEngine
from models.genai_task_log import GenAITaskLog


def run_agent_job(job_id: int, session_id: str):
    db = SessionLocal()
    start_time = time.time()

    try:
        job = db.query(GenAITaskLog).get(job_id)
        engine = GenAIEngine(db, session_id=session_id)

        result = engine.run_task(job.task)

        job.response = str(result)
        job.status = "COMPLETED"
        job.execution_time_seconds = int(time.time() - start_time)

    except Exception as e:
        job.status = "FAILED"
        job.error = str(e)

    finally:
        db.commit()
        db.close()
