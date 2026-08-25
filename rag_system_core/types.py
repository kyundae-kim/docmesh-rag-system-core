from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthenticatedUser:
    """Authenticated identity required by the RAG user-scope boundary."""

    sub: str


@dataclass(slots=True)
class DocumentRecord:
    doc_id: str
    user_id: str
    source: str
    created_at: str
    asset_reference: str | None = None


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


# Compatibility exports; canonical protocol definitions live in ports.py.
from rag_system_core.ports import EmbeddingClient, GenerationClient

__all__ = [
    "AuthenticatedUser",
    "ChunkRecord",
    "DocumentRecord",
    "EmbeddingClient",
    "GenerationClient",
    "IngestResult",
    "IngestionProgressRecord",
    "QueryResult",
]
