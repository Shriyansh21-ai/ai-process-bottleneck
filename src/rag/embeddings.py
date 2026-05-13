import os

from sentence_transformers import SentenceTransformer


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

local_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


if OPENAI_API_KEY:

    from openai import OpenAI

    client = OpenAI(
        api_key=OPENAI_API_KEY
    )

else:

    client = None


def embed_text(text: str) -> list[float]:

    # =========================
    # OPENAI PRIMARY
    # =========================

    if client is not None:

        try:

            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )

            return response.data[0].embedding

        except Exception as e:

            print(f"OpenAI embedding failed: {e}")

    # =========================
    # LOCAL FALLBACK
    # =========================

    embedding = local_model.encode(text)

    return embedding.tolist()