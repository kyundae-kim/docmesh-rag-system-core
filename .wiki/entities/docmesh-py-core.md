---
title: docmesh-py-core
created: 2026-06-19
updated: 2026-08-08
type: entity
tags: [sdk, python, integration, config]
sources: []
confidence: low
---

> **Source status (2026-08-08):** The raw captures previously cited by this page were removed during wiki cleanup. Re-ingest authoritative sources before relying on these implementation-specific claims.

# docmesh-py-core

`docmesh-py-core`는 DocMesh 계열 Python 서비스가 반복적으로 구현하던 외부 서비스 client 생성, health check, lifecycle, Keycloak 인증, 오류·관측성 helper를 공통 SDK로 묶어 소비 프로젝트에서 재사용하게 하는 기반 패키지다. v0.6.0의 일반 애플리케이션 경로는 `docmesh_config`의 `RuntimePlan`을 `docmesh_py_core`의 assembly/lifespan API에 넘기는 **canonical split + assembly-first**다. 동기 서비스는 `assemble_services(plan=...)`, NATS를 포함한 비동기 lifecycle은 `await assemble_service_runtime(plan=...)` 또는 `service_lifespan(plan=...)`으로 client, startup healthcheck, rollback과 cleanup을 조립한다.

## Integration role

이 SDK는 애플리케이션이 PostgreSQL, SQLite, MinIO, NATS, Keycloak, Ollama, Milvus, Langfuse 같은 외부 의존성을 직접 초기화하는 대신 공통 초기화/검증 패턴을 따르게 만든다. 특히 FastAPI 서버, background worker, 배치/CLI 작업처럼 서로 다른 런타임에서 같은 설정 계약을 재사용하게 하는 것이 핵심 가치다.

## Architectural implications

문서상 `docmesh-py-core`의 안정적인 소비 경계는 단일 서비스 client가 아니라 [[service-factory-registry]] 중심의 조합 패턴에 있다. 또한 readiness 관점에서는 각 client의 개별 `check()`뿐 아니라 [[service-health-orchestration]] 같이 서비스 묶음을 required/optional로 분리하는 운영 패턴이 함께 중요하다.

## Public API scope

v0.6.0 API reference는 설정·plan·서비스 선택 타입의 canonical import를 `docmesh_config`에 두고, `docmesh_py_core` package root에는 client factory, `ServiceBundle`/`ServiceRuntime`, `service_lifespan`, health, lifecycle, Keycloak, catalog·문서 생성·오류 helper를 둔다. `docmesh_py_core` root는 `docmesh_config` 심볼을 재노출하지 않으며, 기존 `docmesh_py_core.config`·`settings`·`runtime_plan`·`factories`는 호환 facade다. 신규 코드는 두 package root를 분리해 import해야 한다.

## Configuration policy

v0.6.0 설정 계약은 `docmesh_config`가 모델·진단·`RuntimePlan`을 소유하고, canonical assembly API가 plan을 기준으로 선택 설정을 한 번 진단·로드한 뒤 client와 container를 조립하도록 한다. 개별 service factory는 이미 검증된 `docmesh_config` 설정 객체를 받으며 constructor kwargs·mapping·임의 SDK kwargs를 우회 입력으로 허용하지 않는다. `DOCMESH_LOG_LEVEL`은 별도 logging helper가 읽으며 `DOCMESH_HEALTHCHECK_ENABLED` 같은 전역 toggle은 지원하지 않는다. production 보안 판정과 runtime defaults는 [[settings-loading-and-validation]] 및 [[service-configuration-topology]] 수준의 설계 제약이다.

## Configuration foundation

`docmesh-config` v0.1.0은 이 SDK와 인접한 설정 foundation으로, package-root public API에서 `ServiceConfigs`, `RuntimePlan`, `diagnose_services`, `build_runtime_plan_metadata`, `mask_sensitive_value` 등을 제공한다. 8개 서비스와 98개 환경변수를 환경 전용 typed 모델로 추적하고, 외부 연결 없이 `absent`·`complete`·`partial`·`invalid` 상태와 required/alternative 선택을 진단한다. 따라서 설정 모델·preflight diagnosis·runtime 정책은 [[docmesh-config]]에, 실제 client 생성·lifecycle·네트워크 health check는 `docmesh-py-core` assembly 경계에 두는 분리가 명확해진다.

NATS의 persistent connection은 `create_nats_client()`가 반환하는 builder를 통해 필요 시 열며, 연결의 drain·close 소유권은 caller에게 있다. `SERVICE_CATALOG`과 문서 생성 helper는 설정값을 읽지 않고 deterministic한 환경 템플릿·설정 레퍼런스를 만든다.

## Related pages

- [[developing-with-docmesh-py-core]]
- [[docmesh-config]]
- [[service-factory-registry]]
- [[service-health-orchestration]]
- [[interface-roadmap]]
- [[minimizing-consumer-implementation-with-docmesh-py-core-improvements]]
