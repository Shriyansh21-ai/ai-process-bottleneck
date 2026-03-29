from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class AnalystAgent:
    async def run(self, context: str, task: str):
        prompt = f"""
You are an analysis agent.

Context:
{context}

Task:
{task}

Analyze root causes and insights.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content
