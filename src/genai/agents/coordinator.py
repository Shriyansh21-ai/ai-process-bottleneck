from genai.agents.planner import PlannerAgent
from genai.agents.memory_retriever import RetrieverAgent
from genai.agents.executor import ExecutorAgent
from genai.agents.critic import CriticAgent

class CoordinatorAgent:
    def __init__(self, db):
        self.planner = PlannerAgent()
        self.retriever = RetrieverAgent(db)
        self.executor = ExecutorAgent()
        self.critic = CriticAgent()

    def run(self, task: str) -> str:
        plan = self.planner.plan(task)
        context = self.retriever.retrieve(task)

        results = []
        for step in plan:
            result = self.executor.execute(step, context)
            results.append(result)

        combined = "\n".join(results)
        final = self.critic.review(combined)
        return final
