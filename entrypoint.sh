#!/usr/bin/env bash
#
# Container entrypoint (Milestone 5).
#
#   1. wait for PostgreSQL to accept connections
#   2. apply Alembic migrations (fail hard if they fail — never serve traffic
#      against an incompatible schema)
#   3. exec the production ASGI server (uvicorn)
#
# `set -e` ensures any failing step aborts startup with a non-zero exit code.

set -euo pipefail

# ------------------------------------------------------------------
# config (all overridable via environment)
# ------------------------------------------------------------------
: "${APP_HOST:=0.0.0.0}"
: "${APP_PORT:=8000}"
# Single worker by default: each worker loads its own embedding model
# (hundreds of MB). Scale horizontally with container replicas, not workers.
: "${WEB_CONCURRENCY:=1}"
: "${DB_WAIT_TIMEOUT:=60}"
: "${RUN_MIGRATIONS:=1}"
# Which upstream peers may set X-Forwarded-For/-Proto. Defaults to loopback so
# clients CANNOT spoof their IP (rate-limit keying + logged IPs stay honest).
# Set this to your reverse proxy's IP/CIDR when deploying behind one; only use
# "*" if a trusted proxy is guaranteed to be the sole ingress.
: "${FORWARDED_ALLOW_IPS:=127.0.0.1}"

# ------------------------------------------------------------------
# 1. wait for the database
# ------------------------------------------------------------------
if [ -n "${DATABASE_URL:-}" ]; then
  echo "[entrypoint] waiting for database (timeout ${DB_WAIT_TIMEOUT}s)..."
  python - "$DB_WAIT_TIMEOUT" <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

timeout = int(sys.argv[1])
url = os.environ["DATABASE_URL"]
deadline = time.time() + timeout
last_err = None
while time.time() < deadline:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[entrypoint] database is ready")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        last_err = type(exc).__name__
        time.sleep(2)
print(f"[entrypoint] database not reachable after {timeout}s (last error: {last_err})",
      file=sys.stderr)
sys.exit(1)
PY
else
  echo "[entrypoint] WARNING: DATABASE_URL is not set" >&2
fi

# ------------------------------------------------------------------
# 2. run migrations (abort on failure)
# ------------------------------------------------------------------
if [ "${RUN_MIGRATIONS}" = "1" ]; then
  echo "[entrypoint] applying database migrations..."
  python -m alembic upgrade head
  echo "[entrypoint] migrations applied"
else
  echo "[entrypoint] RUN_MIGRATIONS=0 — skipping migrations"
fi

# ------------------------------------------------------------------
# 3. start the application
# ------------------------------------------------------------------
echo "[entrypoint] starting uvicorn on ${APP_HOST}:${APP_PORT} (workers=${WEB_CONCURRENCY})"
exec python -m uvicorn main:app \
  --host "${APP_HOST}" \
  --port "${APP_PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS}" \
  --timeout-keep-alive 30 \
  --timeout-graceful-shutdown 30
