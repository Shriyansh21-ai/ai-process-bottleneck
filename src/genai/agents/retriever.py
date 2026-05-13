from src.genai.agents.base import BaseAgent
from rag.retriever import retrieve_context

class RetrieverAgent(BaseAgent):
    name = "retriever-agent"

    async def run(self, db, query: str):
        return await self.execute(
            lambda: retrieve_context(db, query),
            input_data=query
        )
