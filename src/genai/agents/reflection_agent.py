# genai/agents/reflection_agent.py

import json
from typing import Dict

from openai import AsyncOpenAI
from genai.config.model_pricing import calculate_cost


class ReflectionAgent:
    """
    Evaluates agent output quality.
    Decides whether refinement is needed.
    """

    def __init__(self):
        self.model = "gpt-4o-mini"
        self.client = AsyncOpenAI()

    # ------------------------------------------------------------
    # REFLECTION
    # ------------------------------------------------------------
    async def reflect(
        self,
        query: str,
        answer: str,
        scratchpad: str,
    ) -> Dict:

        prompt = f"""
You are an AI reflection system.

User query:
{query}

Agent reasoning trace:
{scratchpad}

Final answer:
{answer}

Evaluate:
1. Is the answer logically correct?
2. Is it complete?
3. Any hallucination risk?
4. Any missing reasoning?

Respond strictly in JSON:

{{
  "approved": true or false,
  "feedback": "short explanation",
  "confidence": 0.0 to 1.0
}}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a strict AI evaluator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        # ---------------- TOKEN USAGE ----------------

        usage = response.usage

        cost = calculate_cost(
            model=self.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        raw_content = response.choices[0].message.content.strip()

        # ---------------- SAFE PARSING ----------------

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            parsed = {
                "approved": True,
                "feedback": "Reflection parsing failed. Default approved.",
                "confidence": 0.9,
            }

        # Ensure required keys exist
        parsed.setdefault("approved", True)
        parsed.setdefault("feedback", "")
        parsed.setdefault("confidence", 1.0)

        return {
            "content": parsed,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost_usd": cost,
        }
