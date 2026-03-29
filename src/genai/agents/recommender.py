from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class RecommenderAgent:
    async def run(self, analysis: str):
        prompt = f"""
You are a recommendation agent.

Based on this analysis:
{analysis}

Give clear, actionable recommendations.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content
