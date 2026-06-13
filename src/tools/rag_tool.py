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

    results = retrieve_context(
        db=db,
        query=query,
        limit=limit
    )

    return results