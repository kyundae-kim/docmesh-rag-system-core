---
title: docmesh-py-core
created: 2026-06-19
updated: 2026-06-19
type: entity
tags: [sdk, python, integration, config]
sources: [raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md, raw/articles/docmesh-py-core-config-guide-2026-06-19.md]
confidence: medium
---

# docmesh-py-core

`docmesh-py-core`는 DocMesh 계열 Python 서비스가 반복적으로 구현하던 설정 로드, 외부 서비스 client 생성, health check, Keycloak 인증, 민감정보 마스킹을 공통 SDK로 묶어 소비 프로젝트에서 재사용하게 하는 기반 패키지다. 문서가 전제하는 표준 사용 흐름은 `load_settings()`로 환경변수를 검증하고 `ServiceFactoryRegistry(settings)`를 생성한 뒤 필요한 서비스 client만 만들고 `check()`를 수행한 후 종료 시 `close_all()`로 자원을 정리하는 방식이다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Integration role

이 SDK는 애플리케이션이 PostgreSQL, SQLite, MinIO, NATS, Keycloak, Ollama, Milvus, Langfuse 같은 외부 의존성을 직접 초기화하는 대신 공통 초기화/검증 패턴을 따르게 만든다. 특히 FastAPI 서버, background worker, 배치/CLI 작업처럼 서로 다른 런타임에서 같은 설정 계약을 재사용하게 하는 것이 핵심 가치다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Architectural implications

문서상 `docmesh-py-core`의 안정적인 소비 경계는 단일 서비스 client가 아니라 [[service-factory-registry]] 중심의 조합 패턴에 있다. 또한 readiness 관점에서는 각 client의 개별 `check()`뿐 아니라 [[service-health-orchestration]] 같이 서비스 묶음을 required/optional로 분리하는 운영 패턴이 함께 중요하다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Public API scope

API 가이드는 패키지 루트 import 경계를 보다 명시적으로 정의한다. 일반 사용자는 `docmesh_py_core` 루트에서 `Settings`, `ServiceFactoryRegistry`, `ServiceClientWrapper`, `NatsConnectionBuilder`, `KeycloakAuthService`, `check_all_services`, `mask_sensitive_value`, `build_settings_snapshot` 같은 public 심볼을 직접 가져오고, 하위 모듈 직접 import는 예외적 상황으로 제한하는 것이 권장된다.^[raw/articles/docmesh-py-core-api-guide-2026-06-19.md]

## Configuration policy

설정 가이드는 이 SDK의 환경변수 정책을 더 구체화한다. 모든 설정은 환경변수에서 읽고, 공백 문자열은 미설정으로 간주하며, boolean/숫자형은 정규화와 범위 검증을 거친다. 또한 TLS 검증 기본 유지, 선택 기능의 비활성화 허용, 민감정보 마스킹, 운영/통합 테스트 설정 분리 같은 운영 규칙이 [[settings-loading-and-validation]] 및 [[service-configuration-topology]] 수준의 설계 제약으로 제시된다.^[raw/articles/docmesh-py-core-config-guide-2026-06-19.md]

## Related pages

- [[service-factory-registry]]
- [[service-health-orchestration]]
- [[interface-roadmap]]
