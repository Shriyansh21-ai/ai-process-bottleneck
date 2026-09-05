"""
LLM provider configuration (MRPL Phase 1).

All provider selection and tuning is driven by environment variables, matching
the existing project convention (see :mod:`src.config` and ``.env.example`` —
this module does NOT introduce a settings framework). Every value has a safe
default so the application boots without any LLM configuration at all.

Selector (:func:`get_llm_provider_name`)::

    LLM_PROVIDER=mock     -> deterministic MockLLMProvider (offline dev/tests)
    LLM_PROVIDER=ollama   -> local Ollama inference
    LLM_PROVIDER=openai   -> OpenAI API
    LLM_PROVIDER=auto     -> legacy chain: OpenAI (if keyed) -> Ollama -> offline
    (unset)               -> auto  (preserves pre-Phase-1 production behaviour)

NOTE: ``DEFAULT_PROVIDER`` (used only by the dead Stack B ``src/genai/engine``)
is intentionally NOT read here. Stack A never honoured it, so wiring it in would
silently change behaviour for existing deployments.
"""

import os
from typing import Optional


# Valid explicit selector values. Anything else falls back to "auto".
_VALID_SELECTORS = {"mock", "ollama", "openai", "auto"}

# When LLM_PROVIDER is unset we preserve the historical tiered-fallback
# behaviour so existing production deployments are unaffected.
_DEFAULT_SELECTOR = "auto"


def get_llm_provider_name() -> str:
    """Return the configured provider selector (lowercased).

    An unset or unrecognised value resolves to ``"auto"`` — the backward
    compatible OpenAI -> Ollama -> offline chain.
    """
    raw = os.getenv("LLM_PROVIDER", "").strip().lower()
    if raw in _VALID_SELECTORS:
        return raw
    return _DEFAULT_SELECTOR


def get_llm_timeout(default: float = 60.0) -> float:
    """Per-call wall-clock bound (seconds) for a remote LLM request.

    Shared by the OpenAI and Ollama providers. Configurable via
    ``LLM_TIMEOUT_SECONDS`` (default 60). Guards the planner/verifier LLM calls,
    which run outside the controller's execution-phase timeout, so a hung
    provider cannot stall a ``/run`` indefinitely.
    """
    try:
        value = float(os.getenv("LLM_TIMEOUT_SECONDS", str(default)))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


# ------------------------------------------------------------------
# Ollama settings
# ------------------------------------------------------------------

def get_ollama_model() -> str:
    """Ollama model name. Comes from config — never hardcoded at call sites.

    Defaults to ``llama3`` to preserve the exact model the pre-Phase-1 router
    used when ``OLLAMA_MODEL`` is unset. Deployments (and the friend's capable
    machine) set ``OLLAMA_MODEL`` explicitly, e.g. ``phi3:mini``.
    """
    return os.getenv("OLLAMA_MODEL", "llama3").strip() or "llama3"


def get_ollama_base_url() -> str:
    """Ollama server base URL (``OLLAMA_BASE_URL``, default localhost:11434)."""
    return (
        os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        or "http://localhost:11434"
    )


def get_ollama_temperature(default: float = 0.0) -> float:
    """Sampling temperature for Ollama (``OLLAMA_TEMPERATURE``, default 0.0).

    Kept at 0 by default for deterministic planner/verifier output.
    """
    try:
        return float(os.getenv("OLLAMA_TEMPERATURE", str(default)))
    except (TypeError, ValueError):
        return default


# ------------------------------------------------------------------
# OpenAI settings
# ------------------------------------------------------------------

def get_openai_model() -> str:
    """OpenAI model name (``OPENAI_MODEL``, default ``gpt-4o-mini``)."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def get_openai_api_key() -> Optional[str]:
    """OpenAI API key (``OPENAI_API_KEY``) or ``None`` when unset/blank."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return key or None


def get_openai_temperature(default: float = 0.0) -> float:
    """Sampling temperature for OpenAI (``OPENAI_TEMPERATURE``, default 0.0)."""
    try:
        return float(os.getenv("OPENAI_TEMPERATURE", str(default)))
    except (TypeError, ValueError):
        return default
