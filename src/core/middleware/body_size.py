"""Request body-size guard (Milestone 8 hardening; MRPL Phase 3 upload sizing).

Rejects requests whose declared Content-Length exceeds a configurable maximum
before the body is buffered/parsed, protecting the service from oversized or
abusive payloads.

Two limits are enforced:

  * ``MAX_REQUEST_BYTES`` (default 1 MiB) — the strict global limit for ordinary
    JSON/API traffic (agent task descriptions, auth, etc.).
  * ``UPLOAD_MAX_REQUEST_BYTES`` (default 20 MiB) — a larger limit applied ONLY
    to file-upload endpoints (``UPLOAD_PATH_PREFIXES``, default ``/inspection``).

Before Phase 3 the single 1 MiB global limit ran ahead of the 20 MiB
document-size limit, so realistic scanned inspection reports were rejected at the
middleware before ever reaching the endpoint. Rather than weaken the global
limit for every route, we raise it ONLY for the upload paths — a small, bounded,
configurable change. The upper bound is still enforced (uploads are not
unbounded), and the document layer's own ``DOCUMENT_MAX_BYTES`` check runs after.
"""

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_DEFAULT_MAX = 1 * 1024 * 1024          # 1 MiB — ordinary requests
_DEFAULT_UPLOAD_MAX = 20 * 1024 * 1024  # 20 MiB — file uploads


def _int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def _max_bytes() -> int:
    return _int_env("MAX_REQUEST_BYTES", _DEFAULT_MAX)


def _upload_max_bytes() -> int:
    return _int_env("UPLOAD_MAX_REQUEST_BYTES", _DEFAULT_UPLOAD_MAX)


def _upload_prefixes() -> tuple:
    """Path prefixes that receive the larger upload limit."""
    raw = os.getenv("UPLOAD_PATH_PREFIXES", "/inspection").strip()
    prefixes = tuple(p.strip() for p in raw.split(",") if p.strip())
    return prefixes or ("/inspection",)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with a Content-Length larger than the configured max.

    Upload paths get the (larger) upload limit; everything else gets the strict
    global limit.
    """

    def __init__(self, app):
        super().__init__(app)
        self.max_bytes = _max_bytes()
        self.upload_max_bytes = _upload_max_bytes()
        self.upload_prefixes = _upload_prefixes()

    def _limit_for(self, path: str) -> int:
        if any(path.startswith(prefix) for prefix in self.upload_prefixes):
            return self.upload_max_bytes
        return self.max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self._limit_for(request.url.path):
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
