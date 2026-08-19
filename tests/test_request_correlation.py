"""
Milestone 4 — request/agent correlation (X-Request-ID) tests.
"""

import uuid

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.core.middleware.request_id import HEADER_NAME, RequestIDMiddleware


def _app_with_state():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    def ping(request: Request):
        return {"request_id": getattr(request.state, "request_id", None)}

    return app


client = TestClient(_app_with_state())


def test_request_id_generated_and_returned():
    resp = client.get("/ping")
    assert resp.status_code == 200
    header_id = resp.headers.get(HEADER_NAME)
    assert header_id
    # Body id and header id must match (correlation).
    assert resp.json()["request_id"] == header_id
    # Generated ids are valid UUID4 strings.
    uuid.UUID(header_id)


def test_incoming_request_id_is_honoured():
    incoming = "trace-abc-123"
    resp = client.get("/ping", headers={HEADER_NAME: incoming})
    assert resp.headers.get(HEADER_NAME) == incoming
    assert resp.json()["request_id"] == incoming


def test_invalid_incoming_request_id_is_replaced():
    junk = "x" * 500  # exceeds the max inbound length
    resp = client.get("/ping", headers={HEADER_NAME: junk})
    returned = resp.headers.get(HEADER_NAME)
    assert returned != junk
    uuid.UUID(returned)  # a fresh UUID was generated instead
