# genai/agents/decomposition_agent.py

import json
from typing import Dict, List

from openai import AsyncOpenAI
from genai.config.model_pricing import calculate_cost


class DecompositionAgent:
    """
    Breaks complex task into ordered subtasks.
    """

    def __init__(self):
        self.model = "gpt-4o-mini"
        self.client = AsyncOpenAI()

    async def decompose(self, query: str) -> Dict:

        prompt = f"""
You are an advanced AI planner.

Break the following task into clear, ordered subtasks.

Task:
{query}

Respond strictly in JSON:

{{
  "is_complex": true or false,
  "subtasks": [
    "subtask 1",
    "subtask 2"
  ]
}}

If task is simple, return:
{{
  "is_complex": false,
  "subtasks": []
}}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a strategic decomposition planner."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        usage = response.usage

        cost = calculate_cost(
            model=self.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        raw_content = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            parsed = {
                "is_complex": False,
                "subtasks": []
            }

        parsed.setdefault("is_complex", False)
        parsed.setdefault("subtasks", [])

        return {
            "content": parsed,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost_usd": cost,
        }
