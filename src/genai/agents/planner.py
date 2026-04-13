# genai/agents/planner.py

import json
from typing import Dict, List

from openai import AsyncOpenAI
from src.genai.config.model_pricing import calculate_cost


class PlannerAgent:
    """
    Agentic ReAct Planner

    Decides:
    - Use tool
    - Or produce final answer
    """

    def __init__(self):
        self.model = "gpt-4o-mini"
        self.client = AsyncOpenAI()

    # ------------------------------------------------------------
    # MAIN AGENTIC PLANNER
    # ------------------------------------------------------------
    async def plan_agentic(
        self,
        query: str,
        scratchpad: str,
        tools: List[Dict],
    ) -> Dict:

        tool_descriptions = "\n".join(
            [
                f"- {tool['name']}: {tool.get('description', '')}"
                for tool in tools
            ]
        )

        prompt = f"""
You are an autonomous AI planner using ReAct reasoning.

User query:
{query}

Available tools:
{tool_descriptions}

Previous reasoning:
{scratchpad}

You must respond in JSON.

If tool is needed:
{{
  "type": "tool",
  "tool_name": "<tool name>",
  "tool_input": "<input for tool>"
}}

If final answer:
{{
  "type": "final",
  "content": "<final answer>"
}}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a precise reasoning agent."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        # ---------------- TOKEN USAGE ----------------

        usage = response.usage

        cost = calculate_cost(
            model=self.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        # ---------------- PARSE OUTPUT ----------------

        raw_content = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            # Fallback → force final answer
            parsed = {
                "type": "final",
                "content": raw_content
            }

        # ---------------- STANDARDIZED RETURN ----------------

        return {
            "content": parsed,  # structured JSON
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost_usd": cost,
        }
