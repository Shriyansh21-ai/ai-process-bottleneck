"""Request body-size guard (Milestone 8 hardening).

Rejects requests whose declared Content-Length exceeds a configurable maximum
before the body is buffered/parsed, protecting the service from oversized or
abusive payloads. The limit is generous by default (1 MiB) so legitimate agent
task descriptions, JSON bodies and small uploads pass; raise MAX_REQUEST_BYTES
for endpoints that must accept larger uploads.
"""

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def _max_bytes() -> int:
    try:
        value = int(os.getenv("MAX_REQUEST_BYTES", str(1 * 1024 * 1024)))
        return value if value > 0 else 1 * 1024 * 1024
    except (TypeError, ValueError):
        return 1 * 1024 * 1024


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with a Content-Length larger than the configured max."""

    def __init__(self, app):
        super().__init__(app)
        self.max_bytes = _max_bytes()

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Request body too large"},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid Content-Length header"},
                )
        return await call_next(request)
