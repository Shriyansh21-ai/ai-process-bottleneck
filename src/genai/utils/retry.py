import asyncio
import time
from typing import Callable, Any

async def retry_async(
    fn: Callable,
    *,
    retries: int = 1,
    delay: float = 0.5,
    **kwargs
) -> Any:
    last_error = None

    for attempt in range(retries + 1):
        try:
            return await fn(**kwargs)
        except Exception as e:
            last_error = e
            if attempt < retries:
                await asyncio.sleep(delay)

    raise last_error
