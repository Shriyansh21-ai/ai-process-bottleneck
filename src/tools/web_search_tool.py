import os

from tavily import TavilyClient

from src.agent.research_synthesizer import (
    ResearchSynthesizer
)


client = TavilyClient(
    api_key=os.getenv(
        "TAVILY_API_KEY"
    )
)

synthesizer = ResearchSynthesizer()

def web_search(input_data: dict):

    query = input_data.get(
        "query",
        ""
    )

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