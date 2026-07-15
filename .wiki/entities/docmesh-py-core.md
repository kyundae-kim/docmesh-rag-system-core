---
title: docmesh-py-core
created: 2026-06-19
updated: 2026-07-16
type: entity
tags: [sdk, python, integration, config]
sources: [raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md, raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md]
confidence: medium
---

# docmesh-py-core

`docmesh-py-core`는 DocMesh 계열 Python 서비스가 반복적으로 구현하던 설정 로드, 외부 서비스 client 생성, health check, Keycloak 인증, 민감정보 마스킹을 공통 SDK로 묶어 소비 프로젝트에서 재사용하게 하는 기반 패키지다. v0.2.0 API reference의 일반 애플리케이션 경로는 **assembly-first**다. 동기 서비스는 `assemble_services()`, NATS를 포함한 비동기 lifecycle은 `await assemble_service_runtime()`으로 설정 탐지·필수/대안 서비스 검증·client 생성·선택적 startup check를 조립하고, 반환된 `ServiceBundle`/`ServiceRuntime` context manager가 lifecycle을 관리한다.^[raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md]

## Integration role

이 SDK는 애플리케이션이 PostgreSQL, SQLite, MinIO, NATS, Keycloak, Ollama, Milvus, Langfuse 같은 외부 의존성을 직접 초기화하는 대신 공통 초기화/검증 패턴을 따르게 만든다. 특히 FastAPI 서버, background worker, 배치/CLI 작업처럼 서로 다른 런타임에서 같은 설정 계약을 재사용하게 하는 것이 핵심 가치다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Architectural implications

문서상 `docmesh-py-core`의 안정적인 소비 경계는 단일 서비스 client가 아니라 [[service-factory-registry]] 중심의 조합 패턴에 있다. 또한 readiness 관점에서는 각 client의 개별 `check()`뿐 아니라 [[service-health-orchestration]] 같이 서비스 묶음을 required/optional로 분리하는 운영 패턴이 함께 중요하다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Public API scope

v0.2.0 API reference는 패키지 루트 import 경계를 `__all__` 기준으로 명시한다. `ServiceConfigs`, `ServiceBundle`, `ServiceRuntime`, `ServiceClientWrapper`, 각 `*Config`, `assemble_services`, `assemble_service_runtime`, `load_service_configs`, `load_available_service_configs`, `check_all_services`, `async_check_all_services`, `close_service_clients`, `async_close_service_clients` 및 Keycloak API가 안정적인 공개 소비면이다. 하위 모듈 직접 import보다 이 루트 경계를 사용해야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md]

## Configuration policy

v0.2.0 설정 계약은 환경변수에서 공백·boolean·숫자형을 엄격히 검증하고, `load_service_configs()`/`load_available_service_configs()`로 필요한 서비스만 검증하게 한다. production 판정은 `DOCMESH_SECURITY_MODE` 또는 `DOCMESH_ENV`와 alias 목록으로 결정하며 Keycloak·MinIO·Milvus의 TLS 관련 제약을 강제한다. 이 운영 규칙과 `RuntimeDefaults`를 통한 설정 보존은 [[settings-loading-and-validation]] 및 [[service-configuration-topology]] 수준의 설계 제약이다.^[raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md]

## Related pages

- [[developing-with-docmesh-py-core]]
- [[service-factory-registry]]
- [[service-health-orchestration]]
- [[interface-roadmap]]
