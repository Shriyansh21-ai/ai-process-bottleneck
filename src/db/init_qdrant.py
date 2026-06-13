from qdrant_client.models import (
    VectorParams,
    Distance
)

from src.db.qdrant import client


def init_qdrant():

    collections = client.get_collections().collections

    existing = [
        c.name for c in collections
    ]

    if "documents" not in existing:

        client.create_collection(

            collection_name="documents",

            vectors_config=VectorParams(

                size=384,

                distance=Distance.COSINE
            )
        )

        print(
            "Qdrant collection created"
        )

    else:

        print(
            "Qdrant collection already exists"
        )