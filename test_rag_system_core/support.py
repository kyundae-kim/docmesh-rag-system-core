from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docmesh_py_core import AuthenticatedUser

from rag_system_core import RAGCore
from rag_system_core.composition.factories import (
    create_rag_chunker,
    create_rag_document_storage,
    create_rag_metadata_store,
    create_rag_vector_store,
)


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


def create_test_rig(tmp_path: Path, *, storage_mode: str = "memory") -> TestRig:
    embedding_client = FakeEmbeddingClient()
    generation_client = FakeGenerationClient()
    metadata_path = tmp_path / "metadata.db"
    core = RAGCore(
        embedding_client=embedding_client,
        generation_client=generation_client,
        vector_store=create_rag_vector_store(metadata_path=metadata_path),
        metadata_store=create_rag_metadata_store(metadata_path=metadata_path),
        document_storage=create_rag_document_storage(
            storage_mode=storage_mode,
            document_storage_dir=tmp_path / "documents",
        ),
        chunker=create_rag_chunker(chunk_size=32, chunk_overlap=4),
    )
    return TestRig(
        core=core,
        embedding_client=embedding_client,
        generation_client=generation_client,
    )
