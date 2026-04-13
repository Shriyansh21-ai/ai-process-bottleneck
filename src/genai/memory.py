from src.models.genai_memory import GenAIMemory
from src.genai.embeddings import embed_text
from sqlalchemy.orm import Session
from typing import List


class GenAIMemoryDB:

    def __init__(self, db, session_id):
        self.db = db
        self.session_id = session_id

    def add_memory(self, session_id: str, content: str):
        embedding = embed_text(content)

        memory = GenAIMemory(
            session_id=session_id,
            content=content,
            embedding=embedding
        )

        self.db.add(memory)
        self.db.commit()

    def retrieve(self, session_id: str, query: str, top_k: int = 3) -> List[str]:
        embedding = embed_text(query)

        result = self.db.execute(
            """
            SELECT content
            FROM genai_memory
            WHERE session_id = :session_id
            ORDER BY embedding <-> :embedding
            LIMIT :top_k
            """,
            {
                "session_id": session_id,
                "embedding": embedding,
                "top_k": top_k
            }
        )

        return [row[0] for row in result.fetchall()]
