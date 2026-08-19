---
title: Service Factory Registry
created: 2026-06-19
updated: 2026-08-18
type: concept
tags: [sdk, python, integration, config, decision]
sources: []
confidence: medium
---

# Service Factory Registry

이 페이지의 이전 registry 중심 설명은 초기 SDK 가이드를 반영한다. v0.6.0의 현재 공개 경계는 `ServiceFactoryRegistry`가 아니라 `RuntimePlan` 기반 assembly/lifespan API다. `docmesh_config`가 설정·plan·진단을 소유하고, `assemble_services(plan=...)`, `assemble_service_runtime(plan=...)`, `service_lifespan(plan=...)`이 검증된 config를 client/container·startup healthcheck·rollback·cleanup으로 변환한다.

## Why this boundary matters

이 패턴은 애플리케이션 코드가 PostgreSQL, SQLite, MinIO, NATS 같은 외부 client 생성 세부사항에 직접 결합되는 것을 줄여 준다. 문서는 명시적 backend selector보다 실제 환경변수 존재 여부로 서비스를 선택하는 방식을 권장하며, 예를 들어 `settings.sqlite`가 있으면 SQLite client를, 아니면 PostgreSQL client를 선택하는 식의 분기가 대표적이다.

## Configuration coupling

설정 가이드는 registry 앞단의 `load_settings()`가 단순 파서가 아니라 서비스별 필수값, 조건부 필수값, 기본값, 보안 규칙을 함께 검증하는 계층임을 분명히 한다. 따라서 registry는 단순 factory라기보다 [[settings-loading-and-validation]]에서 이미 정규화된 설정 객체를 전제로 동작하며, 서비스 선택도 별도 backend selector보다 `POSTGRES_*`, `SQLITE_*` 같은 실제 설정 존재 여부에 결합된다.

## Configuration and assembly ownership

`docmesh-config` v0.1.0은 환경변수 전용 typed config, `ServiceConfigs`, `RuntimePlan`, `diagnose_services()`와 secret-safe metadata를 제공하지만 외부 서비스 연결이나 client 생성을 수행하지 않는다. 따라서 [[docmesh-config]]가 설정·preflight·선택 정책을 소유하고, `docmesh-py-core`의 assembly API가 그 결과를 client/lifecycle로 변환하는 계층 분리가 소비자 구현의 결합도를 낮춘다.

## Usage constraints

registry가 반환하는 값은 서비스마다 성격이 다를 수 있다. 특히 `create_client("nats")`는 즉시 연결된 동기 client가 아니라 `NatsConnectionBuilder`를 돌려주므로 `await builder.connect()` 또는 `await builder.check()` 패턴을 강제한다. 따라서 소비 프로젝트는 서비스별 반환 계약 차이를 흡수하는 래퍼 계층을 둘지 여부를 검토해야 한다.

## Catalog and ownership

v0.6.0은 `SERVICE_CATALOG`과 `ServiceDescriptor`로 서비스별 config type·factory·sync 지원·환경 요구사항을 immutable metadata로 제공하고, `generate_environment_template()`과 `generate_configuration_reference()`로 deterministic 문서를 생성한다. 모든 `create_*_client()` factory는 이미 검증된 `docmesh_config` 모델을 받고 임의 kwargs나 test override를 공개하지 않는다. NATS의 persistent connection은 `connect()` 호출자가 소유하며 builder 자체는 자원을 소유하지 않는다.

## RAG composition implications

현재 repository에는 `bootstrap_rag_core(...)`나 `bootstrap_rag_core_from_env(...)` 같은 environment-based RAG entrypoint가 없다. `load_docmesh_settings()`와 service assembly helper는 하위 설정·client 조립 경계로 남아 있고, 최종 Core 생성은 `DocmeshRAGServiceFactory.from_clients(...)` 또는 `from_host_clients(...)` 뒤 `create_rag_core()`를 호출하는 명시적 경로가 담당한다. 따라서 registry 중심의 과거 bootstrap 설명은 현재 public contract가 아니라 historical context로 취급해야 하며, 현재 조립 경계는 [[construction-paths-and-adapter-contracts]]와 [[public-api-surface]]에서 확인한다.

## Return contract

v0.6.0 direct assembly의 반환 경계는 서비스별 `ServiceClientWrapper`/`NatsConnectionBuilder`와 `ServiceBundle` 또는 `ServiceRuntime`이다. 일반 앱은 `service_lifespan()` 또는 context manager가 lifecycle을 소유하는 bundle/runtime을 사용해야 하며, NATS persistent connection의 drain/close는 caller가 수행한다. `get()`·`require()`·`get_client()`는 선택/초기화 실패를 서로 다른 수준으로 표현하고, `require_client()`는 concrete client type을 검증한다.

## Operational notes

권장 종료 패턴은 `with ServiceBundle` 또는 `async with service_lifespan(...)`을 사용해 engine/client/flush/dispose를 한 번에 정리하는 것이다. assembly 또는 startup healthcheck가 실패해도 이미 만든 client를 best-effort rollback하고, 전체 close 실패는 `ServiceCloseError.failures`에 집계한다. 이 수명주기 관리 패턴은 [[service-health-orchestration]]과 결합될 때 startup readiness와 shutdown cleanup을 한 흐름으로 정리할 수 있다.

## Related pages

- [[construction-paths-and-adapter-contracts]]
- [[docmesh-config]]
- [[docmesh-py-core]]
- [[service-health-orchestration]]
- [[public-api-surface]]
