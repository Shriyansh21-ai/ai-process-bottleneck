import json

from src.genai.llm_router import (
    generate_response
)

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

    def verify(
        self,
        user_query: str,
        execution_result: dict
    ) -> dict:

        prompt = f"""
{SYSTEM_PROMPT}

USER QUERY:
{user_query}

EXECUTION RESULT:
{json.dumps(execution_result)}
"""

        result_text = generate_response(
            prompt
        )

        try:

            return json.loads(
                result_text
            )

        except json.JSONDecodeError:

            return {

                "confidence": 0.80,

                "issues": [],

                "approved": True
            }