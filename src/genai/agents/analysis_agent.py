import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# genai/agents/analysis_agent.py

import asyncio
import os
from openai import OpenAI

from genai.agents.base import BaseAgent

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AnalysisAgent(BaseAgent):
    """
    Deep analysis agent

    Responsibilities:
    - Analyze context + task
    - Identify bottlenecks, causes, insights
    - Return analysis + confidence score
    """

    name = "analysis-agent"

    async def run(self, context: str, task: str) -> dict:
        async def call_llm():

            # Safety check
            if not context.strip():
                return {
                    "output": "Insufficient context available for meaningful analysis.",
                    "confidence": 0.4,
                }

            prompt = f"""
You are an expert analysis agent.

Context:
{context}

Task:
{task}

Analyze deeply and provide:
1. Key bottlenecks
2. Root causes
3. Insights

After analysis, estimate how confident you are (0–1).

Return STRICT JSON:
{{
  "output": "...",
  "confidence": 0.0
}}
"""

            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                )
            )

            raw = response.choices[0].message.content

            # Safe JSON parsing
            try:
                import json
                parsed = json.loads(raw)
                return {
                    "output": parsed.get("output", ""),
                    "confidence": float(parsed.get("confidence", 0.7)),
                }
            except Exception:
                return {
                    "output": raw,
                    "confidence": 0.7,
                }

        return await self.execute(
            call_llm,
            input_data=task
        )
