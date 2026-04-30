# src/genai/agents/critics/optimization_critic.py

import json
from openai import AsyncOpenAI

class OptimizationCritic:

    def __init__(self):
        self.client = AsyncOpenAI()
        self.model = "gpt-4o-mini"

    async def critique(self, query: str, answer: str):

        prompt = f"""
Suggest improvements or better approaches.

Return JSON:
{{
 "can_improve": true/false,
 "suggestions": []
}}
"""

        res = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            return json.loads(res.choices[0].message.content)
        except:
            return {"can_improve": False, "suggestions": []}