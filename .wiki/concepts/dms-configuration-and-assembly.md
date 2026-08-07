---
title: DMS Configuration and Assembly
created: 2026-07-27
updated: 2026-08-04
type: concept
tags: [config, sdk, integration, persistence, security, observability]
sources: [raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]
confidence: medium
---

# DMS Configuration and Assembly

## Host-owned configuration boundary

v0.7.0에서 DMS는 환경변수·`.env`를 읽거나 PostgreSQL/SQLite/MinIO connection을 직접 만들지 않는다. 호스트 애플리케이션이 설정 파일·environment·secret manager를 읽고 engine과 MinIO client 또는 metadata/object/operation store를 만든 뒤 DMS factory에 주입한다. `DmsServiceConfigs`는 host 설정 계층에서 사용할 수 있는 immutable value object이지만, public factory가 이를 자동 소비하는 조립 경로는 아니다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

따라서 v0.6.0에 기록된 environment factory, `ServiceConfigs` 자동 조립, `diagnose_environment()` 기반 선택은 v0.7.0 current documented contract와 분리해 읽어야 한다. v0.7.0의 `metadata_backend`와 `strict_configuration`은 host가 공유할 정책 metadata이지 process environment에서 backend를 찾는 selector가 아니다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## Factory paths

| 조립 방식 | 공개 factory | host 입력 | ownership 기본값 |
| --- | --- | --- | --- |
| client sync | `create_sdk_from_clients()` | SQLAlchemy `Engine`, MinIO client, bucket | engine/client caller-owned |
| component sync | `create_sdk_from_components()` | metadata/object store, optional operation store | component caller-owned |
| client async | `create_async_sdk_from_clients()` | client sync와 동일 | sync path와 동일 |
| component async | `create_async_sdk_from_components()` | component sync와 동일 | sync path와 동일 |

client factory는 engine dialect가 `postgresql` 또는 `sqlite`인지, bucket이 비어 있지 않은지를 검사하고 engine에서 persistent upload operation store를 조립한다. component factory는 host가 operation store와 service check를 선택적으로 제공한다. 둘 다 keyword-only 정책 option을 받아 같은 document lifecycle을 제공한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

## DmsAssemblyPlan

`DmsAssemblyPlan`은 metadata backend policy, strict flag, validator와 size/depth, `max_file_size`, startup check/timeout, logger, recovery audit hook, operation observer, access policy를 immutable하게 묶는다. plan을 전달하면 plan 값이 개별 factory option보다 우선하므로 두 입력 경로의 정책이 갈라지지 않게 하나의 plan을 공유해야 한다.

- `check_on_startup=False`가 기본이며, true이면 등록한 `service_checks`를 factory 직후 실행한다.
- 실패·timeout은 `HealthCheckFailedError`가 되고 `service`·`reason`을 제공한다.
- startup 실패 시 SDK-owned resource만 등록 역순으로 rollback한다.
- runtime `check_health()`는 예외 대신 service별 latency/error를 포함한 `HealthStatus`를 반환한다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Resource ownership and cleanup

기본 주입 client/component는 caller-owned라서 SDK가 자동으로 닫지 않는다. 종료 책임을 넘길 때만 `close_callbacks` 또는 `ManagedResource(ownership=ResourceOwnership.SDK, close/aclose=...)`를 등록한다. SDK-owned 자원은 등록 역순으로 한 번씩 정리하고, 한 cleanup이 실패해도 나머지를 시도한 뒤 모든 예외를 `ResourceCleanupError.errors`에 모은다. `close()`·`aclose()`와 `with`·`async with`는 반복 종료에 안전하며 scoped facade는 shared SDK lifecycle을 소유하지 않는다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

## Security and host integration

DMS가 연결값을 읽지 않는다는 것은 secret 책임이 사라진다는 뜻이 아니다. host configuration layer가 endpoint·credential을 검증하고 log/error에서 masking해야 하며, DMS logger/operation event에도 본문·token·password를 기록하지 않는다. DMS 자체는 HTTP server가 아니므로 host API가 `error_descriptor()` 또는 `recommended_http_error()`로 stable error를 외부 응답에 투영한다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

## Related pages

- [[dms-core]]
- [[service-configuration-topology]]
- [[settings-loading-and-validation]]
- [[service-health-orchestration]]
- [[construction-paths-and-adapter-contracts]]
- [[applying-dms-core-as-document-storage]]
