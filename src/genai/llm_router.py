import os
import json
try:

    import ollama

except ImportError:

    ollama = None

from openai import OpenAI


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

                messages=[

                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            print("✅ Using OpenAI")

            _record_llm_meta(model, "openai")

            return response.choices[0].message.content

        except Exception as e:

            print(
                f"⚠️ OpenAI failed: {str(e)}"
            )

    # ==========================================
    # TIER 2 — OLLAMA
    # ==========================================

    if ollama is not None:

        try:

            response = ollama.chat(

                model="llama3",

                messages=[

                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            print("✅ Using Ollama")

            _record_llm_meta("llama3", "ollama")

            return response["message"]["content"]

        except Exception as e:

            print(
                f"⚠️ Ollama failed: {str(e)}"
            )
    # ==========================================
    # TIER 3 — OFFLINE SAFE FALLBACK
    # ==========================================

    print(
        "⚠️ Falling back to offline mode"
    )

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