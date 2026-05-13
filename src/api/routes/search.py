from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models.document import Document

from src.genai.embeddings import embed_text


router = APIRouter(
    prefix="/search",
    tags=["Search"]
)


@router.get("/")
def search_documents(
    query: str,
    db: Session = Depends(get_db)
):

    query_embedding = embed_text(query)

    documents = db.query(Document).all()

    results = []

    for doc in documents:

        results.append({
            "id": doc.id,
            "content": doc.content
        })

    return {
        "query": query,
        "results": results
    }