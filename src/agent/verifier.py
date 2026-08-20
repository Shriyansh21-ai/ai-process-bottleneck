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

            # Fail CLOSED: if the verifier's own output cannot be parsed we
            # cannot vouch for the result. Returning approved=True here would
            # silently disable the safety gate exactly when it is unusable, so
            # we mark the result unverified/not-approved instead.
            return {

                "confidence": 0.0,

                "issues": [
                    "verifier output unparseable — result could not be verified"
                ],

                "approved": False
            }