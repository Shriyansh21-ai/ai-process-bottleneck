"""
Role-based access helper (Milestone 6).

Updated to operate on the authenticated ``User`` ORM object. The only role we
model is ``admin`` (via ``User.is_admin``); ``require_role("admin")`` is
equivalent to :func:`src.core.auth.get_current_admin_user`.
"""

from fastapi import Depends, HTTPException, status

from src.core.auth import get_current_user
from src.db.models.user import User


def require_role(*allowed_roles: str):
    def role_checker(user: User = Depends(get_current_user)) -> User:
        role = "admin" if getattr(user, "is_admin", False) else "user"
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user
    return role_checker
