from sqlalchemy.orm import Session
from sqlalchemy import text
from rag.embeddings import embed_text

def retrieve_context(
    db: Session,
    query: str,
    limit: int = 5
):
    query_embedding = embed_text(query)

    sql = text("""
        SELECT content, section, page_number
        FROM document_chunks
        ORDER BY embedding <-> :embedding
        LIMIT :limit
    """)

    result = db.execute(sql, {
        "embedding": query_embedding,
        "limit": limit
    })

    return result.fetchall()
