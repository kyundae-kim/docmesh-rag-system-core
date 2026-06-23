---
title: Interface Roadmap
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [roadmap, api, mcp, sdk, integration]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-11.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: medium
---

# Interface Roadmap

현재 제품의 우선 인터페이스는 Python SDK 형태의 `RAGCore`이지만, PRD는 이후 FastAPI 기반 API 서비스, async 처리, 외부 vector DB 연동, 더 나아가 서비스 분리로의 확장을 명시한다. 사용자가 밝힌 위키 도메인 요구 역시 SDK를 출발점으로 삼되 추후 API와 MCP 등 다양한 인터페이스로 연결하는 방향과 일치한다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]

## Near-term direction

가장 자연스러운 다음 단계는 현재 [[public-api-surface]]를 안정적인 계약으로 유지한 채 API 계층에서 이를 감싸는 것이다. 이 경우 ingestion/query/문서 관리 메서드의 의미를 바꾸기보다 transport와 인증, 에러 표준화, 비동기 orchestration을 별도 층으로 추가하는 방식이 적합하다.

## MCP relevance

현재 소스 문서에는 MCP 세부 계약이 아직 없다. 따라서 MCP 관련 지식은 현 단계에서 확정 사실이 아니라 향후 인터페이스 확장 방향으로만 다뤄야 한다. 이 페이지의 `confidence`를 `medium`으로 둔 이유도 동일하다.

## Design watchpoints

API/MCP 계층이 추가되더라도 [[user-scope-isolation]]과 [[persistence-and-restart-recovery]]의 핵심 계약은 변하지 않아야 한다. 또한 내부 서비스 경계는 [[rag-service-architecture]]에 정의된 책임 분리를 해치지 않는 방향으로 노출되어야 한다.

## Related pages

- [[public-api-surface]]
- [[rag-service-architecture]]
- [[directory-refactoring-plan-for-docmesh-runtime-integration]]
- [[user-scope-isolation]]
- [[ragcore]]
