from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import create_engine

from rag_system_core import RAGCore
from rag_system_core import AuthenticatedUser
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.composition.factories import create_rag_vector_store
from rag_system_core.composition.health import run_health_checks
from rag_system_core.storage.metadata_store import MetadataStore
from rag_system_core.types import DocumentRecord


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        vectors: list[list[float]] = []
        for text in texts:
            normalized = text.lower()
            vectors.append(
                [
                    float(normalized.count("alpha")),
                    float(normalized.count("beta")),
                    float(normalized.count("gamma")),
                    float(len(normalized)),
                ]
            )
        return vectors


class FakeGenerationClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    @property
    def last_prompt(self) -> str:
        return self.prompts[-1]

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        context_block = prompt.split("[Retrieved Context]\n", 1)[1]
        context, question = context_block.rsplit("\n\n[User Query]\n", 1)
        first_context_line = context.strip().splitlines()[0]
        return f"ANSWER::{question.strip()}::{first_context_line}"


class FakeDocumentStorage:
    def __init__(self, mode: str, base_dir: Path) -> None:
        if mode not in {"memory", "local"}:
            raise ValueError("storage_mode must be 'memory' or 'local'")
        self.mode = mode
        self.base_dir = base_dir
        self._memory_documents: dict[str, str] = {}

    def store_text(
        self,
        *,
        doc_id: str,
        user_id: str,
        text: str,
        source: str,
        idempotency_key: str,
    ) -> str:
        del user_id, idempotency_key
        if self.mode == "memory":
            asset_reference = f"memory://{doc_id}/{source}"
            self._memory_documents[asset_reference] = text
            return asset_reference

        self.base_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(source).suffix or ".txt"
        target = self.base_dir / f"{doc_id}{suffix}"
        target.write_text(text, encoding="utf-8")
        return str(target)

    def store_file_stream(
        self,
        *,
        doc_id: str,
        user_id: str,
        file_stream: BinaryIO,
        size: int,
        source: str,
        idempotency_key: str,
    ) -> str:
        del user_id, size, idempotency_key
        data = file_stream.read()
        if self.mode == "memory":
            asset_reference = f"memory://{doc_id}/{source}"
            self._memory_documents[asset_reference] = data.decode("utf-8")
            return asset_reference

        self.base_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(source).suffix or ".bin"
        target = self.base_dir / f"{doc_id}{suffix}"
        target.write_bytes(data)
        return str(target)

    def store_file_path(
        self,
        *,
        doc_id: str,
        user_id: str,
        file_path: Path,
        source: str | None = None,
        idempotency_key: str,
    ) -> str:
        with file_path.open("rb") as stream:
            return self.store_file_stream(
                doc_id=doc_id,
                user_id=user_id,
                file_stream=stream,
                size=file_path.stat().st_size,
                source=source or file_path.name,
                idempotency_key=idempotency_key,
            )

    def load(self, document: DocumentRecord) -> str | None:
        if document.asset_reference is None:
            return None
        if document.asset_reference.startswith("memory://"):
            return self._memory_documents.get(document.asset_reference)
        path = Path(document.asset_reference)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def delete(self, document: DocumentRecord) -> None:
        if document.asset_reference is None:
            return
        if document.asset_reference.startswith("memory://"):
            self._memory_documents.pop(document.asset_reference, None)
            return
        path = Path(document.asset_reference)
        if path.exists():
            path.unlink()


def authenticated_user(user_id: str) -> AuthenticatedUser:
    return AuthenticatedUser(
        sub=user_id,
        preferred_username=None,
        email=None,
        given_name=None,
        family_name=None,
        name=None,
        realm_roles=[],
        client_roles={},
        claims={},
    )


@dataclass
class TestRig:
    core: RAGCore
    embedding_client: FakeEmbeddingClient
    generation_client: FakeGenerationClient


def create_metadata_store(tmp_path: Path) -> MetadataStore:
    metadata_path = tmp_path / "metadata.db"
    return MetadataStore(create_engine(f"sqlite+pysqlite:///{metadata_path}"))


def create_test_rig(tmp_path: Path, *, storage_mode: str = "memory") -> TestRig:
    embedding_client = FakeEmbeddingClient()
    generation_client = FakeGenerationClient()
    core = RAGCore(
        embedding_client=embedding_client,
        generation_client=generation_client,
        vector_store=create_rag_vector_store(),
        metadata_store=create_metadata_store(tmp_path),
        document_storage=FakeDocumentStorage(storage_mode, tmp_path / "documents"),
        chunker=FixedWindowChunker(chunk_size=32, chunk_overlap=4),
        health_check_runner=run_health_checks,
    )
    return TestRig(
        core=core,
        embedding_client=embedding_client,
        generation_client=generation_client,
    )
