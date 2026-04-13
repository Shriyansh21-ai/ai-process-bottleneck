# genai/agents/synthesizer.py

from typing import Dict

from openai import AsyncOpenAI
from src.genai.config.model_pricing import calculate_cost


class SynthesizerAgent:
    """
    Produces final polished response for user.
    """

    def __init__(self):
        self.model = "gpt-4o-mini"
        self.client = AsyncOpenAI()

    # ------------------------------------------------------------
    # FINAL RESPONSE GENERATION
    # ------------------------------------------------------------
    async def run(
        self,
        agent_outputs: Dict,
        task: str,
    ) -> Dict:

        raw_answer = agent_outputs.get("raw_answer", "")

        prompt = f"""
User task:
{task}

Raw agent answer:
{raw_answer}

Rewrite the answer:
- Clear
- Structured
- Professional
- Concise
- No internal reasoning

Provide final answer only.
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional response synthesizer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        # ---------------- TOKEN USAGE ----------------

        usage = response.usage

        cost = calculate_cost(
            model=self.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        final_text = response.choices[0].message.content.strip()

        return {
            "content": final_text,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost_usd": cost,
        }
