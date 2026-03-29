# genai/routing/fallback_executor.py

import asyncio
import random
from typing import Callable, Dict, List


class ModelExecutionError(Exception):
    pass


class FallbackExecutor:
    """
    Executes model calls with:
    - Retry
    - Multi-model fallback
    - Exponential backoff
    """

    def __init__(self):
        self.max_retries = 2
        self.base_backoff = 0.5  # seconds

    async def execute(
        self,
        model_chain: List[str],
        agent_callable: Callable,
        **kwargs
    ) -> Dict:
        """
        model_chain: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
        agent_callable: function that accepts model=...
        """

        last_error = None

        for model in model_chain:

            for attempt in range(self.max_retries + 1):
                try:
                    return await agent_callable(model=model, **kwargs)

                except Exception as e:
                    last_error = e

                    # exponential backoff
                    delay = self.base_backoff * (2 ** attempt)
                    delay += random.uniform(0, 0.2)

                    await asyncio.sleep(delay)

            # If retries exhausted → try next model

        raise ModelExecutionError(
            f"All models failed. Last error: {str(last_error)}"
        )