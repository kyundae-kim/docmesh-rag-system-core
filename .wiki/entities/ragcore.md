---
title: RAGCore
created: 2026-06-11
updated: 2026-06-11
type: entity
tags: [rag, architecture, sdk, api, python]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-11.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: high
---

# RAGCore

`RAGCore`는 DocMesh RAG Core의 단일 public 진입점이다. 텍스트/파일 기반 ingestion, 사용자 스코프 제한 retrieval, 컨텍스트 기반 generation, 문서/청크 조회, ingestion progress 조회, 문서 삭제를 하나의 인터페이스로 노출한다. 이 단일 진입점 전략은 외부 통합을 단순하게 유지하면서도 내부 책임을 서비스 단위로 분리할 수 있게 설계되어 있다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]

## Public surface

주요 public 메서드는 `ingest_text`, `ingest_file_stream`, `ingest_file_path`, `query`, `list_documents`, `get_document`, `list_document_chunks`, `list_ingestion_progress`, `delete_document`로 구성된다. 반환 타입은 `DocumentRecord`, `ChunkRecord`, `IngestResult`, `IngestionProgressRecord`, `QueryResult`이며 패키지의 공식 public 타입 경로를 통해 재노출된다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]

## Role in the system

`RAGCore`는 외부에 SDK형 인터페이스를 제공하지만 내부적으로는 [[ingestion-pipeline]], retrieval orchestration, generation, metadata persistence를 조합하는 façade 역할을 맡는다. PRD는 이 구조가 향후 API 서버, 비동기 처리, 서비스 분리로 확장될 수 있어야 한다고 규정한다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]

## Constraints and implications

현재 구현에서 `token`은 사실상 `user_id` 스코프로 사용되며, 비어 있으면 `single-user`로 fallback 된다. 또한 문서 본문은 메타데이터에 직접 저장하지 않고 `storage_path` 기반 자산 관리 방식을 사용한다. 따라서 통합 시 호출자는 인증 컨텍스트와 문서 저장 정책을 함께 고려해야 한다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]

## Related pages

- [[public-api-surface]]
- [[rag-service-architecture]]
- [[user-scope-isolation]]
- [[persistence-and-restart-recovery]]
