from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Protocol

import ollama
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SINGLE_USER_ID = "single-user"


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


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
        resolved_model = model or settings.model
        if resolved_model is None or not resolved_model.strip():
            raise ValueError("Ollama embed model must be provided either as 'model' or OLLAMA_EMBED__MODEL")
        self.model = resolved_model
        self.base_url = (base_url or settings.base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.timeout
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


class MilvusSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MILVUS__",
        env_file=".env",
        extra="ignore",
    )

    uri: str | None = None
    collection_name: str = "rag_chunks"
    timeout: float = 30.0


class GenerationClient(Protocol):
    def generate(self, prompt: str) -> str: ...


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
        resolved_model = model or settings.model
        if resolved_model is None or not resolved_model.strip():
            raise ValueError("Ollama generation model must be provided either as 'model' or OLLAMA_GENERATE__MODEL")

        resolved_api_key = api_key or settings.api_key
        if resolved_api_key is None or not resolved_api_key.strip():
            raise ValueError("Ollama API key must be provided either as 'api_key' or OLLAMA_GENERATE__API_KEY")

        self.model = resolved_model
        self.base_url = (base_url or settings.base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.timeout
        self.headers = headers or {"Authorization": f"Bearer {resolved_api_key}"}
        self._client = ollama.Client(host=self.base_url, headers=self.headers, timeout=self.timeout)

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.chat(model=self.model, messages=[{'role': 'user', 'content': prompt}])
        except Exception as exc:
            raise RuntimeError("Failed to generate response from Ollama") from exc

        try:
            generated_text = response['message']['content']
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Ollama returned a malformed generation response") from exc

        return str(generated_text)


@dataclass(slots=True)
class DocumentRecord:
    doc_id: str
    user_id: str
    source: str
    created_at: str
    storage_path: str | None = None


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    doc_id: str
    user_id: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class IngestResult:
    job_id: str
    doc_id: str
    user_id: str
    source: str
    created_at: str
    chunk_count: int


@dataclass(slots=True)
class IngestionProgressRecord:
    progress_id: str
    job_id: str
    doc_id: str
    user_id: str
    source: str
    step_name: str
    step_order: int
    status: str
    created_at: str


@dataclass(slots=True)
class QueryResult:
    answer: str
    prompt: str
    context_chunks: list[ChunkRecord]


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


def resolve_user_id(token: str | None) -> str:
    if token is None:
        return DEFAULT_SINGLE_USER_ID

    normalized = token.strip()
    if not normalized:
        return DEFAULT_SINGLE_USER_ID
    return normalized


def extract_doc_id_from_storage_path(storage_path: str) -> str:
    name = Path(storage_path).stem
    if storage_path.startswith("memory://"):
        return storage_path.removeprefix("memory://").split("/", 1)[0]
    return name


def escape_milvus_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
