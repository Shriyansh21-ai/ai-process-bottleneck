import json
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
You are a Verification Agent.

Your job:
- Evaluate the agent execution result
- Identify hallucinations, assumptions, or weak reasoning
- Rate confidence from 0 to 1
- Output STRICT JSON only

Rules:
- Do NOT add new facts
- Do NOT rewrite results
- Base evaluation ONLY on execution output
"""

class VerifierAgent:
    def verify(self, user_query: str, execution_result: dict) -> dict:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps({
                        "user_query": user_query,
                        "execution_result": execution_result
                    })
                }
            ]
        )

        result_text = response.choices[0].message.content

        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {
                "confidence": 0.0,
                "issues": ["Invalid verifier output"],
                "approved": False
            }
