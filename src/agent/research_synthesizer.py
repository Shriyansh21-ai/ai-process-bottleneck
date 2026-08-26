import json

from openai import OpenAI


# The OpenAI client is built LAZILY (not at import time). Constructing OpenAI()
# eagerly raises OpenAIError when OPENAI_API_KEY is unset, and this module sits
# in the ToolExecutor import chain (register_tools -> web_search_tool -> here).
# An eager client therefore crashed the entire agent pipeline import on any
# deployment without an OpenAI key — even though the key is documented as
# OPTIONAL (see src/config.py). Deferring construction keeps the import safe.
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


SYSTEM_PROMPT = """
You are a Research Synthesis Agent.

Your job:
- Analyze multiple research sources
- Combine overlapping insights
- Remove redundancy
- Identify important trends
- Highlight conflicting information
- Generate a structured research summary

Rules:
- Use ONLY provided sources
- Do NOT hallucinate
- Keep output factual
"""


class ResearchSynthesizer:

    def synthesize(
        self,
        query: str,
        search_results: list
    ):

        response = _get_client().chat.completions.create(

            model="gpt-4o-mini",

            temperature=0,

            messages=[

                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },

                {
                    "role": "user",
                    "content": json.dumps({

                        "query": query,

                        "sources": search_results
                    })
                }
            ]
        )

        return response.choices[0].message.content