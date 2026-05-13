from sqlalchemy.orm import Session

from src.models.document_chunk import (
    DocumentChunk
)


def retrieve_context(
    db: Session,
    query: str,
    limit: int = 5
):

    # ==========================================
    # SIMPLE KEYWORD MATCH
    # ==========================================

    results = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.content.ilike(
                f"%{query}%"
            )
        )
        .limit(limit)
        .all()
    )

    # ==========================================
    # FALLBACK TO RECENT CHUNKS
    # ==========================================

    if not results:

        results = (
            db.query(DocumentChunk)
            .limit(limit)
            .all()
        )

    return [

        {
            "content": r.content,
            "section": r.section,
            "page_number": r.page_number
        }

        for r in results
    ]