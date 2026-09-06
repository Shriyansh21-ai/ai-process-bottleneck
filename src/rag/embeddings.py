import os

from src.genai.model_loader import (
    get_embedding_model
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

client = None


def get_openai_client():

    global client

    if client is None and OPENAI_API_KEY:

        from openai import OpenAI

        client = OpenAI(
            api_key=OPENAI_API_KEY
        )

    return client


def _use_openai_embeddings() -> bool:
    """Decide whether to embed via OpenAI (1536-dim) or the local model (384-dim).

    The Qdrant ``documents`` collection is 384-dimensional (matching the local
    ``all-MiniLM-L6-v2`` model). OpenAI ``text-embedding-3-small`` returns 1536
    dimensions, which CANNOT be written into that collection. To keep the local
    / SIH demo safe we select the embedding backend explicitly:

      * ``EMBEDDINGS_PROVIDER=local``  -> always the 384-dim local model
      * ``EMBEDDINGS_PROVIDER=openai`` -> OpenAI (only sensible with a matching
        1536-dim collection; opt-in, never the default)
      * ``EMBEDDINGS_PROVIDER=auto`` / unset -> historical behaviour (OpenAI when
        a key is present) EXCEPT when ``LLM_PROVIDER`` selects an offline/local
        demo (``mock`` / ``ollama``), where we force the local model so the demo
        makes NO external embedding calls and never mismatches dimensions.

    This is a guard, not a redesign: it does not add a vector DB or a second RAG
    implementation, and production ``auto`` behaviour with OpenAI is unchanged.
    """
    provider = os.getenv("EMBEDDINGS_PROVIDER", "auto").strip().lower()

    if provider == "local":
        return False
    if provider == "openai":
        return True

    # auto: never make external embedding calls when running the offline/local
    # demo modes (mock/ollama) — those paths use the 384-dim local model.
    llm_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if llm_provider in ("mock", "ollama"):
        return False

    # Otherwise preserve the previous behaviour: use OpenAI iff a key is set.
    return get_openai_client() is not None


def embed_text(
    text: str
) -> list[float]:

    # =====================================
    # OPENAI PRIMARY (only when explicitly compatible/selected)
    # =====================================

    openai_client = get_openai_client() if _use_openai_embeddings() else None

    if openai_client is not None:

        try:

            response = openai_client.embeddings.create(

                model="text-embedding-3-small",

                input=text
            )

            return response.data[0].embedding

        except Exception as e:

            print(
                f"OpenAI embedding failed: {e}"
            )

    # =====================================
    # LOCAL FALLBACK
    # =====================================

    try:

        model = get_embedding_model()

        embedding = model.encode(text)

        return embedding.tolist()

    except Exception as e:

        print(
            f"Local embedding failed: {e}"
        )

        return []