from typing import List

from sqlalchemy import text

from src.db.session import SessionLocal
from src.models.genai_memory import GenAIMemory
from src.genai.embeddings import embed_text


class GenAIMemoryDB:

    def __init__(self, db, session_id):

        self.db = db
        self.session_id = session_id

    # ====================================================
    # ADD MEMORY
    # ====================================================

    def add_memory(self, content: str):

        try:

            embedding = embed_text(content)

            memory = GenAIMemory(

                session_id=self.session_id,

                content=content,

                embedding=str(embedding)
            )

            self.db.add(memory)

            self.db.commit()

            self.db.refresh(memory)

            return memory

        except Exception as e:

            self.db.rollback()

            print(
                f"⚠️ Memory save failed: {str(e)}"
            )

            return None

    # ====================================================
    # RETRIEVE MEMORIES
    # ====================================================

    def retrieve(
        self,
        query: str,
        top_k: int = 3
    ) -> List[str]:

        try:

            result = self.db.execute(

                text(
                    """
                    SELECT content
                    FROM genai_memory
                    WHERE session_id = :session_id
                    ORDER BY created_at DESC
                    LIMIT :top_k
                    """
                ),

                {
                    "session_id": self.session_id,
                    "top_k": top_k
                }
            )

            return [

                row[0]

                for row in result.fetchall()
            ]

        except Exception as e:

            print(
                f"⚠️ Memory retrieval failed: {str(e)}"
            )

            return []

    # ====================================================
    # SEARCH ALIAS
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

            {
                "content": memory
            }

            for memory in memories
        ]

    # ====================================================
    # GET ALL MEMORIES
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

            print(
                f"⚠️ Memory get_all failed: {str(e)}"
            )

            return []


# ====================================================
# GLOBAL HELPER
# ====================================================

def add_memory(
    content: str,
    session_id: str
):

    db = SessionLocal()

    try:

        memory_db = GenAIMemoryDB(

            db=db,

            session_id=session_id
        )

        return memory_db.add_memory(
            content=content
        )

    except Exception as e:

        print(
            f"⚠️ add_memory failed: {str(e)}"
        )

        db.rollback()

        return None

    finally:

        db.close()


# ====================================================
# GLOBAL HELPER
# ====================================================

def retrieve_memory(
    query: str,
    session_id: str,
    top_k: int = 3
):

    db = SessionLocal()

    try:

        memory_db = GenAIMemoryDB(

            db=db,

            session_id=session_id
        )

        return memory_db.search(

            query=query,

            limit=top_k
        )

    except Exception as e:

        print(
            f"⚠️ retrieve_memory failed: {str(e)}"
        )

        return []

    finally:

        db.close()


# ====================================================
# GLOBAL HELPER
# ====================================================

def get_all_memories(
    session_id: str
):

    db = SessionLocal()

    try:

        memory_db = GenAIMemoryDB(

            db=db,

            session_id=session_id
        )

        return memory_db.get_all()

    except Exception as e:

        print(
            f"⚠️ get_all_memories failed: {str(e)}"
        )

        return []

    finally:

        db.close()