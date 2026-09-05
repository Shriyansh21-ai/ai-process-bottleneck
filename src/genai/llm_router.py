import os
import json
import logging
try:

    import ollama

except ImportError:

    ollama = None

from openai import OpenAI

from src.llm.config import (
    get_llm_provider_name,
    get_llm_timeout,
    get_openai_model,
)
from src.llm.base import LLMProviderError
from src.llm.factory import select_providers


logger = logging.getLogger("llm_router")


def _llm_timeout() -> float:
    """Per-call wall-clock bound (seconds) for a remote LLM request.

    Without an explicit timeout a hung/slow provider stalls the whole /run
    request: the planner and verifier LLM calls happen OUTSIDE the controller's
    execution-phase ``asyncio.wait_for`` bound, so this is the only guard on
    them. Configurable via ``LLM_TIMEOUT_SECONDS`` (default 60).

    Delegates to :func:`src.llm.config.get_llm_timeout` so the timeout is
    resolved identically for the legacy chain and the provider abstraction.
    """
    return get_llm_timeout()


# ==========================================
# OPENAI CLIENT
# ==========================================

openai_client = None

# ==========================================
# LIGHTWEIGHT LLM TELEMETRY (additive)
# ==========================================
# Records the model/tier used by the most recent generate_response() call so
# the run-summary layer can report it. This never alters generation behavior
# or the generate_response() signature/return value.

LAST_LLM_META = {"model": None, "mode": None}


def _record_llm_meta(model, mode):
    LAST_LLM_META["model"] = model
    LAST_LLM_META["mode"] = mode


def get_last_llm_meta():
    """Return a copy of the last-used LLM model/mode ({'model','mode'})."""
    return dict(LAST_LLM_META)


if os.getenv("OPENAI_API_KEY"):

    try:

        openai_client = OpenAI(
            api_key=os.getenv(
                "OPENAI_API_KEY"
            )
        )

    except Exception:

        openai_client = None


# ==========================================
# OFFLINE SAFE FALLBACK
# ==========================================

def _offline_fallback() -> str:
    """Return the fail-CLOSED degraded payload used when no LLM tier is usable.

    This function is the single generation entry used by BOTH the planner and
    the verifier, so an offline fallback must never masquerade as a real,
    approved verdict. The planner detects this (it sniffs for the "confidence"
    key and repairs to a safe static plan); the verifier treats it as
    not-approved. ``degraded=True`` lets any downstream consumer branch on the
    degraded state.
    """
    return json.dumps({

        "degraded": True,

        "confidence": 0.0,

        "approved": False,

        "issues": [

            "System operating in offline fallback mode — output is not verified"
        ]
    })


# ==========================================
# MAIN GENERATION FUNCTION
# ==========================================

def generate_response(
    prompt: str,
    model: str = None,
):
    """Generate a completion for ``prompt`` using the configured provider.

    Selection is driven by ``LLM_PROVIDER`` (see :mod:`src.llm.config`):

      * ``mock`` / ``ollama`` / ``openai`` -> the clean provider abstraction
        in :mod:`src.llm`, with a fail-closed offline fallback;
      * ``auto`` (the default when unset) -> the legacy OpenAI -> Ollama ->
        offline chain kept below, byte-for-byte, so pre-Phase-1 production
        behaviour is preserved.

    The return contract (a string; a degraded JSON sentinel when offline) and
    the LLM telemetry (:func:`get_last_llm_meta`) are unchanged.
    """

    selection = get_llm_provider_name()

    if selection == "auto":
        return _generate_auto(prompt, model)

    # ==========================================
    # EXPLICIT PROVIDER SELECTION (mock / ollama / openai)
    # ==========================================
    # Delegate to the provider abstraction. Each provider raises
    # LLMProviderError when it cannot serve the request; we then fail closed to
    # the offline sentinel, exactly like the auto chain.

    for provider in select_providers(selection):

        try:

            text = provider.generate(prompt, model=model)

            logger.info(
                "LLM tier=%s model=%s", provider.name, provider.last_model
            )

            _record_llm_meta(provider.last_model, provider.name)

            return text

        except LLMProviderError as e:

            logger.warning(
                "%s tier failed, falling back: %s", provider.name, str(e)
            )

    logger.warning("All LLM tiers unavailable — using offline safe fallback")

    _record_llm_meta(None, "offline")

    return _offline_fallback()


def _generate_auto(prompt: str, model: str = None):
    """Legacy tiered chain: OpenAI -> Ollama -> offline safe fallback.

    Preserved verbatim (module globals ``openai_client`` / ``ollama`` and all)
    so existing behaviour — and the tests that monkeypatch those globals —
    continue to work unchanged when ``LLM_PROVIDER`` is not set.
    """

    # ==========================================
    # TIER 1 — OPENAI
    # ==========================================

    if openai_client:

        try:

            openai_model = model or get_openai_model()

            response = openai_client.chat.completions.create(

                model=openai_model,

                temperature=0,

                timeout=_llm_timeout(),

                messages=[

                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            logger.info("LLM tier=openai model=%s", openai_model)

            _record_llm_meta(openai_model, "openai")

            return response.choices[0].message.content

        except Exception as e:

            # Never log the exception at a level that could echo request content;
            # the message (provider/network error) is safe and key-free.
            logger.warning("OpenAI tier failed, falling back: %s", str(e))

    # ==========================================
    # TIER 2 — OLLAMA
    # ==========================================

    if ollama is not None:

        try:

            # Bound the Ollama call so a hung local server cannot stall /run.
            # ollama.Client forwards timeout to its underlying httpx client; if
            # this build's signature differs we fall back to the module-level
            # chat (never worse than the previous unbounded behavior).
            messages = [{"role": "user", "content": prompt}]
            try:
                client = ollama.Client(timeout=_llm_timeout())
                response = client.chat(model="llama3", messages=messages)
            except TypeError:
                response = ollama.chat(model="llama3", messages=messages)

            logger.info("LLM tier=ollama model=llama3")

            _record_llm_meta("llama3", "ollama")

            return response["message"]["content"]

        except Exception as e:

            logger.warning("Ollama tier failed, falling back: %s", str(e))
    # ==========================================
    # TIER 3 — OFFLINE SAFE FALLBACK
    # ==========================================

    logger.warning("All LLM tiers unavailable — using offline safe fallback")

    _record_llm_meta(None, "offline")

    return _offline_fallback()
