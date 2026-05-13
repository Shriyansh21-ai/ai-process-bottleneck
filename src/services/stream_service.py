from src.rag.retriever import retrieve_context
from src.rag.prompt_builder import build_rag_prompt

from src.genai.openai.openai_client import OpenAIClient

openai_client = OpenAIClient()


async def stream_rag_response(
    db,
    query: str
):

    contexts = retrieve_context(
        db=db,
        query=query
    )

    prompt = build_rag_prompt(
        query=query,
        contexts=contexts
    )

    async for token in openai_client.stream_generate(
        prompt
    ):

        yield token