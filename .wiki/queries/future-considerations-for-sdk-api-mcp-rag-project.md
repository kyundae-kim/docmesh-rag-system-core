---
title: Future Considerations for SDK/API/MCP RAG Project
created: 2026-06-11
updated: 2026-08-18
type: query
tags: [roadmap, sdk, api, mcp, architecture, decision]
sources: []
confidence: medium
---

# Future Considerations for SDK/API/MCP RAG Project

## Question

이 프로젝트를 SDK 중심으로 두고 향후 API/MCP 프로젝트로 확장할 때 어떤 고려사항이 중요한가?

## High-priority considerations

### 1. Core contract stability

가장 먼저 지켜야 할 것은 [[public-api-surface]]의 안정성이다. SDK가 canonical core라면 public import 경로, 반환 타입, 주요 메서드 의미, 예외/오류 의미가 쉽게 흔들리면 안 된다. API와 MCP는 이 contract를 감싸는 계층이므로, core contract가 불안정하면 모든 인터페이스가 함께 흔들린다.

### 2. Boundary discipline

[[rag-service-architecture]] 기준으로 비즈니스 규칙은 core에, transport와 채널 특화 규칙은 API/MCP에 남겨야 한다. API나 MCP가 `internal.*` 같은 내부 구현에 직접 의존하기 시작하면 중복 구현과 강한 결합이 빠르게 커진다.

### 3. Auth vs user scope separation

[[user-scope-isolation]]은 현재 token 문자열을 그대로 user scope로 쓰지만, 서비스화되면 인증/인가와 내부 user scope 해석을 분리해야 한다. 외부 token을 그대로 내부 user_id로 쓰는 모델은 초기에는 단순하지만 장기적으로는 보안, 감사, 멀티테넌시 확장에 제약이 된다.

### 4. Persistence evolution

[[persistence-and-restart-recovery]]가 보여주듯 현재는 SQLite + Milvus Lite + local/memory storage 조합이 핵심이다. 그러나 API 서비스화 이후에는 동시성, 백업, 마이그레이션, 운영 관측성, 외부 vector DB 교체 가능성까지 함께 봐야 한다.

### 5. Async and job orchestration

현재 public surface는 비교적 단순한 sync SDK 관점에 가깝다. 하지만 실제 API에서는 대용량 ingest, 재시도, progress polling, queue 기반 실행, 장기 작업 취소 같은 비동기 운영 요구가 늘어날 가능성이 높다. 이때도 core 의미론은 유지하되 서비스 계층에서 orchestration을 추가하는 편이 맞다.

## Product and platform considerations

### 6. Versioning and compatibility

SDK, API, MCP를 분리 배포하면 버전 호환성 정책이 필요하다. 어떤 API/MCP 버전이 어떤 SDK 버전 범위를 지원하는지 명시하지 않으면 운영과 배포가 빠르게 불안정해진다.

### 7. Shared acceptance tests

현재 테스트 명세는 core 계약을 잘 정의하고 있다. 향후에는 같은 시나리오를 SDK, API, MCP에서 공통 검증하는 acceptance/contract test 계층이 필요하다. 그래야 인터페이스만 달라지고 의미는 같다는 보장을 유지할 수 있다.

### 8. Observability and operations

서비스화 이후에는 단순 기능보다 운영성이 중요해진다. ingestion 단계별 tracing, vector store 오류, generation latency, per-user usage, delete consistency, restart recovery 실패 신호를 관측 가능하게 설계해야 한다.

### 9. Multi-tenant data safety

지금도 user scope isolation은 핵심이지만, API/MCP로 확장하면 데이터 혼합 사고의 위험이 더 커진다. 저장, 검색, 삭제, progress 조회 모든 경로에서 tenant/user 경계를 테스트와 로그 양쪽으로 검증해야 한다.

### 10. Documentation split

문서도 분리 전략이 필요하다. core SDK 문서, API 문서, MCP 문서를 섞어 쓰면 소비자 경험이 나빠진다. 대신 공통 개념은 core 문서에 두고, 채널별 사용법은 각 인터페이스 문서로 분리하는 편이 좋다.

## Recommended order

1. SDK public contract와 error model 안정화
2. 공통 acceptance test 정리
3. 얇은 API 서비스 추가
4. 인증/인가와 internal user scope 해석 분리
5. 비동기 ingest/job 모델 도입
6. MCP server를 최소 tool set으로 시작
7. 필요 시 외부 vector DB / stronger persistence로 확장

## Practical rule of thumb

"도메인 규칙은 core에, 채널 규칙은 adapter에"라는 원칙을 유지하면 장기적으로 구조가 덜 무너진다. 특히 user scope, persistence semantics, delete semantics, retrieval guarantees는 SDK가 소유하고, HTTP/MCP의 입출력 형식과 인증 흐름은 각 인터페이스가 소유하는 편이 좋다.

## Related pages

- [[public-api-surface]]
- [[rag-service-architecture]]
- [[user-scope-isolation]]
- [[persistence-and-restart-recovery]]
- [[interface-roadmap]]
- [[sdk-first-with-api-and-mcp-evaluation]]
