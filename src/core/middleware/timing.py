import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Response-Time-ms"] = str(duration)

        logger = getattr(request.state, "logger", None)
        if logger:
            logger.info(f"request completed in {duration} ms")

        return response
