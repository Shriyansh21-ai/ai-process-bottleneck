from src.genai.memory import (
    GenAIMemoryDB
)

from src.db.session import SessionLocal


def load_memory(input_data: dict):

    session_id = input_data.get(
        "session_id",
        "default"
    )

    query = input_data.get(
        "query",
        ""
    )

    limit = input_data.get(
        "limit",
        5
    )

    db = SessionLocal()

    try:

        memory_db = GenAIMemoryDB(
            db=db,
            session_id=session_id
        )

        results = memory_db.search(
            query=query,
            limit=limit
        )

        return results

    finally:

        db.close()