from tools.sql_tool import run_sql_query
from tools.ml_tool import run_ml_analysis
from tools.rag_tool import retrieve_memory
from utils.logger import setup_logger

logger = setup_logger()

class ToolExecutor:
    def __init__(self):
        self.tool_map = {
            "sql_query": run_sql_query,
            "ml_analysis": run_ml_analysis,
            "rag_retrieval": retrieve_memory,
        }

    def execute_plan(self, plan: dict) -> dict:
        results = []

        for step in plan.get("steps", []):
            tool_name = step["tool"]
            logger.info(f"Executing tool: {tool_name}")

            if tool_name not in self.tool_map:
                logger.error(f"Unauthorized tool attempted: {tool_name}")
                raise ValueError(f"Unauthorized tool: {tool_name}")

            output = self.tool_map[tool_name](step.get("input", {}))

            results.append({
                "step_id": step["step_id"],
                "tool": tool_name,
                "output": output
            })

        return {
            "goal": plan.get("goal"),
            "results": results
        }
