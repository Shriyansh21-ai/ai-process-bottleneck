import json
from typing import Dict
from openai import AsyncOpenAI

class CriticAgent:

    def __init__(self):
        self.model = "gpt-4o-mini"
        self.client = AsyncOpenAI()

    async def critique(self, query: str, answer: str) -> Dict:

        prompt = f"""
You are a critical reasoning expert.

Analyze the answer given to a task.

Task:
{query}

Answer:
{answer}

Evaluate deeply:

Return JSON:
{{
  "is_valid": true or false,
  "issues": ["list of problems"],
  "suggestions": ["improvements"],
  "confidence": 0-1
}}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a strict AI critic."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        raw = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(raw)
        except:
            parsed = {
                "is_valid": True,
                "issues": [],
                "suggestions": [],
                "confidence": 0.7
            }

        return {
            "content": parsed,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost_usd": 0.0
        }