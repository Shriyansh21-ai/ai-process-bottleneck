from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import SessionLocal
from src.services.ai_service import generate_rag_response

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
async def chat(data: dict, db: Session = Depends(get_db)):

    query = data.get("query")

    result = await generate_rag_response(
        db=db,
        query=query
    )

    return result