---
title: User Scope Isolation
created: 2026-06-11
updated: 2026-06-23
type: concept
tags: [rag, security, api, sdk]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-23.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: high
---

# User Scope Isolation

현재 DocMesh RAG Core는 기본 auth mode에서 `token` 문자열을 그대로 `user_id` 스코프로 사용하며, token이 없거나 공백이면 `single-user`로 fallback 한다. 이 규칙은 PRD의 acceptance criteria에도 직접 고정되어 있어, 단순 구현 세부가 아니라 제품 계약이다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]^[raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]

## Why it matters

멀티 유저 환경에서 문서, 청크, 검색 결과가 섞이지 않는 것이 이 시스템의 가장 중요한 안정성 요구 중 하나다. PRD는 저장, 검색, 조회, 삭제 전 과정에서 `user_id` 스코프가 일관되게 유지되어야 한다고 명시하며, 비기능 요구사항에서도 데이터 혼합 방지를 핵심 품질 조건으로 둔다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Keycloak path

`DOCMESH_AUTH_MODE=keycloak`일 때는 Keycloak 검증을 통해 `user_id`를 해석해야 하며, `sub`를 우선 사용하고 없으면 `preferred_username`을 사용해야 한다. 둘 다 없으면 오류여야 한다. 따라서 현재 scope 모델은 단순 token passthrough와 외부 identity resolution을 함께 수용하지만, 두 경로 모두 최종적으로 동일한 `user_id` 기반 격리 계약으로 수렴한다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Enforcement points

스코프 제한은 ingestion 시 메타데이터 기록, retrieval 시 필터링, `get_document`, `list_document_chunks`, `list_ingestion_progress`, `delete_document` 같은 관리 API 전반에 적용되어야 한다. query 역시 반드시 현재 user scope에 속한 chunk만 사용해야 하며, 이것은 acceptance criteria의 명시 항목이다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]^[raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]

## Future implications

현재는 user scope 계약이 단순하고 강하지만, API/MCP 계층이 추가되면 인증/인가 경계와 내부 user scope 해석을 분리하는 설계가 중요해질 수 있다. 이 맥락은 [[public-api-surface]], [[service-factory-registry]], [[interface-roadmap]]와 함께 읽는 편이 좋다.

## Related pages

- [[ragcore]]
- [[product-scope-and-requirements]]
- [[public-api-surface]]
- [[persistence-and-restart-recovery]]
- [[interface-roadmap]]
