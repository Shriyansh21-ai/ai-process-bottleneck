from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from core.rate_limiter import limiter
from api.agent import router as agent_router
from api.auth import router as auth_router

from core.logging import setup_logging
from core.middleware.request_id import RequestIDMiddleware
from core.middleware.timing import TimingMiddleware
from core.exceptions import global_exception_handler

setup_logging()

app = FastAPI(title="Agentic Process Intelligence")

# Attach limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(auth_router, prefix="/api")
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)

app.add_exception_handler(Exception, global_exception_handler)

# Routes
app.include_router(agent_router, prefix="/api")
