import os

from sqlalchemy.orm import Session

from src.rag.embeddings import (
    embed_text
)

from src.db.qdrant import client


def _similarity_threshold() -> float:
    """Minimum cosine score for a retrieved chunk (``RAG_SIMILARITY_THRESHOLD``).

    Default 0.45 preserves the previous behaviour exactly. It is made
    configurable so short/local demo corpora (where absolute similarity scores
    run lower) can admit relevant page-level evidence without a code change.
    """
    try:
        value = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.45"))
        return value if 0.0 <= value <= 1.0 else 0.45
    except (TypeError, ValueError):
        return 0.45


# Backwards-compatible module constant (default). Runtime filtering uses
# _similarity_threshold() so the env var is honoured without a restart-time bake-in.
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

    threshold = _similarity_threshold()

    for result in results.points:

        # ==========================================
        # FILTER LOW QUALITY MATCHES
        # ==========================================

        if result.score < threshold:
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