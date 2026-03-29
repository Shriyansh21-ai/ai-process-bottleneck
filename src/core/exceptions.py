import logging
from fastapi import Request
from fastapi.responses import JSONResponse

async def global_exception_handler(request: Request, exc: Exception):
    logger = getattr(request.state, "logger", logging.getLogger("error"))
    logger.exception("Unhandled exception occurred")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "request_id": getattr(request.state, "request_id", None)
        }
    )
