from sqlalchemy.orm import Session

from src.rag.embeddings import (
    embed_text
)

from src.db.qdrant import client


SIMILARITY_THRESHOLD = 0.45


def retrieve_context(
    db: Session,
    query: str,
    limit: int = 5
):

    # ==========================================
    # GENERATE QUERY EMBEDDING
    # ==========================================

    query_embedding = embed_text(query)

    # ==========================================
    # SEARCH QDRANT
    # ==========================================

    results = client.query_points(

        collection_name="documents",

        query=query_embedding,

        limit=limit
    )

    # ==========================================
    # FORMAT RESULTS
    # ==========================================

    contexts = []

    seen_contents = set()

    for result in results.points:

        # ==========================================
        # FILTER LOW QUALITY MATCHES
        # ==========================================

        if result.score < SIMILARITY_THRESHOLD:
            continue

        payload = result.payload or {}

        content = payload.get("content")

        # ==========================================
        # SKIP EMPTY CONTENT
        # ==========================================

        if not content:
            continue

        # ==========================================
        # REMOVE DUPLICATE CHUNKS
        # ==========================================

        if content in seen_contents:
            continue

        seen_contents.add(content)

        # ==========================================
        # BUILD CONTEXT OBJECT
        # ==========================================

        contexts.append({

            "content": content,

            "title": payload.get(
                "title"
            ),

            "source": payload.get(
                "source"
            ),

            "doc_type": payload.get(
                "doc_type"
            ),

            "chunk_index": payload.get(
                "chunk_index"
            ),

            "score": round(
                result.score,
                4
            )
        })

    # ==========================================
    # DEBUG LOGGING
    # ==========================================

    print("\n=== SEMANTIC SEARCH RESULTS ===")

    if not contexts:

        print("No relevant contexts found")

    else:

        for c in contexts:
            print(c)

    return contexts