import os

# ============================================================
# DEFAULT PROVIDER
# ============================================================

DEFAULT_PROVIDER = os.getenv(
    "DEFAULT_PROVIDER",
    "ollama"
)

# ============================================================
# OLLAMA
# ============================================================

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "phi3:mini"
)

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

# ============================================================
# OPENAI
# ============================================================

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini"
)