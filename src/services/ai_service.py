from src.rag.retriever import retrieve_context
from src.rag.prompt_builder import build_rag_prompt

from src.genai.openai.openai_client import OpenAIClient
from src.genai.offline.ollama_client import OllamaClient

from src.services.memory_service import (
    save_message,
    get_recent_messages
)


openai_client = OpenAIClient()
ollama_client = OllamaClient()


async def generate_rag_response(
    db,
    query: str
):

    # ==========================================
    # RETRIEVE RELEVANT CONTEXT
    # ==========================================

    contexts = retrieve_context(
        db,
        query
    )

    if not contexts:

        return {

            "answer": "No relevant information found.",

            "sources": []
        }

    # ==========================================
    # LOAD CONVERSATION MEMORY
    # ==========================================

    memories = get_recent_messages(
        db,
        limit=10
    )

    memory_context = "\n".join([
        f"{m.role}: {m.message}"
        for m in reversed(memories)
    ])

    # ==========================================
    # BUILD FINAL PROMPT
    # ==========================================

    rag_prompt = build_rag_prompt(
        query,
        contexts
    )

    final_prompt = f"""
Conversation History:
{memory_context}

{rag_prompt}
"""

    # ==========================================
    # SAVE USER MESSAGE
    # ==========================================

    save_message(
        db,
        role="user",
        message=query
    )

    # ==========================================
    # GENERATE RESPONSE
    # ==========================================

    try:

        response = await openai_client.generate(
            final_prompt
        )

    except Exception:

        response = await ollama_client.generate(
            final_prompt
        )

    # ==========================================
    # SAVE ASSISTANT RESPONSE
    # ==========================================

    save_message(
        db,
        role="assistant",
        message=response
    )

    # ==========================================
    # RETURN RESPONSE
    # ==========================================

    return {

    "answer": response,

    "sources": [

        {
            "content": c["content"][:200],
            "section": c["section"],
            "page": c["page_number"]
        }

        for c in contexts
    ]
}