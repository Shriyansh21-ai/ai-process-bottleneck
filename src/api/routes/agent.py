from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.session import SessionLocal
from genai.agent_runner import AgentRunner

router = APIRouter(prefix="/agent", tags=["Agent"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/run")
async def run_agent(task: str, db: Session = Depends(get_db)):
    runner = AgentRunner(db)
    response = await runner.run(task)
    return response
