---
title: Persistence and Restart Recovery
created: 2026-06-11
updated: 2026-06-23
type: concept
tags: [persistence, vector-store, testing, architecture]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-23.md, raw/articles/docmesh-rag-core-srs-2026-06-23.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: high
---

# Persistence and Restart Recovery

이 시스템은 단순한 in-memory demo가 아니라, 재시작 이후에도 문서/청크 메타데이터와 retrieval 가능 상태를 복원할 수 있어야 하는 RAG 코어를 목표로 한다. 현재 PRD는 이를 핵심 성공 기준으로 유지하며, SRS는 이를 `documents`, `chunks`, `ingestion_progress` 유지와 동일 Milvus 구성을 다시 여는 recovery requirement로 더 구체화한다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]^[raw/articles/docmesh-rag-core-srs-2026-06-23.md]

## Persistence layout

문서/청크 메타데이터는 SQLAlchemy ORM + SQLite에 저장되고, 검색 계층은 기본적으로 `metadata_path.with_suffix('.milvus.db')`에 대응하는 Milvus Lite persistent store를 사용한다. 문서 자산은 `memory` 또는 `local` 저장 모드를 선택할 수 있으며, 메타데이터에는 본문 대신 `storage_path`가 기록된다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Data model implications

핵심 persistence 대상은 `documents`, `chunks`, `ingestion_progress` 테이블/모델이다. PRD는 `documents`에 `doc_id`, `user_id`, `source`, `created_at`, `storage_path`를, `chunks`에 Milvus auto-id mirrored metadata를, `ingestion_progress`에 `job_id`, `step_name`, `step_order`, `status`를 기대한다. SRS는 여기에 `metadata_json` persistability, `job_id/doc_id/user_id/step_name/status` 기반 추적성, `memory` asset의 비영속성 같은 데이터 요구사항을 덧붙인다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]^[raw/articles/docmesh-rag-core-srs-2026-06-23.md]

## Deletion semantics

문서 삭제 성공 경로에서는 document metadata, chunk metadata, ingestion progress metadata, stored asset, Milvus 엔트리가 함께 정리되어야 한다. 반대로 vector store 삭제가 실패하면 metadata / asset 삭제를 진행하지 않아야 하므로, 삭제 로직은 단순 정리 작업이 아니라 재시도 가능한 보존 정책을 포함한다. 이 부분은 SRS에서 별도의 기능 요구사항 군으로도 분리되어 있다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]^[raw/articles/docmesh-rag-core-srs-2026-06-23.md]

## Operational meaning

복원 가능성은 단순 조회가 아니라 재초기화 후 query 성공까지 포함한다. 또한 SQLite가 embedding 벡터를 직접 재생성하지는 않아야 하므로, retrieval 복원은 저장된 Milvus 상태 재사용에 의존한다. 이 페이지는 [[rag-service-architecture]], [[product-scope-and-requirements]], [[software-requirements-and-traceability]]를 함께 볼 때 가장 정확하게 해석된다.^[raw/articles/docmesh-rag-core-srs-2026-06-23.md]

## Related pages

- [[rag-service-architecture]]
- [[product-scope-and-requirements]]
- [[software-requirements-and-traceability]]
- [[ingestion-pipeline]]
- [[user-scope-isolation]]
- [[ragcore]]
