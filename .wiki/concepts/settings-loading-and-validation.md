---
title: Settings Loading and Validation
created: 2026-06-19
updated: 2026-08-04
type: concept
tags: [config, sdk, python, security, decision]
sources: [raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-rag-core-config-guide-2026-06-23.md, raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-env-example-v0.5.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/docmesh-config-api-reference-v0.1.0-2026-08-04.md, raw/articles/docmesh-config-configuration-v0.1.0-2026-08-04.md, raw/articles/docmesh-config-examples-v0.1.0-2026-08-04.md, raw/articles/docmesh-config-env-example-v0.1.0-2026-08-04.md, raw/articles/docmesh-py-core-api-reference-v0.6.0-2026-08-04.md, raw/articles/docmesh-py-core-configuration-v0.6.0-2026-08-04.md, raw/articles/docmesh-py-core-examples-v0.6.0-2026-08-04.md, raw/articles/docmesh-py-core-env-example-v0.6.0-2026-08-04.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]
confidence: medium
---

# Settings Loading and Validation

`docmesh-config` v0.1.0은 canonical 설정 package로서 process environment에서 typed config를 읽고 `ServiceConfigs`와 `RuntimePlan`으로 선택·검증한다. `docmesh-py-core`는 이 결과를 client/assembly/lifecycle로 변환하며, partial 설정·잘못된 bool/int/range·production transport 보안 위반을 구조화된 오류로 다룬다.^[raw/articles/docmesh-config-api-reference-v0.1.0-2026-08-04.md]^[raw/articles/docmesh-py-core-configuration-v0.6.0-2026-08-04.md]

## Validation scope

검증 대상은 단순 필수 여부를 넘어 조건부 필수 규칙과 보안 규칙까지 포함한다. 예를 들어 Langfuse 비활성화, PostgreSQL field 조합, Keycloak credential grant, production TLS 설정은 서비스별 선택 경로에서 다르게 적용된다. `RuntimePlan.healthcheck`는 network 실행 결과가 아니라 runtime이 사용할 startup/readiness policy다.^[raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md]^[raw/articles/docmesh-py-core-api-reference-v0.6.0-2026-08-04.md]

## DMS v0.7.0 configuration boundary

DMS v0.7.0은 environment를 읽거나 `diagnose_environment()`를 제공하는 설정 SDK가 아니다. host가 environment·config file·secret manager를 읽고 다음을 자체 검증한 뒤 client/component를 주입해야 한다.

- SQLAlchemy dialect는 `postgresql` 또는 `sqlite`
- MinIO bucket은 비어 있지 않음
- `DmsServiceConfigs`를 사용할 경우 MinIO 필수값과 SQLite/PostgreSQL 중 정확히 하나
- `DmsAssemblyPlan`의 backend policy, size/depth, max file size, startup timeout은 양수·허용 enum
- credential과 endpoint는 log/error에 secret-safe하게 남김

`DmsServiceConfigs`는 immutable value object로 validation에 사용할 수 있지만 public DMS factory가 이 값을 자동 소비하거나 client를 생성하지 않는다. v0.6.0 raw의 environment factory/diagnosis 설명은 versioned historical context이며 v0.7.0 current factory contract와 섞으면 안 된다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## Assembly and runtime checks

DMS의 `service_checks`는 component factory에 주입되고, `DmsAssemblyPlan(check_on_startup=True)`일 때 조립 직후 실행된다. startup failure/timeout은 `HealthCheckFailedError`와 service/reason으로 표현되며 SDK-owned resource만 rollback한다. 이후 `check_health()`는 모든 check를 시도하고 service별 `HealthStatus`를 반환하므로 startup mandatory failure와 runtime observation을 구분한다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Operational policy

DMS access control도 host-defined `AccessContext`·`DocumentAccessPolicy`로 조립하며, observer/audit hook failure가 원래 작업을 덮지 않도록 한다. HTTP adapter는 DMS exception text를 직접 노출하지 않고 stable `code`, `category`, `retryable`을 `error_descriptor()`/`recommended_http_error()`로 변환한다. 즉 settings validation, resource assembly, document policy, transport error는 서로 다른 ownership boundary에 남겨야 한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## Related pages

- [[first-success-configuration]]
- [[docmesh-config]]
- [[keycloak-auth-service]]
- [[docmesh-py-core]]
- [[service-factory-registry]]
- [[service-configuration-topology]]
- [[dms-configuration-and-assembly]]
- [[dms-core]]
