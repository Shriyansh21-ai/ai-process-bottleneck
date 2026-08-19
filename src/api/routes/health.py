"""
Health & readiness endpoints (Milestone 4).

* ``GET /health``       — liveness: the process is up and serving requests.
* ``GET /health/ready`` — readiness: critical dependencies (the database and
  required configuration) are reachable/valid. Returns HTTP 503 when a critical
  dependency is unavailable so orchestrators can gate traffic.

No credentials, connection strings or stack traces are ever exposed.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, Response, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.config import REQUIRED_KEYS, _present
from src.db.session import get_db

logger = logging.getLogger("health")

router = APIRouter(tags=["Health"])


# ------------------------------------------------------------------
# response models (surface cleanly in Swagger / OpenAPI)
# ------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = Field("healthy", description="Liveness status")
    message: str = Field(..., description="Human-readable liveness message")


class ReadinessResponse(BaseModel):
    status: str = Field(..., description="'ready' or 'not_ready'")
    checks: Dict[str, str] = Field(
        ..., description="Per-dependency status (available/unavailable/ok)"
    )


# ------------------------------------------------------------------
# liveness
# ------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 while the application process is alive.",
)
async def health_check():
    return {
        "status": "healthy",
        "message": "AI Process Bottleneck Backend Running",
    }


# ------------------------------------------------------------------
# readiness
# ------------------------------------------------------------------

def _check_database(db) -> bool:
    """Return True if a trivial query succeeds against the database."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        # Never surface the raw DB error (may contain the connection string).
        logger.warning("Readiness check: database is unavailable", exc_info=False)
        return False


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Checks critical dependencies (database connectivity and required "
        "configuration). Returns 200 when ready, 503 when a critical "
        "dependency is unavailable."
    ),
    responses={
        200: {"description": "All critical dependencies are available"},
        503: {
            "description": "A critical dependency is unavailable",
            "model": ReadinessResponse,
        },
    },
)
async def readiness_check(response: Response, db=Depends(get_db)):
    checks: Dict[str, str] = {}

    db_ok = _check_database(db)
    checks["database"] = "available" if db_ok else "unavailable"

    missing_required = [k for k in REQUIRED_KEYS if not _present(k)]
    config_ok = not missing_required
    checks["configuration"] = "ok" if config_ok else "incomplete"

    ready = db_ok and config_ok
    if not ready:
        response.status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "checks": checks}

    return {"status": "ready", "checks": checks}
