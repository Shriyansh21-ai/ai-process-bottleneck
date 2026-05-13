from src.rag.retriever import retrieve_context
from src.rag.prompt_builder import build_rag_prompt
from src.genai.offline.ollama_client import OllamaClient

ollama_client = OllamaClient()

async def rag_answer(db, query: str):

    contexts = retrieve_context(db, query)

    prompt = build_rag_prompt(query, contexts)

    response = await ollama_client.generate(prompt)

    return {
        "query": query,
        "answer": response,
        "contexts_used": len(contexts)
    }