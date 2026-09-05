"""
Provider selection (MRPL Phase 1).

Turns the ``LLM_PROVIDER`` configuration into the ordered list of providers the
router should try. The router (``src.genai.llm_router``) iterates this list and,
if every provider fails, applies its fail-closed offline fallback.

Selection semantics (see :func:`src.llm.config.get_llm_provider_name`):

  * ``mock``   -> [MockLLMProvider]                         (never fails)
  * ``ollama`` -> [OllamaProvider]                          (offline on failure)
  * ``openai`` -> [OpenAIProvider]                          (offline on failure)
  * ``auto``   -> [OpenAIProvider?, OllamaProvider?]        (legacy chain)

In ``auto`` mode only *available* tiers are included: OpenAI when an API key is
set, Ollama when the ``ollama`` package is importable — exactly the pre-Phase-1
behaviour, now expressed declaratively.
"""

from typing import List, Optional

from src.llm.base import LLMProvider
from src.llm.config import get_llm_provider_name
from src.llm.mock_provider import MockLLMProvider
from src.llm.ollama_provider import OllamaProvider
from src.llm.openai_provider import OpenAIProvider


def get_provider(name: str) -> LLMProvider:
    """Construct a single provider by explicit name.

    ``name`` must be one of ``mock`` / ``ollama`` / ``openai``. Raises
    ``ValueError`` for anything else (``auto`` is a chain, not a single
    provider — use :func:`select_providers`).
    """
    key = (name or "").strip().lower()
    if key == "mock":
        return MockLLMProvider()
    if key == "ollama":
        return OllamaProvider()
    if key == "openai":
        return OpenAIProvider()
    raise ValueError(f"Unknown LLM provider: {name!r}")


def select_providers(selection: Optional[str] = None) -> List[LLMProvider]:
    """Return the ordered providers to attempt for the current configuration.

    ``selection`` defaults to :func:`get_llm_provider_name`. The result is never
    empty for explicit selectors; for ``auto`` it may be empty (no tier
    available), in which case the router goes straight to offline fallback.
    """
    selection = (selection or get_llm_provider_name()).strip().lower()

    if selection == "mock":
        return [MockLLMProvider()]
    if selection == "ollama":
        return [OllamaProvider()]
    if selection == "openai":
        return [OpenAIProvider()]

    # auto: preserve the legacy OpenAI -> Ollama chain, skipping tiers that are
    # obviously not configured so we don't waste a round-trip on them.
    chain: List[LLMProvider] = []
    openai_provider = OpenAIProvider()
    if openai_provider.is_available():
        chain.append(openai_provider)
    ollama_provider = OllamaProvider()
    if ollama_provider.is_available():
        chain.append(ollama_provider)
    return chain
