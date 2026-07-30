from __future__ import annotations

import pytest

from rag_system_core import OllamaEmbeddingClient


class RecordingOllamaClient:
    def __init__(self, captured: dict[str, object]) -> None:
        self._captured = captured

    def embed(self, *, model: str, input: list[str]):
        self._captured["model"] = model
        self._captured["input"] = input
        embeddings_by_text = {
            "alpha": [1.0, 0.0, 0.5],
            "beta": [0.0, 1.0, 0.5],
        }
        return {"embeddings": [embeddings_by_text[text] for text in input]}

    def check(self) -> None:
        self._captured["checked"] = True


def test_ollama_embedding_client_uses_injected_client() -> None:
    captured: dict[str, object] = {}
    injected_client = RecordingOllamaClient(captured)

    client = OllamaEmbeddingClient(client=injected_client, model="bge-m3")
    vectors = client.embed(["alpha", "beta"])

    assert vectors == [[1.0, 0.0, 0.5], [0.0, 1.0, 0.5]]
    assert captured == {
        "model": "bge-m3",
        "input": ["alpha", "beta"],
    }


def test_ollama_embedding_client_wraps_ollama_transport_errors() -> None:
    class FakeClient:
        def embed(self, *, model: str, input: list[str]):
            del model, input
            raise ConnectionError("boom")

    client = OllamaEmbeddingClient(client=FakeClient(), model="bge-m3")

    with pytest.raises(RuntimeError, match="Failed to fetch embeddings from Ollama") as exc_info:
        client.embed(["alpha"])

    assert isinstance(exc_info.value.__cause__, ConnectionError)


def test_ollama_embedding_client_rejects_malformed_embeddings_response() -> None:
    class FakeClient:
        def embed(self, *, model: str, input: list[str]):
            del model, input
            return {}

    client = OllamaEmbeddingClient(client=FakeClient(), model="bge-m3")

    with pytest.raises(RuntimeError, match="Ollama returned a malformed embeddings response") as exc_info:
        client.embed(["alpha"])

    assert isinstance(exc_info.value.__cause__, KeyError)


def test_ollama_embedding_client_delegates_health_checks() -> None:
    captured: dict[str, object] = {}
    client = OllamaEmbeddingClient(client=RecordingOllamaClient(captured), model="bge-m3")

    client.check()

    assert captured["checked"] is True
