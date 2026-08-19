"""
Authentication dependencies (Milestone 6).

Provides the reusable FastAPI dependency chain that turns a Bearer token into an
authenticated, active ``User`` ORM object:

    get_current_user          -> validates token, loads user, checks active
    get_current_active_user   -> alias (kept explicit for readability)
    get_current_admin_user    -> additionally requires is_admin

All failures return a safe HTTP 401/403 — internal JWT errors are never leaked.
Authentication lives at the API/security layer only; the agent core is untouched.
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.core.security import decode_access_token, JWTError
from src.db.models.user import User
from src.db.session import get_db

logger = logging.getLogger("auth")

# tokenUrl drives Swagger's "Authorize" (OAuth2 password flow) button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> User:
    """Resolve and validate the authenticated user from a Bearer token."""
    try:
        payload = decode_access_token(token)
    except JWTError:
        # Covers invalid signature, expired, and malformed tokens uniformly.
        raise _UNAUTHORIZED

    subject = payload.get("sub")
    if subject is None:
        raise _UNAUTHORIZED

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _UNAUTHORIZED

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise _UNAUTHORIZED

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Explicit active-user dependency (get_current_user already enforces it)."""
    return user


def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    """Require an authenticated user with administrative privilege."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privilege required",
        )
    return user
