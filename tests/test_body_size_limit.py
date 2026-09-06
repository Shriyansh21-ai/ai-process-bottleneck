"""
MRPL Phase 3 — body-size limit configuration tests.

Verifies that upload endpoints (``/inspection``) accept larger bodies than the
strict global limit, that the global limit still protects ordinary routes, and
that both limits stay bounded and configurable.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.middleware.body_size import (
    BodySizeLimitMiddleware,
    _max_bytes,
    _upload_max_bytes,
    _upload_prefixes,
)


def _app():
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware)

    @app.post("/inspection/analyze")
    async def analyze():
        return {"ok": True}

    @app.post("/other")
    async def other():
        return {"ok": True}

    return app


@pytest.fixture
def small_limits(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BYTES", "100")
    monkeypatch.setenv("UPLOAD_MAX_REQUEST_BYTES", "1000")
    monkeypatch.setenv("UPLOAD_PATH_PREFIXES", "/inspection")


def test_defaults_are_sane():
    # Ordinary requests: 1 MiB; uploads: 20 MiB; upload prefix: /inspection.
    assert _max_bytes() == 1 * 1024 * 1024
    assert _upload_max_bytes() == 20 * 1024 * 1024
    assert "/inspection" in _upload_prefixes()


def test_upload_path_accepts_body_above_global_limit(small_limits):
    with TestClient(_app()) as client:
        resp = client.post("/inspection/analyze", content=b"x" * 500)  # >100, <1000
    assert resp.status_code == 200


def test_non_upload_path_rejects_body_above_global_limit(small_limits):
    with TestClient(_app()) as client:
        resp = client.post("/other", content=b"x" * 500)  # >100 global limit
    assert resp.status_code == 413


def test_upload_path_still_bounded(small_limits):
    with TestClient(_app()) as client:
        resp = client.post("/inspection/analyze", content=b"x" * 2000)  # >1000
    assert resp.status_code == 413


def test_non_upload_small_body_passes(small_limits):
    with TestClient(_app()) as client:
        resp = client.post("/other", content=b"x" * 10)
    assert resp.status_code == 200


def test_invalid_content_length_rejected(small_limits):
    with TestClient(_app()) as client:
        resp = client.post(
            "/other", content=b"x", headers={"content-length": "not-a-number"}
        )
    assert resp.status_code == 400
