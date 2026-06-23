from __future__ import annotations

from pathlib import Path

from rag_system_core.composition.docmesh_runtime import create_service_registry, load_docmesh_settings
from rag_system_core.composition.factories import (
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_vector_store,
)
from rag_system_core.domain.core import RAGCore


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
    embedding_client = create_rag_embedding_client(settings=settings, registry=registry)
    generation_client = create_rag_generation_client(settings=settings, registry=registry)
    vector_store = create_rag_vector_store(metadata_path=Path(metadata_path), settings=settings, registry=registry)
    return RAGCore(
        embedding_client=embedding_client,
        generation_client=generation_client,
        vector_store=vector_store,
        metadata_path=metadata_path,
        document_storage_dir=document_storage_dir,
        storage_mode=storage_mode,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
