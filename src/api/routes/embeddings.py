from fastapi import APIRouter
from pydantic import BaseModel

from src.genai.embeddings import embed_text

router = APIRouter()


class EmbeddingRequest(BaseModel):
    text: str


@router.post("/embed")
async def create_embedding(request: EmbeddingRequest):

    embedding = embed_text(request.text)

    return {
        "embedding_dimension": len(embedding),
        "embedding": embedding
    }