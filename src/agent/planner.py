import json
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
You are an autonomous AI Planner.

Your job:
- Analyze the user request
- Create a step-by-step execution plan
- Choose ONLY from the allowed tools
- Output STRICT JSON (no markdown, no text)

Allowed tools:
1. sql_query        → query PostgreSQL data
2. ml_analysis      → detect bottlenecks using ML
3. rag_retrieval    → fetch historical memory
4. generate_report  → produce final insights

Rules:
- Never invent tools
- Each step must have: step_id, tool, purpose, input
- Keep steps minimal and logical
"""

class PlannerAgent:
    def create_plan(self, user_query: str) -> dict:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}
            ]
        )

        plan_text = response.choices[0].message.content

        try:
            plan = json.loads(plan_text)
        except json.JSONDecodeError:
            raise ValueError("Planner output is not valid JSON")

        return plan
