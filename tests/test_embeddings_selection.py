"""
MRPL Phase 3 — embedding backend selection tests.

Guards the local/SIH demo against sending 1536-dim OpenAI embeddings into the
384-dim Qdrant collection. No network / OpenAI / model download required: the
local model is stubbed so we only exercise the selection logic.
"""

import pytest

import src.rag.embeddings as emb


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("EMBEDDINGS_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


def test_explicit_local_never_uses_openai(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "local")
    assert emb._use_openai_embeddings() is False


def test_explicit_openai_selects_openai(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "openai")
    assert emb._use_openai_embeddings() is True


def test_mock_llm_forces_local_embeddings(monkeypatch):
    # Even if an OpenAI key is present, mock mode must NOT call OpenAI.
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-used")
    assert emb._use_openai_embeddings() is False


def test_ollama_llm_forces_local_embeddings(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert emb._use_openai_embeddings() is False


def test_auto_without_key_uses_local(monkeypatch):
    monkeypatch.setattr(emb, "get_openai_client", lambda: None)
    assert emb._use_openai_embeddings() is False


def test_auto_with_key_uses_openai(monkeypatch):
    monkeypatch.setattr(emb, "get_openai_client", lambda: object())
    assert emb._use_openai_embeddings() is True


def test_embed_text_uses_local_model_in_mock_mode(monkeypatch):
    """In mock mode embed_text must go through the local 384-dim model."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    calls = {"openai": 0}

    def _no_openai():
        calls["openai"] += 1
        return object()

    class _FakeVec:
        def tolist(self):
            return [0.0] * 384

    class _FakeModel:
        def encode(self, text):
            return _FakeVec()

    monkeypatch.setattr(emb, "get_openai_client", _no_openai)
    monkeypatch.setattr(emb, "get_embedding_model", lambda: _FakeModel())

    vec = emb.embed_text("hello")
    assert len(vec) == 384
    # OpenAI embedding path must not have been taken.
    assert calls["openai"] == 0
