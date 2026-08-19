"""
Milestone 6 — authentication tests (register / login / me / token validation).
"""

from src.core.security import create_access_token, verify_password
from tests.conftest import TestingSessionLocal
from src.db.models.user import User


# ------------------------------------------------------------------
# REGISTRATION
# ------------------------------------------------------------------

def test_register_success(auth_client):
    resp = auth_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["is_active"] is True
    assert body["is_admin"] is False
    # Password / hash must never appear in the response.
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email(auth_client):
    payload = {"email": "dup@example.com", "password": "Password123!"}
    assert auth_client.post("/auth/register", json=payload).status_code == 201
    resp = auth_client.post("/auth/register", json=payload)
    assert resp.status_code == 409


def test_register_invalid_email(auth_client):
    resp = auth_client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "Password123!"},
    )
    assert resp.status_code == 422


def test_register_short_password(auth_client):
    resp = auth_client.post(
        "/auth/register",
        json={"email": "shorty@example.com", "password": "short"},
    )
    assert resp.status_code == 422


def test_register_hashes_password(auth_client):
    auth_client.post(
        "/auth/register",
        json={"email": "hash@example.com", "password": "Password123!"},
    )
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "hash@example.com").first()
        assert user is not None
        # Stored value is a bcrypt hash, never the plaintext.
        assert user.hashed_password != "Password123!"
        assert user.hashed_password.startswith("$2")
        assert verify_password("Password123!", user.hashed_password)
    finally:
        db.close()


def test_register_ignores_is_admin_from_client(auth_client):
    # Mass-assignment guard: client cannot self-promote to admin.
    resp = auth_client.post(
        "/auth/register",
        json={
            "email": "sneaky@example.com",
            "password": "Password123!",
            "is_admin": True,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["is_admin"] is False


# ------------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------------

def _register(auth_client, email, password="Password123!"):
    auth_client.post("/auth/register", json={"email": email, "password": password})


def test_login_success(auth_client):
    _register(auth_client, "login@example.com")
    resp = auth_client.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(auth_client):
    _register(auth_client, "wp@example.com")
    resp = auth_client.post(
        "/auth/login",
        data={"username": "wp@example.com", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(auth_client):
    resp = auth_client.post(
        "/auth/login",
        data={"username": "ghost@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 401


def test_login_message_does_not_reveal_existence(auth_client):
    # Same generic message for unknown user and wrong password (no enumeration).
    _register(auth_client, "enum@example.com")
    wrong_pw = auth_client.post(
        "/auth/login",
        data={"username": "enum@example.com", "password": "Nope!"},
    ).json()["detail"]
    unknown = auth_client.post(
        "/auth/login",
        data={"username": "missing@example.com", "password": "Nope!"},
    ).json()["detail"]
    assert wrong_pw == unknown


def test_login_inactive_user(auth_client):
    _register(auth_client, "inactive@example.com")
    db = TestingSessionLocal()
    try:
        u = db.query(User).filter(User.email == "inactive@example.com").first()
        u.is_active = False
        db.commit()
    finally:
        db.close()
    resp = auth_client.post(
        "/auth/login",
        data={"username": "inactive@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 401


# ------------------------------------------------------------------
# /auth/me + token validation
# ------------------------------------------------------------------

def _auth_header(auth_client, email):
    _register(auth_client, email)
    token = auth_client.post(
        "/auth/login", data={"username": email, "password": "Password123!"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_me_authenticated(auth_client):
    headers = _auth_header(auth_client, "me@example.com")
    resp = auth_client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"
    assert "hashed_password" not in resp.json()


def test_me_missing_token(auth_client):
    resp = auth_client.get("/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token(auth_client):
    resp = auth_client.get(
        "/auth/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert resp.status_code == 401


def test_me_malformed_authorization_header(auth_client):
    resp = auth_client.get(
        "/auth/me", headers={"Authorization": "Token abc"}
    )
    assert resp.status_code == 401


def test_me_expired_token(auth_client):
    _register(auth_client, "expired@example.com")
    db = TestingSessionLocal()
    try:
        uid = db.query(User).filter(
            User.email == "expired@example.com"
        ).first().id
    finally:
        db.close()
    expired = create_access_token({"sub": str(uid)}, expires_minutes=-1)
    resp = auth_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert resp.status_code == 401


def test_me_token_for_deleted_user(auth_client):
    # A validly-signed token whose subject no longer exists must be rejected.
    token = create_access_token({"sub": "999999"})
    resp = auth_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
