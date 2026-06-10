---
title: Persistence and Restart Recovery
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [persistence, vector-store, testing, architecture]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-11.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: high
---

# Persistence and Restart Recovery

이 시스템은 단순한 in-memory demo가 아니라, 재시작 이후에도 문서/청크 메타데이터와 retrieval 가능 상태를 복원할 수 있어야 하는 RAG 코어를 목표로 한다. PRD와 테스트 명세 모두 이를 핵심 성공 기준으로 다룬다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]^[raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]

## Persistence layout

문서/청크 메타데이터는 SQLAlchemy ORM + SQLite에 저장되고, 검색 계층은 기본적으로 `metadata_path.with_suffix('.milvus.db')`에 대응하는 Milvus Lite persistent store를 사용한다. 문서 자산은 `memory` 또는 `local` 저장 모드를 선택할 수 있으며, 메타데이터에는 본문 대신 `storage_path`가 기록된다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]

## Data model implications

핵심 persistence 대상은 `documents`, `chunks`, `ingestion_progress` 테이블/모델이다. 청크 메타데이터는 retrieval 복원에 필요한 embedding 관련 정보와 Milvus generated chunk id를 반영해야 하며, 삭제 시 연관 데이터가 함께 정리되어야 한다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]^[raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]

## Operational meaning

복원 가능성은 단순 조회가 아니라 재초기화 후 query 성공까지 포함한다. 따라서 [[ingestion-pipeline]]에서 생성된 산출물이 저장 계층과 vector store 양쪽에 일관되게 반영되어야 하며, [[user-scope-isolation]]도 복원 후 깨지지 않아야 한다.

## Related pages

- [[rag-service-architecture]]
- [[ingestion-pipeline]]
- [[user-scope-isolation]]
- [[ragcore]]
