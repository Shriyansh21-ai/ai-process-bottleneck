import os
import json
import logging
try:

    import ollama

except ImportError:

    ollama = None

from openai import OpenAI


logger = logging.getLogger("llm_router")


def _llm_timeout() -> float:
    """Per-call wall-clock bound (seconds) for a remote LLM request.

    Without an explicit timeout a hung/slow provider stalls the whole /run
    request: the planner and verifier LLM calls happen OUTSIDE the controller's
    execution-phase ``asyncio.wait_for`` bound, so this is the only guard on
    them. Configurable via ``LLM_TIMEOUT_SECONDS`` (default 60).
    """
    try:
        value = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
        return value if value > 0 else 60.0
    except (TypeError, ValueError):
        return 60.0


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
# MAIN GENERATION FUNCTION
# ==========================================

def generate_response(

    prompt: str,

    model: str = "gpt-4o-mini"
):

    # ==========================================
    # TIER 1 — OPENAI
    # ==========================================

    if openai_client:

        try:

            response = openai_client.chat.completions.create(

                model=model,

                temperature=0,

                timeout=_llm_timeout(),

                messages=[

                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            logger.info("LLM tier=openai model=%s", model)

            _record_llm_meta(model, "openai")

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

    # Fail CLOSED and mark the payload itself as degraded. This function is the
    # single entry used by BOTH the planner and the verifier, so an offline
    # fallback must never masquerade as a real, approved verdict. The planner
    # still detects this (it sniffs for the "confidence" key and repairs to a
    # safe static plan); the verifier now correctly treats it as not-approved.
    # `degraded=True` lets any downstream consumer branch on the degraded state.
    return json.dumps({

        "degraded": True,

        "confidence": 0.0,

        "approved": False,

        "issues": [

            "System operating in offline fallback mode — output is not verified"
        ]
    })