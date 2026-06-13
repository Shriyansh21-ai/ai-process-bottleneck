import json

from src.genai.llm_router import (
    generate_response
)

from src.agent.plan_validator import (
    PlanValidator
)

from src.tools.tool_registry import (
    ToolRegistry
)

from src.utils.logger import (
    setup_logger
)

logger = setup_logger()


SYSTEM_PROMPT = """
You are an autonomous AI Planner.

Your responsibilities:

- Analyze user requests
- Create execution workflows
- Select ONLY available tools
- Optimize workflows
- Use memory context when available
- Use verifier feedback to improve plans
- Return STRICT JSON ONLY

==========================================
PLANNING RULES
==========================================

Each step MUST contain:

- step_id
- tool
- purpose
- input
- depends_on

Rules:

- Never invent tools
- Never skip required analysis
- Independent steps should run in parallel
- Dependent steps should reference prior step_ids
- Use memory if useful
- Use web search for latest information
- Keep workflows efficient

Return STRICT JSON ONLY.
"""


class PlannerAgent:

    def __init__(self):

        self.validator = PlanValidator()

    # ==========================================
    # TOOL SECTION
    # ==========================================

    def build_tool_section(self):

        tools = ToolRegistry.get_all_tools()

        lines = []

        for name, meta in tools.items():

            lines.append(
                f"{name} → {meta['description']}"
            )

        return "\n".join(lines)

    # ==========================================
    # FALLBACK REPAIR PLAN
    # ==========================================

    def repair_plan(
        self,
        user_query: str,
        reason: str
    ):

        logger.warning(
            f"Repairing plan | reason={reason}"
        )

        return {

            "goal": user_query,

            "repair_reason": reason,

            "steps": [

                {
                    "step_id": 1,

                    "tool": "rag_retrieval",

                    "purpose": (
                        "Retrieve relevant historical context"
                    ),

                    "input": {
                        "query": user_query
                    },

                    "depends_on": []
                },

                {
                    "step_id": 2,

                    "tool": "memory_tool",

                    "purpose": (
                        "Collect external information"
                    ),

                    "input": {
                        "query": user_query
                    },

                    "depends_on": []
                },

                {
                    "step_id": 3,

                    "tool": "ml_analysis",

                    "purpose": (
                        "Analyze collected information"
                    ),

                    "input": {
                        "query": user_query
                    },

                    "depends_on": [
                        1,
                        2
                    ]
                }
            ]
        }

    # ==========================================
    # PLAN CREATION
    # ==========================================

    def create_plan(
        self,
        user_query: str,
        previous_feedback=None,
        memory_context=None
    ) -> dict:

        logger.info(
            f"Creating plan for: {user_query}"
        )

        tool_section = self.build_tool_section()

        memory_text = ""

        if memory_context:

            for idx, item in enumerate(memory_context, start=1):

                memory_text += (
                    f"\nMemory {idx}:\n"
                    f"{item.get('content', '')}\n"
                )
        else:

            memory_text = "No relevant memories found."

        prompt = f"""
{SYSTEM_PROMPT}

==========================================
AVAILABLE TOOLS
==========================================

{tool_section}

==========================================
USER REQUEST
==========================================

{user_query}

==========================================
PREVIOUS FEEDBACK
==========================================

{previous_feedback}

==========================================
MEMORY CONTEXT
==========================================

{memory_text}

==========================================
OUTPUT FORMAT
==========================================

Example:

{{
    "goal": "{user_query}",
    "steps": [
        {{
            "step_id": 1,
            "tool": "rag_retrieval",
            "purpose": "retrieve context",
            "input": {{
                "query": "{user_query}"
            }},
            "depends_on": []
        }}
    ]
}}

Return STRICT JSON ONLY.
"""

        # ==========================================
        # CALL LLM
        # ==========================================

        try:

            plan_text = generate_response(
                prompt
            )
            if '"confidence"' in plan_text:

                logger.warning(
                    "LLM returned fallback response"
                )

                return self.repair_plan(

                    user_query,

                    "LLM offline fallback detected"
                )

        except Exception as e:

            logger.error(
                f"Planner LLM failed: {str(e)}"
            )

            return self.repair_plan(

                user_query,

                f"Planner LLM failure: {str(e)}"
            )

        # ==========================================
        # PARSE JSON
        # ==========================================

        try:

            plan = json.loads(
                plan_text
            )

        except Exception:

            logger.error(
                "Planner returned invalid JSON"
            )

            return self.repair_plan(

                user_query,

                "Invalid JSON returned by planner"
            )

        # ==========================================
        # ENSURE GOAL EXISTS
        # ==========================================

        if "goal" not in plan:

            plan["goal"] = user_query

        # ==========================================
        # VALIDATE PLAN
        # ==========================================

        try:

            self.validator.validate(
                plan
            )

            self.validator.detect_cycles(
                plan
            )

        except Exception as e:

            logger.error(
                f"Plan validation failed: {str(e)}"
            )

            return self.repair_plan(

                user_query,

                str(e)
            )

        logger.info(
            f"Plan validated successfully | steps={len(plan.get('steps', []))}"
        )

        return plan