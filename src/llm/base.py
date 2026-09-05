"""
LLM provider abstraction (MRPL Phase 1).

This module defines the single, narrow contract that the rest of Neuroflow
(Stack A: ``src/agent/*``) depends on for text generation. The existing agent
pipeline calls into :func:`src.genai.llm_router.generate_response`, which now
delegates to a concrete :class:`LLMProvider` selected from configuration.

Design goals:

  * the planner / verifier / executor must NOT care whether a response came
    from a real Ollama model, OpenAI, or a deterministic mock;
  * providers are cheap to construct and hold only configuration;
  * a provider that cannot serve a request raises :class:`LLMProviderError`
    so the router can apply its fail-closed offline fallback.

This is intentionally minimal — Phase 1 establishes the abstraction only; it
does not implement model routing, streaming, or the full sovereignty stack.
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMProviderError(RuntimeError):
    """Raised when a provider cannot fulfil a generation request.

    The router treats this as "this tier is unavailable" and either falls
    through to the next tier (auto mode) or to the safe offline fallback.
    """


class LLMProvider(ABC):
    """Common contract for every LLM backend.

    Concrete providers set :attr:`name` (a short, stable mode identifier used
    for telemetry) and, after each :meth:`generate` call, record the model
    actually used in :attr:`last_model` so the run-summary layer can report it.
    """

    #: Short, stable identifier for telemetry/logging, e.g. ``"mock"``.
    name: str = "base"

    def __init__(self) -> None:
        # The concrete model used by the most recent generate() call. Providers
        # update this so llm_router can record accurate LLM telemetry without
        # changing the public generate_response() contract.
        self.last_model: Optional[str] = None

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Return the model's text completion for ``prompt``.

        Keyword arguments override the provider's configured defaults for this
        single call. Implementations MUST raise :class:`LLMProviderError` (not
        return a sentinel) when they cannot serve the request, so the router
        can apply its fallback policy.
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """Best-effort check that this provider *could* serve a request.

        Used by the auto-selection chain to skip tiers that are obviously not
        configured (e.g. no API key, ``ollama`` package absent). Defaults to
        ``True``; a ``True`` result is not a guarantee — :meth:`generate` may
        still raise :class:`LLMProviderError`.
        """
        return True
