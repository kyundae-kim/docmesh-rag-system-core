from __future__ import annotations

import rag_system_core.composition.factories as factories_module
import rag_system_core.composition.rag_factories as rag_factories_module
import rag_system_core.composition.service_factory as service_factory_module


def test_factory_implementations_have_separate_composition_owners() -> None:
    assert factories_module.create_rag_embedding_client is rag_factories_module.create_rag_embedding_client
    assert factories_module.create_rag_generation_client is rag_factories_module.create_rag_generation_client
    assert factories_module.create_rag_vector_store is rag_factories_module.create_rag_vector_store
    assert factories_module.DocmeshRAGServiceFactory is service_factory_module.DocmeshRAGServiceFactory
    assert factories_module.RAGServiceFactory is service_factory_module.RAGServiceFactory
    assert rag_factories_module.create_rag_vector_store.__module__ == (
        "rag_system_core.composition.rag_factories"
    )
    assert service_factory_module.DocmeshRAGServiceFactory.__module__ == (
        "rag_system_core.composition.service_factory"
    )
