import json

from openai import OpenAI


client = OpenAI()


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

        response = client.chat.completions.create(

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