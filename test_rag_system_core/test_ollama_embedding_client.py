from __future__ import annotations

import pytest

import rag_system_core.core as core_module
from rag_system_core import OllamaEmbeddingClient


class RecordingOllamaClient:
    def __init__(self, captured: dict[str, object], *, host: str, timeout: float) -> None:
        captured["host"] = host
        captured["timeout"] = timeout
        self._captured = captured

    def embed(self, *, model: str, input: list[str]):
        self._captured["model"] = model
        self._captured["input"] = input
        embeddings_by_text = {
            "alpha": [1.0, 0.0, 0.5],
            "beta": [0.0, 1.0, 0.5],
        }
        return {"embeddings": [embeddings_by_text[text] for text in input]}


def test_ollama_embedding_client_requires_model_when_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_EMBED__MODEL", raising=False)

    with pytest.raises(
        ValueError,
        match="Ollama embed model must be provided either as 'model' or OLLAMA_EMBED__MODEL",
    ):
        OllamaEmbeddingClient(base_url="http://ollama", timeout=7.0)


def test_ollama_embedding_client_reads_configuration_from_environment(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            self._delegate = RecordingOllamaClient(captured, host=host, timeout=timeout)

        def embed(self, *, model: str, input: list[str]):
            return self._delegate.embed(model=model, input=input)

    monkeypatch.setenv("OLLAMA_EMBED__BASE_URL", "http://embed-ollama")
    monkeypatch.setenv("OLLAMA_EMBED__MODEL", "bge-m3")
    monkeypatch.setenv("OLLAMA_EMBED__TIMEOUT", "12.5")
    monkeypatch.setenv("OLLAMA_GENERATE__BASE_URL", "https://generate-ollama")
    monkeypatch.setenv("OLLAMA_GENERATE__TIMEOUT", "99.0")
    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)

    client = OllamaEmbeddingClient()
    vectors = client.embed(["alpha"])

    assert vectors == [[1.0, 0.0, 0.5]]
    assert captured == {
        "host": "http://embed-ollama",
        "timeout": 12.5,
        "model": "bge-m3",
        "input": ["alpha"],
    }


def test_ollama_embedding_client_uses_ollama_package_client(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            self._delegate = RecordingOllamaClient(captured, host=host, timeout=timeout)

        def embed(self, *, model: str, input: list[str]):
            return self._delegate.embed(model=model, input=input)

    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)

    client = OllamaEmbeddingClient(model="bge-m3", base_url="http://ollama", timeout=7.0)
    vectors = client.embed(["alpha", "beta"])

    assert vectors == [[1.0, 0.0, 0.5], [0.0, 1.0, 0.5]]
    assert captured == {
        "host": "http://ollama",
        "timeout": 7.0,
        "model": "bge-m3",
        "input": ["alpha", "beta"],
    }


def test_ollama_embedding_client_wraps_ollama_transport_errors(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            del host, timeout

        def embed(self, *, model: str, input: list[str]):
            del model, input
            raise ConnectionError("boom")

    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)
    client = OllamaEmbeddingClient(model="bge-m3", base_url="http://ollama", timeout=7.0)

    with pytest.raises(RuntimeError, match="Failed to fetch embeddings from Ollama") as exc_info:
        client.embed(["alpha"])

    assert isinstance(exc_info.value.__cause__, ConnectionError)


def test_ollama_embedding_client_rejects_malformed_embeddings_response(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            del host, timeout

        def embed(self, *, model: str, input: list[str]):
            del model, input
            return {}

    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)
    client = OllamaEmbeddingClient(model="bge-m3", base_url="http://ollama", timeout=7.0)

    with pytest.raises(RuntimeError, match="Ollama returned a malformed embeddings response") as exc_info:
        client.embed(["alpha"])

    assert isinstance(exc_info.value.__cause__, KeyError)
