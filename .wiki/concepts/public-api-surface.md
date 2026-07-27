---
title: Public API Surface
created: 2026-06-11
updated: 2026-07-27
type: concept
tags: [sdk, api, python, integration]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-23.md, raw/articles/docmesh-rag-core-prd-2026-06-23.md, raw/articles/docmesh-rag-core-srs-2026-06-23.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]
confidence: high
---

# Public API Surface

이 페이지는 외부 애플리케이션이 `rag_system_core`를 어떻게 안정적으로 import하고 호출해야 하는지 정리한다.

## Import boundary

권장 import 경로는 `from rag_system_core import RAGCore` 및 `from rag_system_core.types import ...` 이다. 현재 API reference는 root export로 `RAGCore`, `OllamaEmbeddingClient`, `OllamaGenerationClient`, `bootstrap_rag_core`, `DocmeshRAGServiceFactory`, `RAGServiceFactory`, 각 record type, `EmbeddingClient`, `GenerationClient`를 명시한다. 반면 `rag_system_core.domain.*`, `rag_system_core.storage.*`, `rag_system_core.adapters.*`, `rag_system_core.core`는 외부 사용 문서의 주 대상이 아니다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-23.md]

## Construction and operational methods

현재 public construction path는 `RAGCore(...)`와 `bootstrap_rag_core(...)`다. operational surface는 세 가지 ingestion entrypoint(`ingest_text`, `ingest_file_stream`, `ingest_file_path`)와 query/관리 메서드(`query`, `list_documents`, `get_document`, `list_document_chunks`, `list_ingestion_progress`, `delete_document`) 및 `health_check()`로 구성된다. PRD와 SRS는 이 집합을 제품/소프트웨어 계약으로 함께 고정하고, API reference는 각 메서드 시그니처와 실패 조건까지 구체화한다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]^[raw/articles/docmesh-rag-core-srs-2026-06-23.md]^[raw/articles/docmesh-rag-core-api-reference-2026-06-23.md]

## Public data and composition types

SRS는 public record type으로 `DocumentRecord`, `ChunkRecord`, `IngestResult`, `IngestionProgressRecord`, `QueryResult`를 명시하고, API reference는 각 dataclass field shape까지 드러낸다. composition helper로는 `DocmeshRAGServiceFactory`, `create_rag_embedding_client(...)`, `create_rag_generation_client(...)`, `create_rag_vector_store(...)`, `create_rag_metadata_store(...)`, `create_rag_document_storage(...)`, `create_rag_chunker(...)`, `load_docmesh_settings(...)`, `create_service_registry(...)`, `resolve_user_id(...)`가 중요하다. 따라서 API surface는 단순 호출 메서드 집합이 아니라 조립 경계까지 포함한 안정적 소비면으로 읽는 것이 맞다.^[raw/articles/docmesh-rag-core-srs-2026-06-23.md]^[raw/articles/docmesh-rag-core-api-reference-2026-06-23.md]

## Input and prompt contracts

현재 제품 계약에서 `ingest_file_stream(...)`는 `source`가 비어 있으면 실패해야 하며, generation prompt는 최소 `[System Prompt]`, `[Retrieved Context]`, `[User Query]` 섹션을 포함해야 한다. API reference는 `ingest_text`의 빈 문서 오류, `ingest_file_path`의 source fallback, `delete_document`의 bool 반환 의미와 선행 vector-store 삭제 규칙까지 구체적으로 적는다. 이런 세부는 단순 구현 취향이 아니라 acceptance criteria와 운영 계약에 해당한다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]^[raw/articles/docmesh-rag-core-srs-2026-06-23.md]^[raw/articles/docmesh-rag-core-api-reference-2026-06-23.md]

## Adapter contracts

`EmbeddingClient`는 `embed(texts: list[str]) -> list[list[float]]`, `GenerationClient`는 `generate(prompt: str) -> str` 계약을 만족해야 한다. 또한 공개 adapter인 `OllamaEmbeddingClient`, `OllamaGenerationClient`는 각각 transport 오류와 malformed response를 `RuntimeError`로 표준화한다. 이는 외부 통합 코드가 adapter failure model을 어느 수준까지 가정할 수 있는지 보여 준다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-23.md]

## Root import discipline

`docmesh-py-core` v0.5.0 API reference는 패키지 루트의 `__all__`을 공개 소비 경계로 고정하고 86개 공개 이름을 계약 테스트로 확인한다. 조립 경로에는 `RuntimePlan`, `Service`, `assemble_services`, `assemble_service_runtime`, `ServiceBundle`, `ServiceRuntime`이 있고, direct API에는 `*Config`, `load_service_configs(services={...})`, `create_*_client`가 있다. `diagnose_services`, `ServiceClientWrapper`, `NatsConnectionBuilder`, health/cleanup helper, `KeycloakAuthService`도 루트에서 import한다. 따라서 RAG Core의 public API와 마찬가지로, 통합 코드는 문서화된 root export에 의존하고 내부 모듈 import를 피해야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]

## Integration implications

외부 인터페이스는 단순하지만 실제 구현은 [[rag-service-architecture]]와 [[ingestion-pipeline]]에 걸친 내부 조합 위에 있다. 따라서 SDK를 API나 MCP로 감쌀 때는 public surface를 그대로 재노출하되 내부 구현 경계는 새 인터페이스 계층 밖으로 새지 않게 유지하는 편이 바람직하다. 제품 전체 범위를 해석할 때는 [[product-scope-and-requirements]], [[software-requirements-and-traceability]], [[construction-paths-and-adapter-contracts]]를 함께 보는 것이 좋다.

## Related pages

- [[ragcore]]
- [[product-scope-and-requirements]]
- [[software-requirements-and-traceability]]
- [[construction-paths-and-adapter-contracts]]
- [[rag-service-architecture]]
- [[ingestion-pipeline]]
- [[service-factory-registry]]
- [[interface-roadmap]]
