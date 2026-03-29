from genai.memory import GenAIMemoryDB

class RetrieverAgent:
    def __init__(self, db):
        self.memory = GenAIMemoryDB(db)

    def retrieve(self, query: str) -> str:
        chunks = self.memory.retrieve(query)
        return "\n".join(chunks)
