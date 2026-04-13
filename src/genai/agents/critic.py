from src.genai.engine import GenAIEngine

class CriticAgent:
    def __init__(self):
        self.engine = GenAIEngine()

    def review(self, result: str) -> str:
        prompt = f"""
You are a critic agent.

Review the following output for:
- correctness
- clarity
- missing reasoning

Improve it if needed.

Output:
{result}
"""
        return self.engine.run(prompt)
