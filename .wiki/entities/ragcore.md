---
title: RAGCore
created: 2026-06-11
updated: 2026-08-18
type: entity
tags: [rag, architecture, sdk, api, python]
sources: []
confidence: high
---

# RAGCore

`RAGCore`는 DocMesh RAG Core의 단일 public 진입점이다. 텍스트/파일 기반 ingestion, 사용자 스코프 제한 retrieval, 컨텍스트 기반 generation, 문서/청크 조회, ingestion progress 조회, 문서 삭제를 하나의 인터페이스로 노출한다. 현재 PRD는 이 단일 진입점 전략을 제품의 핵심 가치로 규정하고, API reference는 이것이 실제로 조립된 의존성 그래프를 소비하는 façade임을 명확히 한다.

## Public surface

주요 public 메서드는 `ingest_text`, `ingest_file_stream`, `ingest_file_path`, `query`, `list_documents`, `get_document`, `list_document_chunks`, `list_ingestion_progress`, `delete_document`, `health_check`로 구성된다. 반환 타입은 `DocumentRecord`, `ChunkRecord`, `IngestResult`, `IngestionProgressRecord`, `QueryResult`이며 패키지의 공식 public 타입 경로를 통해 재노출된다.

## Role in the system

`RAGCore`는 외부에 SDK형 인터페이스를 제공하지만 내부적으로는 [[ingestion-pipeline]], retrieval orchestration, generation, metadata persistence를 조합하는 façade 역할을 맡는다. 현재 repository에는 environment 기반으로 `RAGCore`를 생성하는 public bootstrap entrypoint가 없으며, 조립 결과물의 최종 소비 경계는 `RAGCore` 자체와 `DocmeshRAGServiceFactory.create_rag_core()`다.

## Constructor boundary

현재 구현에서 `RAGCore(...)`는 `embedding_client`, `generation_client`, `vector_store`, `metadata_store`, `document_storage`, `chunker`를 직접 주입받는 조립형 생성자다. 즉 설정 경로나 chunk 파라미터를 직접 넘기는 convenience constructor로 보면 안 되며, 실제 첫 성공 경로는 helper factory를 통한 구성 후 주입이다. 이 경계는 [[construction-paths-and-adapter-contracts]]와 [[service-factory-registry]]를 함께 볼 때 가장 분명해진다.

## Constraints and implications

현재 구현에서 token은 기본적으로 그대로 `user_id` 스코프로 사용되며, 비어 있으면 `single-user`로 fallback 된다. 또한 문서 본문은 메타데이터에 직접 저장하지 않고 `storage_path` 기반 자산 관리 방식을 사용한다. 파일 스트림 ingestion은 `source`가 없으면 실패해야 하고, `delete_document`는 vector store 삭제가 먼저 성공해야 metadata/asset 정리를 진행하므로 통합 시 인증 컨텍스트와 문서 출처 정보, 삭제 재시도 정책을 함께 관리해야 한다.

## Related pages

- [[product-scope-and-requirements]]
- [[public-api-surface]]
- [[construction-paths-and-adapter-contracts]]
- [[rag-service-architecture]]
- [[user-scope-isolation]]
- [[persistence-and-restart-recovery]]
