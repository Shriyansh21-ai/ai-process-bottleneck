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


def embed_text(
    text: str
) -> list[float]:

    # =====================================
    # OPENAI PRIMARY
    # =====================================

    openai_client = get_openai_client()

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