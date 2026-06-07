from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class GenerationClient(Protocol):
    def generate(self, prompt: str) -> str: ...


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


__all__ = [
    "ChunkRecord",
    "DocumentRecord",
    "EmbeddingClient",
    "GenerationClient",
    "IngestionProgressRecord",
    "IngestResult",
    "QueryResult",
]
