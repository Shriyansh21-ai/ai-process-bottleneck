from src.genai.offline.ollama_client import OllamaClient

ollama_client = OllamaClient()


async def generate_response(prompt: str):

    response = await ollama_client.generate(prompt)

    return response