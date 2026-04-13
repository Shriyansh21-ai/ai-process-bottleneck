import time
import traceback
from sqlalchemy.orm import Session
from src.models.genai_task_log import GenAITaskLog


def log_genai_task(
    db: Session,
    task: str,
    response: str = None,
    error: str = None,
    execution_time: float = None
):
    try:
        record = GenAITaskLog(
            task=task,
            response=response,
            error=error,
            execution_time_seconds=execution_time
        )
        db.add(record)
        db.commit()

    except Exception:
        db.rollback()   # ✅ VERY IMPORTANT
        print("DB LOGGING ERROR:", traceback.format_exc())  # don’t crash app


def safe_run(db: Session, func, *args, **kwargs):
    start = time.time()
    try:
        result = func(*args, **kwargs)
        execution_time = time.time() - start

        log_genai_task(
            db,
            task=kwargs.get("task", "unknown"),
            response=str(result),   # ✅ ensure string
            execution_time=execution_time
        )

        return result

    except Exception:
        execution_time = time.time() - start
        error_msg = traceback.format_exc()

        log_genai_task(
            db,
            task=kwargs.get("task", "unknown"),
            error=error_msg,
            execution_time=execution_time
        )

        raise