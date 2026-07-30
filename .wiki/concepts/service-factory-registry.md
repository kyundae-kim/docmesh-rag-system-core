---
title: Service Factory Registry
created: 2026-06-19
updated: 2026-07-16
type: concept
tags: [sdk, python, integration, config, decision]
sources: [raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md, raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-rag-core-api-reference-2026-06-23.md, raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md]
confidence: medium
---

# Service Factory Registry

이 페이지의 이전 registry 중심 설명은 초기 SDK 가이드를 반영한다. v0.2.0의 현재 공개 경계는 `ServiceFactoryRegistry`가 아니라 assembly API다. 동기 lifecycle은 `assemble_services()`가, NATS를 포함한 async lifecycle은 `assemble_service_runtime()`이 설정 로드·available 서비스 탐지·`required`/`one_of` 검증·client 생성·선택적 startup healthcheck를 하나의 조정 계층으로 제공한다.^[raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md]

## Why this boundary matters

이 패턴은 애플리케이션 코드가 PostgreSQL, SQLite, MinIO, NATS 같은 외부 client 생성 세부사항에 직접 결합되는 것을 줄여 준다. 문서는 명시적 backend selector보다 실제 환경변수 존재 여부로 서비스를 선택하는 방식을 권장하며, 예를 들어 `settings.sqlite`가 있으면 SQLite client를, 아니면 PostgreSQL client를 선택하는 식의 분기가 대표적이다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Configuration coupling

설정 가이드는 registry 앞단의 `load_settings()`가 단순 파서가 아니라 서비스별 필수값, 조건부 필수값, 기본값, 보안 규칙을 함께 검증하는 계층임을 분명히 한다. 따라서 registry는 단순 factory라기보다 [[settings-loading-and-validation]]에서 이미 정규화된 설정 객체를 전제로 동작하며, 서비스 선택도 별도 backend selector보다 `POSTGRES_*`, `SQLITE_*` 같은 실제 설정 존재 여부에 결합된다.^[raw/articles/docmesh-py-core-config-guide-2026-06-19.md]

## Usage constraints

registry가 반환하는 값은 서비스마다 성격이 다를 수 있다. 특히 `create_client("nats")`는 즉시 연결된 동기 client가 아니라 `NatsConnectionBuilder`를 돌려주므로 `await builder.connect()` 또는 `await builder.check()` 패턴을 강제한다. 따라서 소비 프로젝트는 서비스별 반환 계약 차이를 흡수하는 래퍼 계층을 둘지 여부를 검토해야 한다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## RAG bootstrap implications

RAG Core API reference는 `bootstrap_rag_core(...)`가 settings를 직접 로드하지 않고 `service_factory`를 통해 embedding/generation/vector/metadata/storage/chunker를 조립한다고 명시한다. 또한 DocMesh 경로 예시에서 `load_docmesh_settings()`와 `create_service_registry(settings)`를 먼저 호출한 뒤 `DocmeshRAGServiceFactory(settings=settings, registry=registry)`를 구성한다. 따라서 registry는 RAG bootstrap 경로에서 선택적 주변도구가 아니라 [[construction-paths-and-adapter-contracts]]와 [[public-api-surface]]를 잇는 실제 조립 전제조건이다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-23.md]

## Return contract

v0.2.0 direct factory의 반환 규칙은 `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`가 대체로 `ServiceClientWrapper`, 비활성 Langfuse가 `None`, NATS가 `NatsConnectionBuilder`라는 점이다. 그러나 일반 앱은 factory를 직접 조합하기보다 `ServiceBundle` 또는 `ServiceRuntime`을 사용해야 하며, NATS는 동기 bundle에서 제외되어 async runtime으로 조립한다. `factory_overrides` 및 keyword-only factory hooks는 테스트·특수 실행 환경의 명시적 대체 지점이다.^[raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md]

## Operational notes

권장 종료 패턴은 애플리케이션 수명주기 끝에서 `registry.close_all()`을 호출해 engine/client/flush/dispose를 한 번에 정리하는 것이다. 이 수명주기 관리 패턴은 [[service-health-orchestration]]과 결합될 때 startup readiness와 shutdown cleanup을 한 흐름으로 정리할 수 있다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Related pages

- [[construction-paths-and-adapter-contracts]]
- [[docmesh-py-core]]
- [[service-health-orchestration]]
- [[public-api-surface]]
