from __future__ import annotations

import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any, BinaryIO

from docmesh_py_core import KeycloakAuthService, ServiceFactoryRegistry, check_all_services, load_settings
import ollama
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag_system_core.types import DocumentRecord

DEFAULT_SINGLE_USER_ID = "single-user"


def _load_docmesh_settings(env: dict[str, str] | None = None) -> Any:
    return load_settings(env or os.environ)


def _create_docmesh_service_client(service_name: str, *, settings: Any | None = None) -> Any | None:
    resolved_settings = settings if settings is not None else _load_docmesh_settings()
    registry = ServiceFactoryRegistry(resolved_settings)
    return registry.create_client(service_name)


def _read_docmesh_ollama_settings(settings: Any | None = None) -> tuple[str | None, str | None, str | None, float | None]:
    resolved_settings = settings if settings is not None else _load_docmesh_settings()
    ollama_settings = getattr(resolved_settings, "ollama", None)
    if ollama_settings is None:
        return None, None, None, None

    host = getattr(ollama_settings, "host", None)
    embedding_model = getattr(ollama_settings, "embedding_model", None)
    generation_model = getattr(ollama_settings, "generation_model", None)
    timeout = getattr(ollama_settings, "request_timeout_seconds", None)
    return host, embedding_model, generation_model, float(timeout) if timeout is not None else None


def _read_docmesh_milvus_settings(settings: Any | None = None) -> tuple[str | None, str | None, float | None]:
    resolved_settings = settings if settings is not None else _load_docmesh_settings()
    milvus_settings = getattr(resolved_settings, "milvus", None)
    if milvus_settings is None:
        return None, None, None

    uri = getattr(milvus_settings, "uri", None)
    collection_name = getattr(milvus_settings, "collection", None) or getattr(
        milvus_settings, "collection_name", None
    )
    timeout = getattr(milvus_settings, "request_timeout_seconds", None)
    if timeout is None:
        timeout = getattr(milvus_settings, "connect_timeout_seconds", None)
    return uri, collection_name, float(timeout) if timeout is not None else None


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
        docmesh_settings = _load_docmesh_settings()
        docmesh_host, docmesh_embedding_model, _, docmesh_timeout = _read_docmesh_ollama_settings(docmesh_settings)
        resolved_model = model or docmesh_embedding_model or settings.model
        if resolved_model is None or not resolved_model.strip():
            raise ValueError("Ollama embed model must be provided either as 'model' or OLLAMA_EMBED__MODEL")
        self.model = resolved_model
        self.base_url = (base_url or docmesh_host or settings.base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else (docmesh_timeout or settings.timeout)
        if model is None and base_url is None and timeout is None:
            self._client = _create_docmesh_service_client("ollama", settings=docmesh_settings) or ollama.Client(
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


class MilvusSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MILVUS__",
        env_file=".env",
        extra="ignore",
    )

    uri: str | None = None
    collection_name: str = "rag_chunks"
    timeout: float = 30.0


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
        docmesh_settings = _load_docmesh_settings()
        docmesh_host, _, docmesh_generation_model, docmesh_timeout = _read_docmesh_ollama_settings(docmesh_settings)
        resolved_model = model or docmesh_generation_model or settings.model
        if resolved_model is None or not resolved_model.strip():
            raise ValueError("Ollama generation model must be provided either as 'model' or OLLAMA_GENERATE__MODEL")

        resolved_api_key = api_key or settings.api_key
        using_docmesh_client = model is None and base_url is None and timeout is None and api_key is None and headers is None
        docmesh_client = _create_docmesh_service_client("ollama", settings=docmesh_settings) if using_docmesh_client else None
        if resolved_api_key is None or not resolved_api_key.strip():
            if docmesh_client is None:
                raise ValueError("Ollama API key must be provided either as 'api_key' or OLLAMA_GENERATE__API_KEY")

        self.model = resolved_model
        self.base_url = (base_url or docmesh_host or settings.base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else (docmesh_timeout or settings.timeout)
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


class DocumentStorage:
    def __init__(self, mode: str, base_dir: Path) -> None:
        if mode not in {"memory", "local"}:
            raise ValueError("storage_mode must be 'memory' or 'local'")
        self.mode = mode
        self.base_dir = base_dir
        self._memory_documents: dict[str, str] = {}

    def store_text(self, *, doc_id: str, text: str, source: str) -> str:
        if self.mode == "memory":
            storage_path = f"memory://{doc_id}/{source}"
            self._memory_documents[storage_path] = text
            return storage_path

        self.base_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(source).suffix or ".txt"
        target = self.base_dir / f"{doc_id}{suffix}"
        target.write_text(text, encoding="utf-8")
        return str(target)

    def store_file_stream(self, *, doc_id: str, file_stream: BinaryIO, source: str) -> str:
        data = file_stream.read()
        if self.mode == "memory":
            storage_path = f"memory://{doc_id}/{source}"
            self._memory_documents[storage_path] = data.decode("utf-8")
            return storage_path

        self.base_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(source).suffix or ".bin"
        target = self.base_dir / f"{doc_id}{suffix}"
        target.write_bytes(data)
        return str(target)

    def store_file_path(self, *, doc_id: str, file_path: Path, source: str | None = None) -> str:
        with file_path.open("rb") as stream:
            return self.store_file_stream(
                doc_id=doc_id,
                file_stream=stream,
                source=source or file_path.name,
            )

    def load(self, document: DocumentRecord) -> str | None:
        if document.storage_path:
            if document.storage_path.startswith("memory://"):
                return self._memory_documents.get(document.storage_path)
            path = Path(document.storage_path)
            if path.exists():
                return path.read_text(encoding="utf-8")
        return None

    def delete(self, document: DocumentRecord) -> None:
        if not document.storage_path:
            return
        if document.storage_path.startswith("memory://"):
            self._memory_documents.pop(document.storage_path, None)
            return
        path = Path(document.storage_path)
        if path.exists():
            path.unlink()


class FixedWindowChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + self.chunk_size)
            chunks.append(normalized[start:end].strip())
            if end == len(normalized):
                break
            start = end - self.chunk_overlap
        return [chunk for chunk in chunks if chunk]


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCMESH_", env_file=".env", extra="ignore")

    auth_mode: str = "token"


@dataclass(slots=True)
class LocalHealthServiceResult:
    service: str
    ok: bool
    error: str | None = None


@dataclass(slots=True)
class LocalHealthCheckResult:
    ok: bool
    services: list[LocalHealthServiceResult]


def resolve_user_id(token: str | None) -> str:
    if token is None:
        return DEFAULT_SINGLE_USER_ID

    normalized = token.strip()
    if not normalized:
        return DEFAULT_SINGLE_USER_ID

    auth_mode = AuthSettings().auth_mode.strip().lower()
    if auth_mode != "keycloak":
        return normalized

    settings = _load_docmesh_settings()
    auth_service = KeycloakAuthService(settings, allowed_algorithms=["RS256"])
    user = auth_service.extract_user_info(normalized)
    subject = getattr(user, "sub", None)
    if subject is not None and str(subject).strip():
        return str(subject)
    preferred_username = getattr(user, "preferred_username", None)
    if preferred_username is not None and str(preferred_username).strip():
        return str(preferred_username)
    raise RuntimeError("Keycloak user info did not include a usable subject")


def extract_doc_id_from_storage_path(storage_path: str) -> str:
    name = Path(storage_path).stem
    if storage_path.startswith("memory://"):
        return storage_path.removeprefix("memory://").split("/", 1)[0]
    return name


def escape_milvus_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def resolve_milvus_runtime_settings(*, fallback_uri: str) -> tuple[str, str, float]:
    settings = MilvusSettings()
    docmesh_settings = _load_docmesh_settings()
    docmesh_uri, docmesh_collection_name, docmesh_timeout = _read_docmesh_milvus_settings(docmesh_settings)
    resolved_uri = docmesh_uri or settings.uri or fallback_uri
    resolved_collection_name = docmesh_collection_name or settings.collection_name
    resolved_timeout = docmesh_timeout or settings.timeout
    return resolved_uri, resolved_collection_name, resolved_timeout


def run_health_checks(service_checks: dict[str, Any], required_services: set[str] | None = None) -> Any:
    try:
        return check_all_services(service_checks, required_services=required_services)
    except Exception:
        pass

    services: list[LocalHealthServiceResult] = []
    ok = True
    for service_name, check in service_checks.items():
        try:
            check()
            services.append(LocalHealthServiceResult(service=service_name, ok=True, error=None))
        except Exception as exc:
            ok = False
            services.append(LocalHealthServiceResult(service=service_name, ok=False, error=str(exc)))
            if required_services is not None and service_name in required_services:
                break
    return LocalHealthCheckResult(ok=ok, services=services)
