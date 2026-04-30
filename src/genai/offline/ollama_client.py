import httpx
import asyncio


class OllamaClient:

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model

    async def generate(self, prompt: str, timeout: int = 20) -> str:
        """
        Generate response from Ollama
        """

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )

                response.raise_for_status()
                data = response.json()

                return data.get("response", "").strip()

        except Exception as e:
            print("❌ Ollama Error:", str(e))
            raise e