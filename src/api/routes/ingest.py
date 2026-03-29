from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def ingest_data(data: dict, db: Session = Depends(get_db)):
    """
    Example Ingest endpoint
    Replace with logic to ingest new data/resources/tasks
    """
    # Placeholder
    return {"status": "success", "message": "Data ingested successfully"}
