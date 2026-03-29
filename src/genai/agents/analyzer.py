from genai.agents.base import BaseAgent
from genai.memory import GenAIMemoryDB

class AnalyzerAgent(BaseAgent):
    name = "memory-agent"

    async def run(self, db, query: str):
        memory = GenAIMemoryDB(db)
        return await self.execute(
            lambda: memory.retrieve(query),
            input_data=query
        )
