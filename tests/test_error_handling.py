"""
Milestone 4 — centralized, production-safe error handling tests.

Verifies:
  * unexpected exceptions -> 500 with a SAFE body (no stack trace / secrets /
    internal paths) and a request_id;
  * HTTPException(404) is preserved;
  * validation errors -> 422 with request_id;
  * successful responses are unchanged.
"""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.core.exceptions import (
    global_exception_handler,
    validation_exception_handler,
)
from src.core.middleware.request_id import RequestIDMiddleware


class _Body(BaseModel):
    x: int


SECRET = "sk-proj-TOPSECRETKEY"
PATH = "/etc/app/private/config.yaml"


def _app():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
    app.add_exception_handler(Exception, global_exception_handler)

    @app.get("/boom")
    def boom():
        raise RuntimeError(
            f"database password=hunter2 key={SECRET} file={PATH}"
        )

    @app.get("/missing")
    def missing():
        raise HTTPException(status_code=404, detail="thing not found")

    @app.get("/ok")
    def ok():
        return {"result": "fine"}

    @app.post("/validate")
    def validate(body: _Body):
        return {"x": body.x}

    return app


client = TestClient(_app(), raise_server_exceptions=False)


def test_unexpected_exception_returns_safe_500():
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "Internal server error"
    assert "request_id" in body
    assert body["request_id"]


def test_500_never_leaks_internals():
    text = client.get("/boom").text
    for leak in ("hunter2", SECRET, PATH, "RuntimeError", "Traceback"):
        assert leak not in text


def test_not_found_preserved():
    resp = client.get("/missing")
    assert resp.status_code == 404


def test_validation_error_returns_422():
    resp = client.post("/validate", json={"x": "not-an-int"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "Validation error"
    assert "request_id" in body


def test_success_unchanged():
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"result": "fine"}
