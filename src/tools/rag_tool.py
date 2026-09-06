from src.rag.retriever import (
    retrieve_context
)


def rag_search(input_data: dict):

    db = input_data["db"]

    query = input_data["query"]

    limit = input_data.get(
        "top_k",
        5
    )

    # MRPL Phase 3 (additive): when the planner scopes retrieval to a single
    # document, forward the id so evidence is drawn ONLY from that document.
    # Absent -> corpus-wide retrieval, exactly as before.
    document_id = input_data.get("document_id")

    results = retrieve_context(
        db=db,
        query=query,
        limit=limit,
        document_id=document_id,
    )

    return results
