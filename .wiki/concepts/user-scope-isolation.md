---
title: User Scope Isolation
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [rag, security, api, sdk]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-11.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: high
---

# User Scope Isolation

현재 DocMesh RAG Core는 `token` 문자열을 그대로 `user_id` 스코프로 사용하며, token이 없거나 공백이면 `single-user`로 fallback 한다. 이 규칙은 API 문서, PRD, 테스트 명세에 모두 반복적으로 등장하는 핵심 계약이다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]^[raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]

## Why it matters

멀티 유저 환경에서 문서, 청크, 검색 결과가 섞이지 않는 것이 이 시스템의 가장 중요한 안정성 요구 중 하나다. PRD는 저장, 검색, 조회, 삭제 전 과정에서 `user_id` 스코프가 일관되게 유지되어야 한다고 명시하며, 리스크 항목에서도 데이터 혼합을 심각한 문제로 분류한다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]

## Enforcement points

스코프 제한은 ingestion 시 메타데이터 기록, retrieval 시 필터링, `get_document`, `list_document_chunks`, `list_ingestion_progress`, `delete_document` 같은 관리 API 전반에 적용되어야 한다. 테스트 명세 역시 서로 다른 token 간 query 결과 혼합 금지와 현재 token scope 기반 접근 제어를 중점적으로 확인한다.^[raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]

## Future implications

현재는 token 문자열 직접 사용이라는 단순 모델이지만, API 문서는 선택적 Keycloak 기반 `token -> user_id` 해석 가능성을 언급한다. 향후 API/MCP 계층이 생기면 인증/인가 경계와 내부 user scope 해석을 분리하는 설계가 필요할 수 있다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]

## Related pages

- [[ragcore]]
- [[public-api-surface]]
- [[persistence-and-restart-recovery]]
- [[interface-roadmap]]
