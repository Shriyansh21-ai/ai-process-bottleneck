"""
Request correlation middleware (Milestone 4).

Assigns every request a ``request_id`` that flows through logs and back to the
client via the ``X-Request-ID`` response header, enabling end-to-end tracing:

    request_id -> agent_run_id -> step_execution / step_id

A well-formed inbound ``X-Request-ID`` is honoured (so an upstream gateway /
client can propagate its own id); otherwise a fresh UUID4 is generated.
"""

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

HEADER_NAME = "X-Request-ID"
_MAX_INBOUND_LEN = 128


def _coerce_request_id(raw: str | None) -> str:
    """Return a safe request id: the inbound one if valid, else a new UUID4."""
    if raw:
        candidate = raw.strip()
        # Keep it bounded and printable so it can't be used to inject log noise.
        if 0 < len(candidate) <= _MAX_INBOUND_LEN and candidate.isprintable():
            return candidate
    return str(uuid.uuid4())


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = _coerce_request_id(request.headers.get(HEADER_NAME))
        request.state.request_id = request_id

        logger = logging.getLogger("request")
        adapter = logging.LoggerAdapter(logger, {"request_id": request_id})
        request.state.logger = adapter

        try:
            response: Response = await call_next(request)
        except Exception:
            # Let the registered exception handlers build the response, but make
            # sure the id is still available to them via request.state.
            raise

        response.headers[HEADER_NAME] = request_id
        return response
