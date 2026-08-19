"""
Shared slowapi rate limiter (Milestone 6 hardening).

Limits are applied per-route via ``@limiter.limit(...)`` decorators (auth and
/run endpoints). The whole mechanism can be switched off with
``RATE_LIMIT_ENABLED=false`` — useful for local dev and the test suite.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import rate_limit_enabled

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],  # generous global fallback
    enabled=rate_limit_enabled(),
)
