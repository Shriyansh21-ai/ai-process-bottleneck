import ollama

class OllamaClient:

    def __init__(self, model="tinyllama"):
        self.model = model

    async def generate(self, prompt: str) -> str:
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response["message"]["content"]

        except Exception as e:
            print("❌ Ollama error:", str(e))
            return None