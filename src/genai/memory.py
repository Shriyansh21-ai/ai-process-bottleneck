from typing import List

from sqlalchemy import text

from src.models.genai_memory import GenAIMemory
from src.genai.embeddings import embed_text


class GenAIMemoryDB:

    def __init__(self, db, session_id):
        self.db = db
        self.session_id = session_id

    # ====================================================
    # ✅ ADD MEMORY
    # ====================================================

    def add_memory(self, session_id: str, content: str):

        embedding = embed_text(content)

        memory = GenAIMemory(
            session_id=session_id,
            content=content,
            embedding=embedding
        )

        try:
            self.db.add(memory)
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            print("⚠️ Memory save failed:", str(e))

    # ====================================================
    # ✅ VECTOR RETRIEVAL
    # ====================================================

    def retrieve(
        self,
        query: str,
        top_k: int = 3
    ) -> List[str]:

        try:

            embedding = embed_text(query)

            result = self.db.execute(
                text(
                    """
                    SELECT content
                    FROM genai_memory
                    WHERE session_id = :session_id
                    ORDER BY embedding <-> :embedding
                    LIMIT :top_k
                    """
                ),
                {
                    "session_id": self.session_id,
                    "embedding": embedding,
                    "top_k": top_k
                }
            )

            return [
                row[0]
                for row in result.fetchall()
            ]

        except Exception as e:

            print("⚠️ Memory retrieval failed:", str(e))
            return []

    # ====================================================
    # ✅ SEARCH ALIAS
    # ====================================================

    def search(
        self,
        query: str,
        limit: int = 3
    ):

        memories = self.retrieve(
            query=query,
            top_k=limit
        )

        return [
            {"content": m}
            for m in memories
        ]

    # ====================================================
    # ✅ GET ALL MEMORIES
    # ====================================================

    def get_all(self):

        try:

            result = self.db.execute(
                text(
                    """
                    SELECT content
                    FROM genai_memory
                    WHERE session_id = :session_id
                    ORDER BY created_at DESC
                    LIMIT 100
                    """
                ),
                {
                    "session_id": self.session_id
                }
            )

            return [
                row[0]
                for row in result.fetchall()
            ]

        except Exception as e:

            print("⚠️ Memory get_all failed:", str(e))
            return []