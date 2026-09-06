from sqlalchemy.orm import Session

from src.rag.embeddings import (
    embed_text
)

from src.db.qdrant import client


SIMILARITY_THRESHOLD = 0.45


def retrieve_context(
    db: Session,
    query: str,
    limit: int = 5,
    document_id=None,
):
    """Retrieve semantically relevant chunks from the vector store.

    MRPL Phase 3 (additive, backward compatible):

      * ``document_id`` — when provided, restrict the search to a single ingested
        document via a Qdrant payload filter. This lets the inspection workflow
        retrieve evidence ONLY from the just-uploaded report instead of the whole
        corpus. Omitting it preserves the previous corpus-wide behaviour.
      * each returned context now also carries ``page_number``,
        ``extraction_method`` and ``document_id`` (when present in the stored
        payload) so downstream consumers can attach page-level provenance to a
        finding. Legacy callers that only read ``content``/``score`` are
        unaffected.
    """

    # ==========================================
    # GENERATE QUERY EMBEDDING
    # ==========================================

    query_embedding = embed_text(query)

    # ==========================================
    # OPTIONAL DOCUMENT-SCOPED FILTER
    # ==========================================
    # Only build a filter when a document_id is supplied, so unscoped searches
    # issue exactly the same query as before.
    query_filter = None
    if document_id is not None:
        # Imported lazily so the retriever module import stays light and the
        # legacy (unscoped) path never constructs filter objects.
        from qdrant_client.models import (
            Filter,
            FieldCondition,
            MatchValue,
        )

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

    # ==========================================
    # SEARCH QDRANT
    # ==========================================

    results = client.query_points(

        collection_name="documents",

        query=query_embedding,

        limit=limit,

        query_filter=query_filter,
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

            # Page-level provenance (MRPL Phase 3). Present only for documents
            # ingested with per-page structure; None for legacy documents.
            "document_id": payload.get(
                "document_id"
            ),

            "page_number": payload.get(
                "page_number"
            ),

            "extraction_method": payload.get(
                "extraction_method"
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