"""
MRPL demo environment check (Phase 5).

A small, read-only preflight that tells a fresh developer whether this machine
can run the offline SIH demo (LLM_PROVIDER=mock, local embeddings, no Ollama /
OpenAI / internet / GPU). It is NOT a second application: it performs cheap
checks and prints a single verdict.

It checks, as far as practical:

    * Required Python dependencies
    * Database connectivity
    * Qdrant (embedded vector store)
    * LLM provider          (expected: mock)
    * Embedding provider     (expected: local)
    * OCR availability       (advisory - the demo PDF is text-based)

Output ends with either::

    DEMO ENVIRONMENT READY
    DEMO ENVIRONMENT NOT READY

SECURITY: this script never prints secrets. Connection strings, API keys and
passwords are never echoed - only presence / reachability and the URL scheme.

Usage:
    python scripts/check_demo_environment.py

Exit code 0 when ready, 1 when not ready.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# When invoked as ``python scripts/check_demo_environment.py`` Python puts the
# script's own directory on sys.path (not the repo root), so ``import src.*``
# would fail. Add the repo root explicitly so the check works from anywhere.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Load .env so DATABASE_URL / LLM_PROVIDER / EMBEDDINGS_PROVIDER are visible,
# exactly like the application does at startup.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a hard dependency in practice
    pass


OK = "OK"
WARN = "WARN"
FAIL = "FAIL"


@dataclass
class Check:
    name: str
    status: str
    detail: str


# Core runtime dependencies the offline demo needs (import name -> pip package).
_REQUIRED_DEPS = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "pydantic": "pydantic",
    "qdrant_client": "qdrant-client",
    "sentence_transformers": "sentence-transformers",
    "pypdf": "pypdf",
    "reportlab": "reportlab",
}


def check_dependencies() -> Check:
    import importlib.util

    missing = [
        pip_name
        for mod, pip_name in _REQUIRED_DEPS.items()
        if importlib.util.find_spec(mod) is None
    ]
    if missing:
        return Check(
            "Required Python dependencies",
            FAIL,
            f"missing: {', '.join(missing)} - run: pip install -r requirements.txt",
        )
    return Check(
        "Required Python dependencies",
        OK,
        f"all {len(_REQUIRED_DEPS)} present",
    )


def check_llm_provider() -> Check:
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if provider == "mock":
        return Check("LLM provider", OK, "mock (offline)")
    if not provider:
        return Check(
            "LLM provider",
            WARN,
            "LLM_PROVIDER is unset - set LLM_PROVIDER=mock for the offline demo",
        )
    return Check(
        "LLM provider",
        WARN,
        f"{provider} - the offline demo on this machine expects LLM_PROVIDER=mock",
    )


def check_embeddings_provider() -> Check:
    provider = (os.getenv("EMBEDDINGS_PROVIDER") or "").strip().lower()
    if provider in ("", "local"):
        detail = "local" if provider else "unset (defaults to local)"
        return Check("Embedding provider", OK, detail)
    return Check(
        "Embedding provider",
        WARN,
        f"{provider} - the offline demo expects local embeddings",
    )


def check_ocr() -> Check:
    """OCR is advisory: the demo PDF is text-based, so OCR is not required."""
    try:
        from src.documents.ocr import TesseractOCREngine

        if TesseractOCREngine().is_available():
            return Check("OCR (Tesseract)", OK, "available")
        return Check(
            "OCR (Tesseract)",
            WARN,
            "unavailable - not required for the text-based demo PDF",
        )
    except Exception as exc:  # noqa: BLE001
        return Check(
            "OCR (Tesseract)",
            WARN,
            f"unavailable ({type(exc).__name__}) - not required for the demo",
        )


def _url_scheme(url: str) -> str:
    """Return only the scheme of a URL (never the credentials/host)."""
    return url.split("://", 1)[0] if "://" in url else "unknown"


def check_database() -> Check:
    url = os.getenv("DATABASE_URL")
    if not url:
        return Check(
            "Database",
            FAIL,
            "DATABASE_URL is not set (copy .env.example to .env)",
        )
    scheme = _url_scheme(url)
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return Check("Database", OK, f"connected ({scheme})")
    except Exception as exc:  # noqa: BLE001 - surface type only, never the URL
        return Check(
            "Database",
            FAIL,
            f"cannot connect ({scheme}): {type(exc).__name__} - "
            f"start the database (docker compose up postgres)",
        )


def check_qdrant() -> Check:
    try:
        from src.db.qdrant import client

        client.get_collections()
        return Check("Qdrant (embedded)", OK, "reachable")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "already accessed" in msg or "lock" in msg or "storage" in msg:
            return Check(
                "Qdrant (embedded)",
                WARN,
                "store is locked - likely already in use by a running backend",
            )
        return Check(
            "Qdrant (embedded)",
            FAIL,
            f"unavailable: {type(exc).__name__}",
        )


def run_checks() -> list[Check]:
    return [
        check_dependencies(),
        check_database(),
        check_qdrant(),
        check_llm_provider(),
        check_embeddings_provider(),
        check_ocr(),
    ]


def is_ready(checks: list[Check]) -> bool:
    return not any(c.status == FAIL for c in checks)


def format_report(checks: list[Check]) -> str:
    width = max(len(c.name) for c in checks)
    lines = ["", "MRPL DEMO ENVIRONMENT CHECK", "=" * 40]
    for c in checks:
        lines.append(f"  [{c.status:<4}] {c.name.ljust(width)}  {c.detail}")
    lines.append("=" * 40)
    if is_ready(checks):
        lines.append("DEMO ENVIRONMENT READY")
    else:
        lines.append("DEMO ENVIRONMENT NOT READY")
        failed = [c.name for c in checks if c.status == FAIL]
        lines.append(f"  Blocking: {', '.join(failed)}")
    return "\n".join(lines)


def main() -> int:
    checks = run_checks()
    print(format_report(checks))
    return 0 if is_ready(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
