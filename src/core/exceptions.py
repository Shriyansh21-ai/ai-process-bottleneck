"""
Centralized, production-safe exception handlers (Milestone 4).

* Unhandled exceptions -> HTTP 500 with a SAFE body (no stack trace, no
  secrets, no internal paths) plus the request_id for correlation.
* Validation errors      -> HTTP 422 with the field errors and the request_id.

FastAPI's built-in handlers already produce clean 404/400 (``HTTPException``)
responses; these handlers add request-id correlation and guarantee 500s never
leak internals.
"""

import logging

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("error")


def _request_id(request: Request):
    return getattr(request.state, "request_id", None)


async def global_exception_handler(request: Request, exc: Exception):
    log = getattr(request.state, "logger", logger)
    # Full detail is logged server-side only — never returned to the client.
    log.exception("Unhandled exception occurred")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": _request_id(request),
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": jsonable_encoder(exc.errors()),
            "request_id": _request_id(request),
        },
    )
