from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models.document import Document

from src.rag.retriever import (
    retrieve_context
)

from src.genai.offline.ollama_client import (
    OllamaClient
)


router = APIRouter(
    prefix="/rag",
    tags=["RAG"]
)


@router.post("/")
async def rag_query(
    # Bound the query length — this drives retrieval + an LLM generation, so an
    # unbounded prompt is a cost/resource-abuse vector.
    query: str = Query(..., min_length=1, max_length=4000),
    db: Session = Depends(get_db)
):

    documents = db.query(Document).all()

    relevant_docs = retrieve_context(
    db=db,
    query=query
)

    context = "\n".join([
        doc["content"]
        for doc in relevant_docs
    ])

    prompt = f"""
You are an AI assistant.

Use the following context to answer.

Context:
{context}

Question:
{query}
"""

    ollama = OllamaClient()

    response = await ollama.generate(prompt)

    return {
        "query": query,
        "retrieved_context": context,
        "response": response
    }