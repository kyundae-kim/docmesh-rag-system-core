from __future__ import annotations

import ollama
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag_system_core.composition.docmesh_runtime import (
    create_docmesh_service_client,
    read_docmesh_ollama_settings,
    try_load_docmesh_settings,
)


class OllamaEmbedSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OLLAMA_EMBED__",
        env_file=".env",
        extra="ignore",
    )

    base_url: str = "http://ollama:11434"
    model: str | None = None
    timeout: float = 30.0


class OllamaGenerateSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OLLAMA_GENERATE__",
        env_file=".env",
        extra="ignore",
    )

    base_url: str = "https://ollama.com"
    model: str = "gpt-oss:20b"
    timeout: float = 30.0
    api_key: str | None = None


class MilvusSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MILVUS__",
        env_file=".env",
        extra="ignore",
    )

    uri: str | None = None
    collection_name: str = "rag_chunks"
    timeout: float = 30.0


OllamaSettings = OllamaEmbedSettings


class OllamaEmbeddingClient:
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        settings = OllamaEmbedSettings()
        should_try_docmesh = model is None or base_url is None or timeout is None
        docmesh_settings = try_load_docmesh_settings() if should_try_docmesh else None
        docmesh_host, docmesh_embedding_model, _, docmesh_timeout = read_docmesh_ollama_settings(docmesh_settings)
        resolved_model = model or docmesh_embedding_model or settings.model
        if resolved_model is None or not resolved_model.strip():
            raise ValueError("Ollama embed model must be provided either as 'model' or OLLAMA_EMBED__MODEL")
        self.model = resolved_model
        self.base_url = (base_url or docmesh_host or settings.base_url or "http://ollama:11434").rstrip("/")
        self.timeout = timeout if timeout is not None else (docmesh_timeout or settings.timeout or 30.0)
        if model is None and base_url is None and timeout is None and docmesh_settings is not None:
            self._client = create_docmesh_service_client("ollama", settings=docmesh_settings) or ollama.Client(
                host=self.base_url,
                timeout=self.timeout,
            )
        else:
            self._client = ollama.Client(host=self.base_url, timeout=self.timeout)

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
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        settings = OllamaGenerateSettings()
        should_try_docmesh = model is None or base_url is None or timeout is None
        docmesh_settings = try_load_docmesh_settings() if should_try_docmesh else None
        docmesh_host, _, docmesh_generation_model, docmesh_timeout = read_docmesh_ollama_settings(docmesh_settings)
        resolved_model = model or docmesh_generation_model or settings.model
        if resolved_model is None or not resolved_model.strip():
            raise ValueError("Ollama generation model must be provided either as 'model' or OLLAMA_GENERATE__MODEL")

        resolved_api_key = api_key or settings.api_key
        using_docmesh_client = (
            model is None
            and base_url is None
            and timeout is None
            and api_key is None
            and headers is None
            and docmesh_settings is not None
        )
        docmesh_client = create_docmesh_service_client("ollama", settings=docmesh_settings) if using_docmesh_client else None
        if resolved_api_key is None or not resolved_api_key.strip():
            if docmesh_client is None:
                raise ValueError("Ollama API key must be provided either as 'api_key' or OLLAMA_GENERATE__API_KEY")

        self.model = resolved_model
        self.base_url = (base_url or docmesh_host or settings.base_url or "https://ollama.com").rstrip("/")
        self.timeout = timeout if timeout is not None else (docmesh_timeout or settings.timeout or 30.0)
        self.headers = headers or ({"Authorization": f"Bearer {resolved_api_key}"} if resolved_api_key else None)
        self._client = docmesh_client or ollama.Client(host=self.base_url, headers=self.headers, timeout=self.timeout)

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
