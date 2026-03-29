from sqlalchemy import text
from db.session import SessionLocal
from genai.embeddings import embed_text

def retrieve_memory(input_data: dict):
    query_text = input_data.get("query", "")
    top_k = input_data.get("top_k", 3)

    embedding = embed_text(query_text)

    sql = """
    SELECT content
    FROM genai_memory
    ORDER BY embedding <-> :embedding
    LIMIT :top_k
    """

    db = SessionLocal()
    try:
        result = db.execute(
            text(sql),
            {"embedding": embedding, "top_k": top_k}
        )
        return [row[0] for row in result.fetchall()]
    finally:
        db.close()
