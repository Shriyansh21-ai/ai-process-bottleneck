import aiohttp

from src.genai.config.model_config import (
    OLLAMA_MODEL,
    OLLAMA_BASE_URL
)


class OllamaClient:

    async def generate(
        self,
        prompt: str,
        model: str = OLLAMA_MODEL
    ):

        url = f"{OLLAMA_BASE_URL}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        timeout = aiohttp.ClientTimeout(total=120)

        try:

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                async with session.post(
                    url,
                    json=payload
                ) as response:

                    if response.status != 200:

                        error_text = await response.text()

                        raise Exception(
                            f"Ollama API Error: {error_text}"
                        )

                    data = await response.json()

                    return data.get(
                        "response",
                        ""
                    )

        except Exception as e:

            raise Exception(
                f"Ollama connection failed: {str(e)}"
            )