from __future__ import annotations

from pathlib import Path

from rag_system_core.composition.docmesh_runtime import create_service_registry, load_docmesh_settings
from rag_system_core.composition.factories import DocmeshRAGServiceFactory, RAGServiceFactory
from rag_system_core.domain.core import RAGCore


def bootstrap_rag_core(
    *,
    service_factory: RAGServiceFactory,
    metadata_path,
    document_storage_dir,
    storage_mode="local",
    chunk_size=512,
    chunk_overlap=64,
):
    return RAGCore(
        embedding_client=service_factory.create_embedding_client(),
        generation_client=service_factory.create_generation_client(),
        vector_store=service_factory.create_vector_store(metadata_path=Path(metadata_path)),
        metadata_store=service_factory.create_metadata_store(metadata_path=Path(metadata_path)),
        document_storage=service_factory.create_document_storage(
            storage_mode=storage_mode,
            document_storage_dir=document_storage_dir,
        ),
        chunker=service_factory.create_chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
    )


def bootstrap_rag_core_from_docmesh(
    *,
    metadata_path,
    document_storage_dir,
    storage_mode="local",
    chunk_size=512,
    chunk_overlap=64,
):
    settings = load_docmesh_settings()
    registry = create_service_registry(settings)
    service_factory = DocmeshRAGServiceFactory(settings=settings, registry=registry)
    return bootstrap_rag_core(
        service_factory=service_factory,
        metadata_path=metadata_path,
        document_storage_dir=document_storage_dir,
        storage_mode=storage_mode,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
