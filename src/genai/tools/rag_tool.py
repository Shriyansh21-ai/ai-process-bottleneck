# genai/tools/rag_tool.py

from src.genai.tools.tool_registry import ai_tool
from src.rag.retreiver import retrieve_context


@ai_tool(
    name="rag_search",
    description="Search knowledge base documents for relevant context."
)
def rag_search_tool(engine, query: str):
    return retrieve_context(engine.db, query)

