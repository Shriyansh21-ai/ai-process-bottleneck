from sqlalchemy.orm import Session
from models.agent_job import AgentJob

def create_job(db: Session, query: str) -> AgentJob:
    job = AgentJob(query=query)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def update_job_status(db: Session, job_id: int, **kwargs):
    job = db.query(AgentJob).get(job_id)
    for k, v in kwargs.items():
        setattr(job, k, v)
    db.commit()
