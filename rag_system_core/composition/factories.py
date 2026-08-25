"""Public composition-factory compatibility surface.

The implementations live in responsibility-focused modules. This module keeps
the established advanced import path stable for callers.
"""

from rag_system_core.composition.rag_factories import (
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_vector_store,
)
from rag_system_core.composition.service_factory import (
    DocmeshRAGServiceFactory,
    RAGServiceFactory,
)

__all__ = [
    "DocmeshRAGServiceFactory",
    "RAGServiceFactory",
    "create_rag_embedding_client",
    "create_rag_generation_client",
    "create_rag_vector_store",
]
