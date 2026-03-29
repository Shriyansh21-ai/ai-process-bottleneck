# genai/tool_registry.py

from genai.tools import search_cases, retrieve_documents, analyze_metrics

TOOL_REGISTRY = {
    "search_cases": search_cases,
    "retrieve_documents": retrieve_documents,
    "analyze_metrics": analyze_metrics,
}
