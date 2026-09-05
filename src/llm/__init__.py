"""
LLM provider abstraction package (MRPL Phase 1).

Public surface used by the rest of Neuroflow::

    from src.llm import LLMProvider, get_provider, select_providers
    from src.llm import MockLLMProvider, OllamaProvider, OpenAIProvider

The agent pipeline does not import these directly — it calls
``src.genai.llm_router.generate_response``, which delegates here. This package
is the clean seam that lets a mock model and Ollama be swapped with no change to
PlannerAgent / ToolExecutor / VerifierAgent.
"""

from src.llm.base import LLMProvider, LLMProviderError
from src.llm.config import get_llm_provider_name
from src.llm.factory import get_provider, select_providers
from src.llm.mock_provider import MockLLMProvider
from src.llm.ollama_provider import OllamaProvider
from src.llm.openai_provider import OpenAIProvider

__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "MockLLMProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "get_provider",
    "select_providers",
    "get_llm_provider_name",
]
