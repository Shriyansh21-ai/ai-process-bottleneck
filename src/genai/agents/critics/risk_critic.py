# src/genai/agents/critics/risk_critic.py

import json
from openai import AsyncOpenAI

class RiskCritic:

    def __init__(self):
        self.client = AsyncOpenAI()
        self.model = "gpt-4o-mini"

    async def critique(self, query: str, answer: str):

        prompt = f"""
Check risks, harmful outputs, unsafe reasoning.

Return JSON:
{{
 "safe": true/false,
 "risks": [],
 "severity": "low/medium/high"
}}
"""

        res = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            return json.loads(res.choices[0].message.content)
        except:
            return {"safe": True, "risks": [], "severity": "low"}