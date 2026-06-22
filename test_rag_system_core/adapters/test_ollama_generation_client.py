from __future__ import annotations

import pytest

import rag_system_core.core as core_module
import rag_system_core.infrastructure as infrastructure_module
from rag_system_core import OllamaGenerationClient


class RecordingOllamaGenerateClient:
    def __init__(self, captured: dict[str, object], *, host: str, timeout: float) -> None:
        captured["host"] = host
        captured["timeout"] = timeout
        self._captured = captured

    def chat(self, *, model: str, messages: list[dict[str, str]]):
        self._captured["model"] = model
        self._captured["messages"] = messages
        return {"message": {"content": "cloud answer"}}


def test_ollama_generation_client_requires_model_when_not_configured(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "")

    with pytest.raises(
        ValueError,
        match="Ollama generation model must be provided either as 'model' or OLLAMA_GENERATION_MODEL",
    ):
        OllamaGenerationClient.from_env()


def test_ollama_generation_client_reads_configuration_from_environment(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            self._delegate = RecordingOllamaGenerateClient(captured, host=host, timeout=timeout)

        def chat(self, *, model: str, messages: list[dict[str, str]]):
            return self._delegate.chat(model=model, messages=messages)

    monkeypatch.setenv("OLLAMA_HOST", "http://shared-ollama")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "gpt-oss:20b")
    monkeypatch.setenv("OLLAMA_REQUEST_TIMEOUT_SECONDS", "18.5")
    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)

    client = OllamaGenerationClient.from_env()
    response = client.generate("Summarize alpha")

    assert response == "cloud answer"
    assert captured == {
        "host": "http://shared-ollama",
        "timeout": 18.5,
        "model": "gpt-oss:20b",
        "messages": [{"role": "user", "content": "Summarize alpha"}],
    }


def test_ollama_generation_client_explicit_overrides_bypass_docmesh_loading(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            self._delegate = RecordingOllamaGenerateClient(captured, host=host, timeout=timeout)

        def chat(self, *, model: str, messages: list[dict[str, str]]):
            return self._delegate.chat(model=model, messages=messages)

    def broken_load_settings(env) -> object:
        del env
        raise RuntimeError("invalid docmesh settings")

    monkeypatch.setattr(infrastructure_module, "load_settings", broken_load_settings)
    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)

    client = OllamaGenerationClient.from_settings(model="gpt-oss:20b", base_url="http://ollama.example", timeout=7.0)
    response = client.generate("Summarize alpha")

    assert response == "cloud answer"
    assert captured == {
        "host": "http://ollama.example",
        "timeout": 7.0,
        "model": "gpt-oss:20b",
        "messages": [{"role": "user", "content": "Summarize alpha"}],
    }


def test_ollama_generation_client_wraps_transport_errors(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            del host, timeout

        def chat(self, *, model: str, messages: list[dict[str, str]]):
            del model, messages
            raise ConnectionError("boom")

    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)
    client = OllamaGenerationClient.from_settings(model="gpt-oss:20b", base_url="http://ollama", timeout=7.0)

    with pytest.raises(RuntimeError, match="Failed to generate response from Ollama") as exc_info:
        client.generate("alpha")

    assert isinstance(exc_info.value.__cause__, ConnectionError)


def test_ollama_generation_client_rejects_malformed_response(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            del host, timeout

        def chat(self, *, model: str, messages: list[dict[str, str]]):
            del model, messages
            return {}

    monkeypatch.setattr(core_module.ollama, "Client", FakeClient)
    client = OllamaGenerationClient.from_settings(model="gpt-oss:20b", base_url="http://ollama", timeout=7.0)

    with pytest.raises(RuntimeError, match="Ollama returned a malformed generation response") as exc_info:
        client.generate("alpha")

    assert isinstance(exc_info.value.__cause__, KeyError)


def test_ollama_generation_client_uses_injected_client_without_loading_settings(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def broken_load_settings(env) -> object:
        del env
        raise RuntimeError("invalid docmesh settings")

    monkeypatch.setattr(infrastructure_module, "load_settings", broken_load_settings)

    injected_client = RecordingOllamaGenerateClient(captured, host="http://ignored", timeout=999.0)
    client = OllamaGenerationClient(client=injected_client, model="gpt-oss:20b")

    response = client.generate("Summarize alpha")

    assert response == "cloud answer"
    assert captured == {
        "host": "http://ignored",
        "timeout": 999.0,
        "model": "gpt-oss:20b",
        "messages": [{"role": "user", "content": "Summarize alpha"}],
    }
