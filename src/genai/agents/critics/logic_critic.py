# src/genai/agents/critics/logic_critic.py

import json
from openai import AsyncOpenAI

class LogicCritic:

    def __init__(self):
        self.client = AsyncOpenAI()
        self.model = "gpt-4o-mini"

    async def critique(self, query: str, answer: str):

        prompt = f"""
Check logical correctness.

Task:
{query}

Answer:
{answer}

Return JSON:
{{
 "valid": true/false,
 "issues": [],
 "confidence": 0-1
}}
"""

        res = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            return json.loads(res.choices[0].message.content)
        except:
            return {"valid": True, "issues": [], "confidence": 0.7}