import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        logger = logging.getLogger("request")
        adapter = logging.LoggerAdapter(logger, {"request_id": request_id})
        request.state.logger = adapter

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
