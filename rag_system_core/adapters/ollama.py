from __future__ import annotations

from typing import Any

import ollama

from rag_system_core.composition.docmesh_runtime import (
    create_docmesh_service_client,
    read_docmesh_ollama_settings,
    try_load_docmesh_settings,
)


def _resolve_ollama_runtime(
    *,
    settings: Any | None,
    model: str | None,
    base_url: str | None,
    timeout: float | None,
    kind: str,
) -> tuple[str, str, float]:
    docmesh_host, docmesh_embedding_model, docmesh_generation_model, docmesh_timeout = read_docmesh_ollama_settings(settings)
    configured_model = docmesh_embedding_model if kind == "embedding" else docmesh_generation_model
    error_message = (
        "Ollama embed model must be provided either as 'model' or OLLAMA_EMBEDDING_MODEL"
        if kind == "embedding"
        else "Ollama generation model must be provided either as 'model' or OLLAMA_GENERATION_MODEL"  # noqa: E501
    )

    resolved_model = model or configured_model
    if resolved_model is None or not resolved_model.strip():
        raise ValueError(error_message)

    resolved_base_url = (base_url or docmesh_host or "http://ollama:11434").rstrip("/")
    resolved_timeout = timeout if timeout is not None else (docmesh_timeout or 30.0)
    return resolved_model, resolved_base_url, resolved_timeout


def _resolve_ollama_client(
    *,
    client: Any | None,
    settings: Any | None,
    registry: Any | None,
    base_url: str,
    timeout: float,
) -> Any:
    if client is not None:
        return client
    return create_docmesh_service_client("ollama", settings=settings, registry=registry) or ollama.Client(
        host=base_url,
        timeout=timeout,
    )


class OllamaEmbeddingClient:
    def __init__(
        self,
        *,
        client: Any,
        model: str,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout
        self._client = client

    @classmethod
    def from_settings(
        cls,
        *,
        settings: Any | None = None,
        registry: Any | None = None,
        client: Any | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> "OllamaEmbeddingClient":
        resolved_model, resolved_base_url, resolved_timeout = _resolve_ollama_runtime(
            settings=settings,
            model=model,
            base_url=base_url,
            timeout=timeout,
            kind="embedding",
        )
        resolved_client = _resolve_ollama_client(
            client=client,
            settings=settings,
            registry=registry,
            base_url=resolved_base_url,
            timeout=resolved_timeout,
        )
        return cls(
            client=resolved_client,
            model=resolved_model,
            base_url=resolved_base_url,
            timeout=resolved_timeout,
        )

    @classmethod
    def from_env(
        cls,
        *,
        client: Any | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> "OllamaEmbeddingClient":
        settings = try_load_docmesh_settings()
        return cls.from_settings(
            settings=settings,
            client=client,
            model=model,
            base_url=base_url,
            timeout=timeout,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            response = self._client.embed(model=self.model, input=texts)
        except Exception as exc:
            raise RuntimeError("Failed to fetch embeddings from Ollama") from exc

        try:
            embeddings = response["embeddings"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Ollama returned a malformed embeddings response") from exc

        return [[float(value) for value in vector] for vector in embeddings]

    def check(self) -> None:
        if hasattr(self._client, "check"):
            self._client.check()
            return
        if hasattr(self._client, "ps"):
            self._client.ps()
            return
        raise RuntimeError("Ollama client does not support health checks")


class OllamaGenerationClient:
    def __init__(
        self,
        *,
        client: Any,
        model: str,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout
        self._client = client

    @classmethod
    def from_settings(
        cls,
        *,
        settings: Any | None = None,
        registry: Any | None = None,
        client: Any | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> "OllamaGenerationClient":
        resolved_model, resolved_base_url, resolved_timeout = _resolve_ollama_runtime(
            settings=settings,
            model=model,
            base_url=base_url,
            timeout=timeout,
            kind="generation",
        )
        resolved_client = _resolve_ollama_client(
            client=client,
            settings=settings,
            registry=registry,
            base_url=resolved_base_url,
            timeout=resolved_timeout,
        )
        return cls(
            client=resolved_client,
            model=resolved_model,
            base_url=resolved_base_url,
            timeout=resolved_timeout,
        )

    @classmethod
    def from_env(
        cls,
        *,
        client: Any | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> "OllamaGenerationClient":
        settings = try_load_docmesh_settings()
        return cls.from_settings(
            settings=settings,
            client=client,
            model=model,
            base_url=base_url,
            timeout=timeout,
        )

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        except Exception as exc:
            raise RuntimeError("Failed to generate response from Ollama") from exc

        try:
            generated_text = response["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Ollama returned a malformed generation response") from exc

        return str(generated_text)

    def check(self) -> None:
        if hasattr(self._client, "check"):
            self._client.check()
            return
        if hasattr(self._client, "ps"):
            self._client.ps()
            return
        raise RuntimeError("Ollama client does not support health checks")
