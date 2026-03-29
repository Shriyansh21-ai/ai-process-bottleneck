from genai.agents.planner import PlannerAgent
from genai.agents.memory_retriever import RetrieverAgent
from genai.agents.analyst import AnalystAgent
from genai.agents.recommender import RecommenderAgent
from genai.agents.synthesizer import SynthesizerAgent

class AgentRunner:
    def __init__(self, db):
        self.db = db
        self.planner = PlannerAgent()
        self.retriever = RetrieverAgent(db)
        self.analyst = AnalystAgent()
        self.recommender = RecommenderAgent()
        self.synthesizer = SynthesizerAgent()

    async def run(self, task: str):
        plan = await self.planner.plan(task)

        outputs = {}

        for step in plan:
            if step == "retrieve":
                outputs["retrieve"] = await self.retriever.run(task)

            elif step == "analyze":
                outputs["analysis"] = await self.analyst.run(
                    outputs.get("retrieve", ""),
                    task
                )

            elif step == "recommend":
                outputs["recommend"] = await self.recommender.run(
                    outputs.get("analysis", "")
                )

        return await self.synthesizer.run(outputs)
