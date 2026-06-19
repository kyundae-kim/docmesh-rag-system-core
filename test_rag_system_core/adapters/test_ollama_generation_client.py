from __future__ import annotations

import pytest

import rag_system_core.core as core_module
from rag_system_core import OllamaGenerationClient


class RecordingOllamaGenerateClient:
    def __init__(self, captured: dict[str, object], *, host: str, headers: dict[str, str], timeout: float) -> None:
        captured["host"] = host
        captured["headers"] = headers
        captured["timeout"] = timeout
        self._captured = captured

    def chat(self, *, model: str, messages: list[dict[str, str]]):
        self._captured["model"] = model
        self._captured["messages"] = messages
        return {"message": {"content": "cloud answer"}}


def test_ollama_generation_client_requires_api_key_when_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_GENERATE__API_KEY", raising=False)

    with pytest.raises(
        ValueError,
        match="Ollama API key must be provided either as 'api_key' or OLLAMA_GENERATE__API_KEY",
    ):
        OllamaGenerationClient(model="gpt-oss:20b")


def test_ollama_generation_client_requires_model_when_not_configured(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_GENERATE__MODEL", "")

    with pytest.raises(
        ValueError,
        match="Ollama generation model must be provided either as 'model' or OLLAMA_GENERATE__MODEL",
    ):
        OllamaGenerationClient(api_key="test-api-key")


def test_ollama_generation_client_reads_cloud_configuration_from_environment(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, host: str, headers: dict[str, str], timeout: float) -> None:
            self._delegate = RecordingOllamaGenerateClient(captured, host=host, headers=headers, timeout=timeout)

        def chat(self, *, model: str, messages: list[dict[str, str]]):
            return self._delegate.chat(model=model, messages=messages)

    monkeypatch.setenv("OLLAMA_GENERATE__API_KEY", "test-api-key")
    monkeypatch.setenv("OLLAMA_GENERATE__TIMEOUT", "18.5")
    monkeypatch.setenv("OLLAMA_GENERATE__BASE_URL", "https://generate-ollama")
    monkeypatch.setenv("OLLAMA_EMBED__BASE_URL", "http://embed-ollama")
    monkeypatch.setenv("OLLAMA_EMBED__TIMEOUT", "99.0")
    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)

    client = OllamaGenerationClient()
    response = client.generate("Summarize alpha")

    assert response == "cloud answer"
    assert captured == {
        "host": "https://generate-ollama",
        "headers": {"Authorization": "Bearer test-api-key"},
        "timeout": 18.5,
        "model": "gpt-oss:20b",
        "messages": [{"role": "user", "content": "Summarize alpha"}],
    }


def test_ollama_generation_client_wraps_transport_errors(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, *, host: str, headers: dict[str, str], timeout: float) -> None:
            del host, headers, timeout

        def chat(self, *, model: str, messages: list[dict[str, str]]):
            del model, messages
            raise ConnectionError("boom")

    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)
    client = OllamaGenerationClient(model="gpt-oss:20b", api_key="test-api-key")

    with pytest.raises(RuntimeError, match="Failed to generate response from Ollama") as exc_info:
        client.generate("alpha")

    assert isinstance(exc_info.value.__cause__, ConnectionError)


def test_ollama_generation_client_rejects_malformed_response(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, *, host: str, headers: dict[str, str], timeout: float) -> None:
            del host, headers, timeout

        def chat(self, *, model: str, messages: list[dict[str, str]]):
            del model, messages
            return {}

    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)
    client = OllamaGenerationClient(model="gpt-oss:20b", api_key="test-api-key")

    with pytest.raises(RuntimeError, match="Ollama returned a malformed generation response") as exc_info:
        client.generate("alpha")

    assert isinstance(exc_info.value.__cause__, KeyError)
