import asyncio
import os
from src.genai.agents.base import BaseAgent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = None
if OPENAI_API_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)


class MemorySummarizerAgent(BaseAgent):
    name = "memory-summarizer-agent"

    async def run(self, memories: list[str]) -> str:
        async def call_llm():
            joined_memory = "\n".join(memories)

            prompt = f"""
You are a memory compression agent.

Summarize the following conversation memory
into a concise, long-term usable summary.

Memory:
{joined_memory}

Rules:
- Keep important facts
- Remove redundancy
- Max 5–7 bullet points
"""

            if client is None:
                # Fallback summarizer for local testing
                return "[SUMMARY FALLBACK] " + " ".join(joined_memory.split()[:100])

            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                )
            )

            return response.choices[0].message.content

        return await self.execute(
            call_llm,
            input_data=f"{len(memories)} memories"
        )
