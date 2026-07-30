---
title: Project Roadmap
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [roadmap, sdk, api, mcp, architecture, decision]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-11.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: medium
---

# Project Roadmap

이 로드맵은 현재 DocMesh RAG Core를 **SDK 중심의 canonical core**로 유지하면서, 이후 **API**와 **MCP** 인터페이스로 확장하는 순서를 정리한다. 방향성은 [[sdk-first-with-api-and-mcp-evaluation]]과 [[future-considerations-for-sdk-api-mcp-rag-project]]의 판단을 따르며, 기반 구조는 [[public-api-surface]]와 [[rag-service-architecture]]를 전제로 한다.

## Roadmap principles

- 도메인 규칙은 core SDK가 소유한다.
- 채널 규칙은 API/MCP adapter가 소유한다.
- [[user-scope-isolation]]과 [[persistence-and-restart-recovery]]는 어떤 인터페이스가 추가되어도 깨지면 안 되는 핵심 계약이다.
- 새 인터페이스를 만들기 전에 core contract와 acceptance test를 먼저 안정화한다.

## Phase 0 — Core contract hardening

### Goal

SDK를 단순 구현물이 아니라 외부가 의존 가능한 제품 계약으로 만든다.

### Main work

- public import 경로와 노출 타입 정리
- 반환 모델과 오류 모델 표준화
- `RAGCore` public 메서드 의미 고정
- `internal.*` 직접 의존 금지 원칙 명문화
- core 문서와 예제 정리

### Exit criteria

- 외부 소비자가 internal 경로를 보지 않고도 SDK를 사용할 수 있다.
- public API 변경 시 breaking/non-breaking 기준이 문서화되어 있다.
- [[public-api-surface]]가 실제 구현과 어긋나지 않는다.

## Phase 1 — Test and reliability baseline

### Goal

SDK/API/MCP로 확장해도 유지될 공통 기능 계약을 테스트로 고정한다.

### Main work

- 현재 테스트 명세를 acceptance/contract test 관점으로 재구성
- user scope isolation 시나리오 강화
- delete semantics, restart recovery, ingestion progress 검증 강화
- mock client와 fixture를 정비해 다른 인터페이스에서도 같은 시나리오를 재사용 가능하게 구성

### Exit criteria

- SDK에 대해 핵심 lifecycle 시나리오가 자동 검증된다.
- 이후 API/MCP 프로젝트가 같은 시나리오를 공유할 수 있다.
- [[user-scope-isolation]]과 [[persistence-and-restart-recovery]] 관련 회귀를 빠르게 감지할 수 있다.

## Phase 2 — Thin API service

### Goal

SDK를 재사용하는 얇은 HTTP API 계층을 만든다.

### Main work

- FastAPI 등으로 ingest/query/document management 엔드포인트 구성
- request/response schema 정의
- auth와 internal user scope 해석 분리
- 동기 SDK 호출을 우선 감싸되 progress polling 구조 추가
- 운영 기본기: health check, logging, config, error mapping

### Exit criteria

- API가 core 로직을 재구현하지 않고 SDK를 호출한다.
- API 인증 경계와 SDK 내부 user scope enforcement 경계가 분리된다.
- 핵심 SDK 시나리오가 API에서도 의미상 동일하게 통과한다.

## Phase 3 — Async ingestion and operations maturity

### Goal

실서비스 운영을 위한 비동기 작업 모델과 운영성을 강화한다.

### Main work

- queue / background worker 기반 ingest job 처리
- progress polling 및 취소/재시도 모델 설계
- tracing, metrics, structured logging 추가
- 대용량 문서/다중 사용자 환경에서의 failure mode 정리
- backup, migration, data recovery 절차 정리

### Exit criteria

- 장기 실행 ingestion을 API에서 안정적으로 운용할 수 있다.
- 운영자가 병목과 장애 지점을 관측할 수 있다.
- persistence와 vector store 관련 운영 절차가 문서화되어 있다.

## Phase 4 — MCP interface

### Goal

에이전트/도구 기반 사용 시나리오를 위해 MCP 서버를 추가한다.

### Main work

- 최소 tool set 정의: ingest, query, list_documents, get_document, delete_document 등
- tool input/output schema 설계
- 세션 컨텍스트와 auth passthrough 전략 정리
- SDK contract를 그대로 활용하는 MCP adapter 구성
- 에이전트 사용성 기준으로 응답 shaping 정리

### Exit criteria

- MCP tool이 SDK의 핵심 의미를 훼손하지 않는다.
- user scope와 권한 경계가 MCP에서도 일관된다.
- API와 MCP가 공통 core contract 위에서 독립적으로 배포 가능하다.

## Phase 5 — Storage and scale evolution

### Goal

MVP 저장 구조를 넘어 운영/확장 요구에 대응한다.

### Main work

- SQLite / Milvus Lite 유지 한계 측정
- 외부 vector DB 교체 경로 정의
- stronger metadata store 또는 managed DB 전환 검토
- tenant isolation 강화를 위한 저장 전략 검토
- 성능, 비용, 운영 복잡도 trade-off 비교 문서화

### Exit criteria

- 현재 저장 구조의 한계가 정량 또는 운영 경험으로 설명된다.
- 교체가 필요할 때 어떤 경로로 전환할지 설계가 있다.
- [[persistence-and-restart-recovery]]가 새 저장 구조에서도 유지된다.

## Cross-cutting concerns

모든 phase에서 공통으로 봐야 할 항목:

- 보안: 인증, 비밀 관리, tenant separation
- 버전 정책: SDK/API/MCP compatibility matrix
- 문서 체계: core / API / MCP 문서 분리
- 관측성: latency, failures, job progress, deletion consistency
- 개발 생산성: local dev 환경, fixtures, example apps

## Recommended near-term order

1. [[public-api-surface]] 정합성 재검토 및 error model 정리
2. acceptance/contract test 계층 정리
3. 얇은 API 서비스 생성
4. auth/user scope 분리 설계 반영
5. async ingestion/job orchestration 추가
6. MCP 최소 tool set 추가
7. 저장소/운영 구조 고도화

## Related pages

- [[public-api-surface]]
- [[rag-service-architecture]]
- [[user-scope-isolation]]
- [[persistence-and-restart-recovery]]
- [[interface-roadmap]]
- [[sdk-first-with-api-and-mcp-evaluation]]
- [[future-considerations-for-sdk-api-mcp-rag-project]]
