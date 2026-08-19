"""
Optional administrative endpoints.

NOT wired into the application by default (Milestone 6: "do not expose
administrative APIs unnecessarily"). Kept as a correct, ready-to-mount example
that reuses the admin authorization dependency — admin status comes from the
authenticated user's DB record, never from client input.
"""

from fastapi import APIRouter, Depends

from src.core.auth import get_current_admin_user
from src.db.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health")
def system_health(user: User = Depends(get_current_admin_user)):
    return {"status": "OK", "checked_by": user.id}
