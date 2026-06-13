

from sqlalchemy.orm import Session
from typing import Dict, Any
from src.rag.retriever import retrieve_context
from src.models.case import Case

def search_cases(db: Session, query: str) -> str:
    """Search historical cases related to a bottleneck"""
    cases = (
        db.query(Case)
        .filter(Case.description.ilike(f"%{query}%"))
        .limit(5)
        .all()
    )

    if not cases:
        return "No relevant historical cases found."

    return "\n".join(
        f"- Case {c.id}: {c.description}" for c in cases
    )


def retrieve_documents(db: Session, query: str) -> str:
    """Retrieve context using pgvector RAG"""
    return retrieve_context(db, query)


def analyze_metrics(data: Dict[str, Any]) -> str:
    """Simple analytical tool"""
    if not data:
        return "No metrics provided."

    avg = sum(data.values()) / len(data)
    return f"Average metric value is {avg:.2f}"
