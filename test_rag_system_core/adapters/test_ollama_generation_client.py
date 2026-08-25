from __future__ import annotations

import pytest

from rag_system_core import OllamaGenerationClient


class RecordingOllamaGenerateClient:
    def __init__(self, captured: dict[str, object]) -> None:
        self._captured = captured

    def chat(self, *, model: str, messages: list[dict[str, str]]):
        self._captured["model"] = model
        self._captured["messages"] = messages
        return {"message": {"content": "cloud answer"}}

def test_ollama_generation_client_uses_injected_client() -> None:
    captured: dict[str, object] = {}
    injected_client = RecordingOllamaGenerateClient(captured)

    client = OllamaGenerationClient(client=injected_client, model="gpt-oss:20b")
    response = client.generate("Summarize alpha")

    assert response == "cloud answer"
    assert captured == {
        "model": "gpt-oss:20b",
        "messages": [{"role": "user", "content": "Summarize alpha"}],
    }


def test_ollama_generation_client_wraps_transport_errors() -> None:
    class FakeClient:
        def chat(self, *, model: str, messages: list[dict[str, str]]):
            del model, messages
            raise ConnectionError("boom")

    client = OllamaGenerationClient(client=FakeClient(), model="gpt-oss:20b")

    with pytest.raises(RuntimeError, match="Failed to generate response from Ollama") as exc_info:
        client.generate("alpha")

    assert isinstance(exc_info.value.__cause__, ConnectionError)


def test_ollama_generation_client_rejects_malformed_response() -> None:
    class FakeClient:
        def chat(self, *, model: str, messages: list[dict[str, str]]):
            del model, messages
            return {}

    client = OllamaGenerationClient(client=FakeClient(), model="gpt-oss:20b")

    with pytest.raises(RuntimeError, match="Ollama returned a malformed generation response") as exc_info:
        client.generate("alpha")

    assert isinstance(exc_info.value.__cause__, KeyError)
