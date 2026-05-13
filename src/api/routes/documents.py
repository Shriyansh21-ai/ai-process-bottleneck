from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models.document import Document

from src.genai.embeddings import embed_text


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


@router.post("/")
def create_document(
    content: str,
    db: Session = Depends(get_db)
):

    embedding = embed_text(content)

    document = Document(
        content=content,
        embedding=str(embedding)
    )

    db.add(document)

    db.commit()

    db.refresh(document)

    return {
        "message": "Document stored successfully",
        "document_id": document.id
    }