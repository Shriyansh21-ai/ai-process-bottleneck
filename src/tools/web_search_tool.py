import os
import logging

from src.agent.research_synthesizer import (
    ResearchSynthesizer
)


logger = logging.getLogger("web_search_tool")

# Lazily-built singletons. The Tavily client MUST NOT be constructed at import
# time: it raises MissingAPIKeyError when TAVILY_API_KEY is unset, and this
# module is imported (via register_tools) by ToolExecutor. A module-level
# construction would therefore break the import of the ENTIRE agent pipeline on
# any deployment without a Tavily key. TAVILY_API_KEY is optional (like
# OPENAI_API_KEY): a missing key degrades this single tool, not the whole app.
_client = None
_synthesizer = None


def _get_client():
    """Construct the Tavily client on first use. Returns None if unavailable."""
    global _client
    if _client is not None:
        return _client
    if not os.getenv("TAVILY_API_KEY"):
        return None
    try:
        from tavily import TavilyClient
        _client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    except Exception as e:  # missing package / bad key — degrade this tool only
        logger.warning("Tavily client unavailable: %s", str(e))
        return None
    return _client


def _get_synthesizer():
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = ResearchSynthesizer()
    return _synthesizer


def web_search(input_data: dict):

    query = input_data.get(
        "query",
        ""
    )

    client = _get_client()
    if client is None:
        # Graceful degradation: surface a controlled error the executor can
        # audit as a failed step, instead of crashing at import or call time.
        return {
            "error": "web_search unavailable: TAVILY_API_KEY is not configured",
            "query": query,
        }

    synthesizer = _get_synthesizer()

    response = client.search(

        query=query,

        search_depth="advanced",

        max_results=5
    )

    results = []

    for item in response.get(
        "results",
        []
    ):

        results.append({

            "title": item.get("title"),

            "url": item.get("url"),

            "content": item.get("content")
        })

    summary = synthesizer.synthesize(
    query=query,
    search_results=results
    )

    return {

        "query": query,

        "sources": results,

        "research_summary": summary
    }