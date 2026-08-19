"""
Core security primitives (password hashing + JWT).

Milestone 6 consolidation:
  * The JWT secret / algorithm / expiry now come from environment config
    (see ``src.config``) — no secret is hardcoded, and production has no
    insecure default.
  * ``create_access_token`` and ``decode_access_token`` are the single source of
    truth used by both the auth endpoints and the auth dependency, so tokens are
    always signed and verified with the SAME key.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from jose import jwt, JWTError
from passlib.context import CryptContext

from src.config import (
    get_access_token_expire_minutes,
    get_jwt_algorithm,
    get_jwt_secret,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------------
# API keys (existing helper, unchanged)
# ------------------------------------------------------------------

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


# ------------------------------------------------------------------
# Passwords
# ------------------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    # Never raises on malformed hashes — treat as a failed verification.
    try:
        return pwd_context.verify(password, hashed)
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------
# JWT
# ------------------------------------------------------------------

def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    """Sign a JWT. Payload should carry only minimal claims (e.g. ``sub``)."""
    to_encode = data.copy()
    minutes = (
        expires_minutes
        if expires_minutes is not None
        else get_access_token_expire_minutes()
    )
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, get_jwt_secret(), algorithm=get_jwt_algorithm()
    )


def decode_access_token(token: str) -> dict:
    """
    Verify signature + expiry and return the claims.

    Raises :class:`jose.JWTError` on any invalid/expired/malformed token — the
    caller translates that into a safe HTTP 401 without leaking internals.
    """
    return jwt.decode(
        token, get_jwt_secret(), algorithms=[get_jwt_algorithm()]
    )


__all__ = [
    "generate_api_key",
    "hash_api_key",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "JWTError",
]
