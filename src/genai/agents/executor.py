from src.genai.engine import GenAIEngine

class ExecutorAgent:
    def __init__(self):
        self.engine = GenAIEngine()

    def execute(self, step: str, context: str) -> str:
        prompt = f"""
Context:
{context}

Execute the following step carefully:
{step}
"""
        return self.engine.run(prompt)
