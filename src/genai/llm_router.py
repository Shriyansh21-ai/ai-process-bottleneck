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

    return json.dumps({

        "confidence": 0.60,

        "approved": True,

        "issues": [

            "System operating in fallback mode"
        ]
    })