# genai/tools/memory_tool.py

from genai.tools.tool_registry import ai_tool


@ai_tool(
    name="recall_memory",
    description="Retrieve previous conversation memory from this session."
)
def memory_recall_tool(engine, query: str):
    return engine.memory.retrieve(engine.session_id, query)

