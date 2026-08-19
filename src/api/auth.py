"""
Authentication endpoints (Milestone 6).

    POST /auth/register  — create an account
    POST /auth/login     — obtain a JWT access token (OAuth2 password flow)
    GET  /auth/me        — the authenticated user's profile

Backed by the ``users`` table. Passwords are bcrypt-hashed and never returned.
Login uses a generic error and does not reveal whether an email exists.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError

from src.core.auth import get_current_active_user
from src.core.rate_limiter import limiter
from src.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from src.config import get_auth_rate_limit
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.auth import Token, UserCreate, UserResponse

logger = logging.getLogger("auth")

router = APIRouter(prefix="/auth", tags=["Auth"])

_AUTH_LIMIT = get_auth_rate_limit()

# A real bcrypt hash of a random value, verified against on unknown-email logins
# so the response time is similar to a real password check (reduces the timing
# signal an attacker could use to enumerate accounts).
_DUMMY_HASH = hash_password("timing-equalizer-not-a-real-password")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation error"},
    },
)
@limiter.limit(_AUTH_LIMIT)
def register(request: Request, payload: UserCreate, db=Depends(get_db)):
    email = payload.email.strip().lower()

    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_admin=False,  # never honour is_admin from client input
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Handles the race where two registrations collide on the unique email.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    db.refresh(user)
    # UserResponse (from_attributes) strips hashed_password.
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login and obtain an access token",
    responses={401: {"description": "Invalid credentials"}},
)
@limiter.limit(_AUTH_LIMIT)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db),
):
    # OAuth2 form uses "username"; we treat it as the email.
    email = form_data.username.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    # Generic failure for both unknown-email and wrong-password to avoid
    # account enumeration. Always run verify_password to reduce timing signal.
    if user is None:
        verify_password(form_data.password, _DUMMY_HASH)
        raise _invalid_credentials()
    if not verify_password(form_data.password, user.hashed_password):
        raise _invalid_credentials()
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user",
    responses={401: {"description": "Not authenticated"}},
)
def me(current_user: User = Depends(get_current_active_user)):
    return current_user


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
