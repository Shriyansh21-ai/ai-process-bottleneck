import time
import traceback
from sqlalchemy.orm import Session
from models.genai_task_log import GenAITaskLog

def log_genai_task(db: Session, task: str, response: str = None, error: str = None, execution_time: float = None):
    record = GenAITaskLog(
        task=task,
        response=response,
        success=(error is None),
        error=error,
        execution_time_seconds=execution_time
    )
    db.add(record)
    db.commit()

def safe_run(db: Session, func, *args, **kwargs):
    start = time.time()
    try:
        result = func(*args, **kwargs)
        execution_time = time.time() - start
        log_genai_task(db, task=kwargs.get("task", "unknown"), response=result, execution_time=execution_time)
        return result
    except Exception as e:
        execution_time = time.time() - start
        error_msg = traceback.format_exc()
        log_genai_task(db, task=kwargs.get("task", "unknown"), error=error_msg, execution_time=execution_time)
        raise
