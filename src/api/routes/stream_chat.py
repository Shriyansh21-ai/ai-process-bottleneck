from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session

from src.db.session import SessionLocal

from src.services.stream_service import (
    stream_rag_response
)

router = APIRouter(
    prefix="/stream-chat",
    tags=["Streaming Chat"]
)


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


@router.post("/")
async def stream_chat(
    data: dict,
    db: Session = Depends(get_db)
):

    query = data.get("query")

    async def generator():

        async for token in stream_rag_response(
            db=db,
            query=query
        ):

            yield token

    return StreamingResponse(
        generator(),
        media_type="text/plain"
    )