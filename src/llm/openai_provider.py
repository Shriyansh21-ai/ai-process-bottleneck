"""
OpenAI LLM provider (MRPL Phase 1).

Preserves the existing OpenAI generation tier (the pre-Phase-1 router's Tier 1)
behind the common :class:`~src.llm.base.LLMProvider` contract. It is retained,
not removed: OpenAI remains a valid fallback in ``auto`` mode and an explicit
choice via ``LLM_PROVIDER=openai``. MRPL will later prioritise local inference,
but that policy is out of scope for Phase 1.

The client is constructed LAZILY. Building ``OpenAI()`` eagerly raises when
``OPENAI_API_KEY`` is unset, and the key is documented as OPTIONAL — so eager
construction would crash import on key-less deployments.
"""

import logging
from typing import Optional

from openai import OpenAI

from src.llm.base import LLMProvider, LLMProviderError
from src.llm.config import (
    get_llm_timeout,
    get_openai_api_key,
    get_openai_model,
    get_openai_temperature,
)

logger = logging.getLogger("llm.openai")


class OpenAIProvider(LLMProvider):
    """Provider backed by the OpenAI Chat Completions API."""

    name = "openai"

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
        client=None,
    ) -> None:
        super().__init__()
        self.model = model or get_openai_model()
        self.temperature = (
            temperature if temperature is not None else get_openai_temperature()
        )
        self.timeout = timeout if timeout is not None else get_llm_timeout()
        self._client = client  # injectable for tests
        self.last_model = self.model

    def is_available(self) -> bool:
        """True only when an API key is configured."""
        return get_openai_api_key() is not None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = get_openai_api_key()
            if not api_key:
                raise LLMProviderError("OPENAI_API_KEY is not set")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> str:
        use_model = model or self.model
        use_temperature = (
            temperature if temperature is not None else self.temperature
        )
        use_timeout = timeout if timeout is not None else self.timeout
        self.last_model = use_model

        try:
            response = self._get_client().chat.completions.create(
                model=use_model,
                temperature=use_temperature,
                timeout=use_timeout,
                messages=[{"role": "user", "content": prompt}],
            )
            logger.info("LLM tier=openai model=%s", use_model)
            return response.choices[0].message.content

        except LLMProviderError:
            raise
        except Exception as exc:
            # Never log at a level that could echo request content; the message
            # (provider/network error) is safe and key-free.
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc
