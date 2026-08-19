# syntax=docker/dockerfile:1
#
# Production image for the AI Process Bottleneck FastAPI backend (Milestone 5).
#
# Design notes:
#   * python:3.13-slim matches the verified dev interpreter (3.13.x).
#   * torch is installed CPU-only (no CUDA) to keep the image lean.
#   * dependencies are installed BEFORE the app is copied so code changes don't
#     bust the (expensive) pip layer.
#   * the app runs as a non-root user.
#   * NO .env / secrets are copied in — configuration is injected at runtime.

FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Keep the HuggingFace model cache inside the app dir (writable by appuser).
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# Minimal runtime OS packages. curl is used by the container HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# --- Python dependencies (cached layer) ---
RUN python -m pip install --upgrade pip
# CPU-only torch keeps the image dramatically smaller than the default CUDA build.
RUN pip install torch==2.11.0 --extra-index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Application code ---
COPY . .

# Create a non-root user and hand over app + cache ownership.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/.cache /app/logs /app/qdrant_data \
    && chown -R appuser:appuser /app

RUN chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

# Liveness at the image level (compose defines its own healthchecks too).
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
