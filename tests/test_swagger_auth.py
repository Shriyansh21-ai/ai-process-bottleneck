"""
Milestone 6 — Swagger / OpenAPI authentication wiring (Phase 20).

Verifies the OpenAPI schema exposes the OAuth2 password-flow security scheme
(so Swagger's "Authorize" button works) and that protected endpoints reference
it, while the auth endpoints themselves are documented.
"""

from fastapi import FastAPI

from src.api.auth import router as auth_router
from src.api.routes.agent_runs import router as agent_runs_router


def _openapi():
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(agent_runs_router)
    return app.openapi()


def test_oauth2_security_scheme_present():
    schema = _openapi()
    schemes = schema.get("components", {}).get("securitySchemes", {})
    # OAuth2PasswordBearer registers an OAuth2 scheme with a password flow.
    assert any(s.get("type") == "oauth2" for s in schemes.values())
    oauth = next(s for s in schemes.values() if s.get("type") == "oauth2")
    assert "password" in oauth.get("flows", {})
    assert oauth["flows"]["password"]["tokenUrl"].endswith("auth/login")


def test_protected_route_declares_security():
    schema = _openapi()
    get_runs = schema["paths"]["/runs"]["get"]
    # A security requirement means Swagger shows the lock + sends the token.
    assert get_runs.get("security"), "GET /runs should require authentication"


def test_auth_endpoints_documented():
    schema = _openapi()
    paths = schema["paths"]
    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/auth/me" in paths
    # 401 documented on the protected profile endpoint.
    assert "401" in paths["/auth/me"]["get"]["responses"]
