import os
import json
from typing import Dict

from openai import AsyncOpenAI
from src.genai.config.model_pricing import calculate_cost


class DecompositionAgent:
    def __init__(self):
        self.model = "gpt-4o-mini"
        self.client = AsyncOpenAI()

    async def decompose(self, query: str, model: str = None, **kwargs) -> Dict:

        model_to_use = model if model else self.model

        # 🔥 STEP 1: OFFLINE MODE CHECK
        if os.getenv("OPENAI_ENABLED", "false").lower() != "true":
            print("⚠️ OFFLINE MODE: Using fallback decomposition")

            return self._fallback_response(query)

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

        try:
            # 🔥 STEP 2: SAFE OPENAI CALL
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "You are a strategic decomposition planner."},
                    {"role": "user", "content": prompt},
                ],
                temperature=kwargs.get("temperature", 0.2),
            )

            usage = response.usage

            raw_content = response.choices[0].message.content.strip()

            try:
                parsed = json.loads(raw_content)
            except json.JSONDecodeError:
                print("⚠️ JSON parsing failed, using fallback")
                return self._fallback_response(query)

            parsed.setdefault("is_complex", False)
            parsed.setdefault("subtasks", [])

            cost = calculate_cost(
                model=model_to_use,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )

            return {
                "content": parsed,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "cost_usd": cost,
                "model_used": model_to_use,
            }

        except Exception as e:
            # 🔥 STEP 3: GLOBAL FALLBACK (MOST IMPORTANT)
            print("🔥 OpenAI FAILED:", str(e))

            return self._fallback_response(query)

    # 🔥 STEP 4: SMART FALLBACK FUNCTION
    def _fallback_response(self, query: str) -> Dict:
        words = query.lower().split()

        if "bottleneck" in words or "analyze" in words:
            parsed = {
                "is_complex": True,
                "subtasks": [
                    "Understand the system/process",
                    "Identify bottlenecks",
                    "Analyze delays or inefficiencies",
                    "Suggest optimizations"
                ]
            }
        else:
            parsed = {
                "is_complex": len(words) > 8,
                "subtasks": [
                    "Process input",
                    "Generate response"
                ] if len(words) > 8 else []
            }

        return {
            "content": parsed,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0,
            "model_used": "fallback-mode",
        }