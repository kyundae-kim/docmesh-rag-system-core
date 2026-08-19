---
title: SDK-first with API and MCP Evaluation
created: 2026-06-11
updated: 2026-08-18
type: query
tags: [sdk, api, mcp, architecture, roadmap, decision]
sources: []
confidence: medium
---

# SDK-first with API and MCP Evaluation

## Question

프로젝트를 먼저 SDK로 만들고, 이후 별도의 API 프로젝트와 MCP 프로젝트를 만들어 배포하는 접근이 개발 관점과 관리 관점에서 타당한가?

## Short answer

전반적으로 **좋은 전략**이다. 특히 현재 DocMesh RAG Core처럼 public API surface가 이미 비교적 선명하고, 내부 책임을 ingestion/retrieval/generation/metadata로 분리하려는 구조라면, SDK를 canonical core로 두고 API/MCP는 adapter product로 분리하는 방식이 가장 자연스럽다. 다만 성공 조건은 “SDK가 진짜 core contract 역할을 하도록 경계를 엄격히 관리하는 것”이다.

## Why this fits the current architecture

현재 구조는 [[public-api-surface]]와 [[rag-service-architecture]]가 보여주듯 단일 `RAGCore` 진입점과 명시적 public import 경계를 갖고 있다. 따라서 API 서버나 MCP 서버는 코어 로직을 재구현하기보다 transport, auth, async orchestration, deployment concern을 추가하는 얇은 계층으로 설계하는 편이 맞다.

## Development benefits

- 코어 로직의 단일 소스화: ingestion, retrieval, generation, persistence 규칙을 SDK 한 곳에서 검증 가능
- 테스트 재사용성: 현재 테스트 명세의 핵심 계약을 API/MCP가 그대로 상속 가능
- 빠른 실험성: Python 환경에서 새 기능을 먼저 구현·검증한 뒤 외부 인터페이스에 노출 가능
- 경계 명확화: 내부 모듈과 public surface를 분리하면 후속 인터페이스가 안정적으로 붙는다

## Management and operations benefits

- 릴리스 전략 분리: core SDK, API service, MCP server를 별도 버전/배포 단위로 운용 가능
- 장애 격리: transport 레이어 문제와 core retrieval 문제를 분리해 디버깅 가능
- 팀 분업 용이: core 팀과 interface 팀의 책임 경계가 비교적 선명해진다
- 채널 확장성: SDK를 기준으로 API, MCP, CLI 등 여러 채널을 추가하기 쉬움

## Main risks

- SDK가 너무 application-specific 해지면 API/MCP에서 다시 우회 코드가 생김
- API/MCP가 SDK contract를 우회해 내부 모듈에 직접 의존하면 중복과 결합이 커짐
- 인증/인가와 내부 `user_id` 스코프 해석이 섞이면 [[user-scope-isolation]]이 깨질 수 있음
- persistence/async 요구가 늘면서 SDK 동기 인터페이스와 서비스 운영 요구가 어긋날 수 있음

## Recommendation

가장 좋은 형태는 **SDK-first + adapter products** 이다.

1. SDK를 canonical domain/core로 둔다.
2. API 프로젝트는 HTTP transport, auth, request validation, async job orchestration에 집중한다.
3. MCP 프로젝트는 tool schema, session semantics, auth passthrough, result shaping에 집중한다.
4. 어느 인터페이스도 `rag_system_core.internal.*`에 직접 의존하지 않게 한다.
5. 공통 acceptance test를 만들어 SDK/API/MCP가 같은 기능 계약을 만족하는지 검증한다.

## Practical design rule

“비즈니스 규칙은 SDK, 채널 규칙은 API/MCP” 원칙을 유지해야 한다. user scope, persistence semantics, ingestion progress, delete semantics 같은 핵심 규칙은 core에 남기고, API/MCP는 호출 방식과 운영 모델만 다르게 가져가는 편이 좋다.

## Related pages

- [[public-api-surface]]
- [[rag-service-architecture]]
- [[user-scope-isolation]]
- [[interface-roadmap]]
