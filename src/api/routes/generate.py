from fastapi import APIRouter
from pydantic import BaseModel

from src.genai.offline.ollama_client import OllamaClient

router = APIRouter()

ollama = OllamaClient()


class PromptRequest(BaseModel):
    prompt: str


@router.post("/generate")
async def generate_text(request: PromptRequest):

    response = await ollama.generate(request.prompt)

    return {
        "response": response
    }