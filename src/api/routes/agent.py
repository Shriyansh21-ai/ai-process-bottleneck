from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.db.session import SessionLocal
from src.genai.agent_runner import AgentRunner

# ✅ Request schema
class RunRequest(BaseModel):
    query: str
    session_id: str

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

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        print("🔥 ERROR TRACEBACK:\n", error_details)

        return {
            "status": "error",
            "error": str(e),
            "traceback": error_details
        }