"""
Ollama LLM provider (MRPL Phase 1).

Wraps the local Ollama server. This preserves the behaviour of the pre-Phase-1
router's Ollama tier but makes everything configurable instead of hardcoded:

  * model      -> OLLAMA_MODEL       (was hardcoded ``"llama3"``)
  * base URL   -> OLLAMA_BASE_URL    (was ignored entirely)
  * timeout    -> LLM_TIMEOUT_SECONDS
  * temperature-> OLLAMA_TEMPERATURE

The ``ollama`` package is optional (it is intentionally NOT in requirements.txt);
it is imported behind a try/except so importing this module never fails on a
machine without it. When absent, :meth:`generate` raises
:class:`~src.llm.base.LLMProviderError` and the router falls back.

IMPORTANT: This module is import-safe and configuration-only. Actual Ollama
inference is validated on a capable machine, not on the constrained dev box.
"""

import logging
from typing import Optional

try:
    import ollama
except ImportError:  # pragma: no cover - exercised only where ollama is absent
    ollama = None

from src.llm.base import LLMProvider, LLMProviderError
from src.llm.config import (
    get_llm_timeout,
    get_ollama_base_url,
    get_ollama_model,
    get_ollama_temperature,
)

logger = logging.getLogger("llm.ollama")


class OllamaProvider(LLMProvider):
    """Provider backed by a local Ollama server."""

    name = "ollama"

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__()
        # Resolve from configuration once at construction; callers may still
        # override per-call via generate(...) kwargs.
        self.model = model or get_ollama_model()
        self.base_url = base_url or get_ollama_base_url()
        self.temperature = (
            temperature if temperature is not None else get_ollama_temperature()
        )
        self.timeout = timeout if timeout is not None else get_llm_timeout()
        self.last_model = self.model

    def is_available(self) -> bool:
        """True only if the optional ``ollama`` package is importable."""
        return ollama is not None

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> str:
        if ollama is None:
            raise LLMProviderError(
                "ollama package is not installed; cannot reach local Ollama"
            )

        use_model = model or self.model
        use_temperature = (
            temperature if temperature is not None else self.temperature
        )
        use_timeout = timeout if timeout is not None else self.timeout
        self.last_model = use_model

        messages = [{"role": "user", "content": prompt}]
        options = {"temperature": use_temperature}

        try:
            # Prefer an explicit client so base URL + timeout are honoured. Some
            # older ollama builds have a different Client signature; fall back to
            # the module-level chat (never worse than the pre-Phase-1 behaviour).
            try:
                client = ollama.Client(host=self.base_url, timeout=use_timeout)
                response = client.chat(
                    model=use_model, messages=messages, options=options
                )
            except TypeError:
                response = ollama.chat(
                    model=use_model, messages=messages, options=options
                )

            logger.info("LLM tier=ollama model=%s", use_model)
            return response["message"]["content"]

        except LLMProviderError:
            raise
        except Exception as exc:
            # Wrap any transport/model error so the router applies its fallback.
            # The message (network/model error) is safe and key-free.
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc
