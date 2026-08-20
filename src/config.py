"""
Production configuration validation (Milestone 4).

This module intentionally does NOT use ``pydantic.BaseSettings`` (which moved to
the separate ``pydantic-settings`` package in Pydantic v2) so it stays import
safe and dependency-light. It reads the same environment variables the rest of
the application already relies on and validates them at startup.

Design goals:

  * distinguish REQUIRED config (missing -> hard error) from OPTIONAL /
    FALLBACK-supported config (missing -> warning, app still runs);
  * surface a clear, actionable error at startup instead of an obscure failure
    deep inside a request;
  * NEVER print or log secret values — only whether they are present.

``OPENAI_API_KEY`` is deliberately OPTIONAL: the LLM router (see
``src.genai.llm_router``) falls back to Ollama and finally to a safe offline
mode, so the application is designed to run without it.
"""

import logging
import os

logger = logging.getLogger("config")


class ConfigError(RuntimeError):
    """Raised when required production configuration is missing/invalid."""


# Variables that MUST be present for the app to function at all.
REQUIRED_KEYS = ("DATABASE_URL",)

# Variables that enable extra capability but have a working fallback. Their
# absence is reported as a warning, never an error.
FALLBACK_KEYS = ("OPENAI_API_KEY",)

# Purely optional tuning knobs (documented for completeness).
OPTIONAL_KEYS = (
    "OPENAI_MODEL",
    "OLLAMA_MODEL",
    "OLLAMA_BASE_URL",
    "ENV",
    "CORS_ALLOW_ORIGINS",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "RATE_LIMIT_ENABLED",
    "AUTH_RATE_LIMIT",
    "RUN_RATE_LIMIT",
)

# Keys required only in production (have a safe dev fallback otherwise).
PRODUCTION_REQUIRED_KEYS = ("JWT_SECRET_KEY",)

# Keys that hold secrets — never echo their values anywhere.
_SECRET_KEYS = {"OPENAI_API_KEY", "DATABASE_URL", "JWT_SECRET_KEY"}


def _present(key: str) -> bool:
    value = os.getenv(key)
    return value is not None and value.strip() != ""


def get_env() -> str:
    """Return the deployment environment (defaults to ``dev``).

    Reads ``ENV``; ``ENVIRONMENT`` is accepted as a backward-compatible alias.
    """
    value = os.getenv("ENV") or os.getenv("ENVIRONMENT") or "dev"
    return value.strip().lower()


def is_production() -> bool:
    return get_env() in {"prod", "production"}


def validate_config(raise_on_error: bool = True) -> dict:
    """
    Validate startup configuration.

    Returns a report dict::

        {
            "environment": "dev",
            "missing_required": [...],
            "missing_fallback": [...],
            "ok": bool,
        }

    When ``raise_on_error`` is True and a required key is missing, a
    :class:`ConfigError` is raised with a safe (secret-free) message.
    """

    missing_required = [k for k in REQUIRED_KEYS if not _present(k)]
    # JWT_SECRET_KEY is required only in production; add it to the hard-fail set
    # there so we never boot production with an insecure signing default.
    if is_production():
        missing_required += [
            k for k in PRODUCTION_REQUIRED_KEYS if not _present(k)
        ]
    missing_fallback = [k for k in FALLBACK_KEYS if not _present(k)]

    for key in missing_fallback:
        logger.warning(
            "Optional config '%s' is not set — running in fallback mode for "
            "this capability.",
            key,
        )

    report = {
        "environment": get_env(),
        "missing_required": missing_required,
        "missing_fallback": missing_fallback,
        "ok": not missing_required,
    }

    if missing_required:
        # Message names the keys only — never their (absent) values.
        message = (
            "Missing required configuration: "
            + ", ".join(missing_required)
            + ". Set these environment variables (see .env.example)."
        )
        logger.error(message)
        if raise_on_error:
            raise ConfigError(message)
    else:
        logger.info(
            "Configuration validated (env=%s, openai=%s).",
            report["environment"],
            "enabled" if _present("OPENAI_API_KEY") else "fallback",
        )

    return report


# ------------------------------------------------------------------
# JWT / authentication configuration (Milestone 6)
# ------------------------------------------------------------------

# A clearly-insecure dev fallback. It is ONLY used outside production; in
# production a missing JWT_SECRET_KEY is a hard error (see validate_config).
_DEV_JWT_SECRET = "dev-insecure-jwt-secret-change-me"


class AuthConfigError(RuntimeError):
    """Raised when authentication configuration is unsafe/missing."""


def get_jwt_secret() -> str:
    """
    Return the JWT signing secret.

    * production: ``JWT_SECRET_KEY`` MUST be set (no default) — raises otherwise.
    * dev/staging: falls back to a well-known INSECURE dev secret so local work
      is frictionless. Never rely on the fallback outside development.
    """
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if secret:
        return secret
    if is_production():
        raise AuthConfigError(
            "JWT_SECRET_KEY must be set in production. Refusing to start with "
            "an insecure default."
        )
    return _DEV_JWT_SECRET


def get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256").strip() or "HS256"


def get_access_token_expire_minutes() -> int:
    raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60").strip()
    try:
        value = int(raw)
        return value if value > 0 else 60
    except ValueError:
        return 60


def rate_limit_enabled() -> bool:
    """Rate limiting is on unless explicitly disabled (e.g. in tests)."""
    return os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() not in (
        "0", "false", "no", "off",
    )


def get_auth_rate_limit() -> str:
    """slowapi limit string for auth endpoints (login/register)."""
    return os.getenv("AUTH_RATE_LIMIT", "10/minute").strip() or "10/minute"


def get_run_rate_limit() -> str:
    """slowapi limit string for the agent execution endpoint."""
    return os.getenv("RUN_RATE_LIMIT", "30/minute").strip() or "30/minute"


def get_cors_origins() -> list:
    """
    Return the list of allowed CORS origins.

    Reads the comma-separated ``CORS_ALLOW_ORIGINS`` env var. Defaults to
    ``["*"]`` for developer convenience. In production set an explicit
    allow-list, e.g. ``CORS_ALLOW_ORIGINS=https://app.example.com``.

    Note: when the origin list is the wildcard ``*``, credentialed requests
    must be disabled (browsers reject ``Access-Control-Allow-Origin: *`` with
    credentials, and it is unsafe). :func:`cors_allow_credentials` enforces
    this pairing.
    """
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if raw in ("", "*"):
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def cors_allow_credentials() -> bool:
    """Allow credentials only when origins are explicitly allow-listed."""
    return get_cors_origins() != ["*"]


def safe_config_snapshot() -> dict:
    """
    Return a redacted view of configuration for diagnostics / health output.

    Secret values are reduced to a boolean ``present`` flag. This is safe to
    log or expose internally — it never contains credentials.
    """

    snapshot = {"environment": get_env()}
    for key in (
        REQUIRED_KEYS + PRODUCTION_REQUIRED_KEYS + FALLBACK_KEYS + OPTIONAL_KEYS
    ):
        if key in _SECRET_KEYS:
            snapshot[key] = {"present": _present(key)}
        else:
            snapshot[key] = os.getenv(key)
    return snapshot
