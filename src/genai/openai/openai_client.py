from openai import AsyncOpenAI
import os


class OpenAIClient:

    def __init__(self):

        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

    async def generate(
        self,
        prompt: str,
        model: str = "gpt-4o-mini"
    ):

        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI financial intelligence assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        return response.choices[0].message.content
    
    async def stream_generate(
    self,
    prompt: str,
    model: str = "gpt-4o-mini"
):

        stream = await self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI financial intelligence assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            stream=True
        )

        async for chunk in stream:

            delta = chunk.choices[0].delta.content

            if delta:

                yield delta