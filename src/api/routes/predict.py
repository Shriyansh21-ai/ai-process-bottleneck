from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import SessionLocal
from src.models.process import Process

router = APIRouter()

# Dependency: get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def run_prediction(input_data: dict, db: Session = Depends(get_db)):
    """
    Run prediction logic.
    input_data: dict containing input features
    """
    # Example: store a dummy process (replace with your real logic)
    new_process = Process(process_code=input_data.get("process_code", "dummy"))
    db.add(new_process)
    db.commit()
    db.refresh(new_process)
    return {"status": "success", "process_id": new_process.id}
