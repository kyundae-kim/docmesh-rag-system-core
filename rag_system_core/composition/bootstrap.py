from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from rag_system_core.composition.factories import DocmeshRAGServiceFactory, RAGServiceFactory
from rag_system_core.composition.health import run_health_checks
from rag_system_core.domain.core import RAGCore


def bootstrap_rag_core(
    *,
    service_factory: RAGServiceFactory,
    metadata_path,
    chunk_size=512,
    chunk_overlap=64,
):
    return RAGCore(
        embedding_client=service_factory.create_embedding_client(),
        generation_client=service_factory.create_generation_client(),
        vector_store=service_factory.create_vector_store(),
        metadata_store=service_factory.create_metadata_store(metadata_path=Path(metadata_path)),
        document_storage=service_factory.create_document_storage(),
        chunker=service_factory.create_chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
        health_check_runner=run_health_checks,
    )


@contextmanager
def bootstrap_rag_core_from_env(
    *,
    metadata_path: str | Path,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    check_on_startup: bool = True,
    parallel_healthchecks: bool = True,
) -> Iterator[RAGCore]:
    with DocmeshRAGServiceFactory.from_env(
        check_on_startup=check_on_startup,
        parallel_healthchecks=parallel_healthchecks,
    ) as service_factory:
        yield bootstrap_rag_core(
            service_factory=service_factory,
            metadata_path=metadata_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

