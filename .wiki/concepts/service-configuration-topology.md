---
title: Service Configuration Topology
created: 2026-06-19
updated: 2026-08-04
type: concept
tags: [config, integration, architecture, security, observability]
sources: [raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-rag-core-config-guide-2026-06-23.md, raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-env-example-v0.5.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md, raw/articles/docmesh-config-api-reference-v0.1.0-2026-08-04.md, raw/articles/docmesh-config-configuration-v0.1.0-2026-08-04.md, raw/articles/docmesh-config-examples-v0.1.0-2026-08-04.md, raw/articles/docmesh-config-env-example-v0.1.0-2026-08-04.md, raw/articles/docmesh-py-core-api-reference-v0.6.0-2026-08-04.md, raw/articles/docmesh-py-core-configuration-v0.6.0-2026-08-04.md, raw/articles/docmesh-py-core-examples-v0.6.0-2026-08-04.md, raw/articles/docmesh-py-core-env-example-v0.6.0-2026-08-04.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]
confidence: medium
---

# Service Configuration Topology

`docmesh-py-core`와 `docmesh-config`은 Keycloak, PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS를 typed config·runtime plan·client/lifecycle 계층으로 나눈다. `docmesh-config`은 설정과 preflight metadata를 소유하고, `docmesh-py-core`는 검증된 모델로 client와 runtime을 조립한다. 서비스별 timeout/retry/pool·인증·health 의미가 다르므로, 전체 env 집합을 한 번에 필수로 취급하지 않는 것이 중요하다.^[raw/articles/docmesh-config-api-reference-v0.1.0-2026-08-04.md]^[raw/articles/docmesh-py-core-api-reference-v0.6.0-2026-08-04.md]

## Canonical configuration foundation

`ServiceConfigs`는 common 설정과 서비스 설정을 bundle로 묶고 `RuntimePlan`은 required/optional 선택·대안 그룹·startup 정책을 표현한다. 이 계층은 외부 연결을 하지 않으므로 configuration topology와 실제 client/lifecycle topology를 분리해 관찰할 수 있다.^[raw/articles/docmesh-config-api-reference-v0.1.0-2026-08-04.md]

## Service-specific behavior

PostgreSQL은 host/db/user/password 필드와 pool 설정으로 URL을 조립하고, SQLite는 memory·readonly·WAL·busy timeout을 지원하며, Langfuse는 비활성화할 수 있다. NATS는 인증 방식과 persistent connection ownership이 별도 계약이다. 이런 service-specific behavior는 [[service-factory-registry]]의 반환·수명주기 차이를 함께 고려해야 한다.^[raw/articles/docmesh-py-core-configuration-v0.6.0-2026-08-04.md]^[raw/articles/docmesh-py-core-examples-v0.6.0-2026-08-04.md]

## DMS host-owned slice

`dms-core` v0.7.0은 이 topology의 설정 reader가 아니라 **주입된 document storage facade**다. DMS는 `POSTGRES_*`, `SQLITE_*`, `MINIO_*`, `DMS_METADATA_BACKEND`, `DMS_CONFIGURATION_STRICT` 같은 환경변수를 자동 해석하지 않고, host가 engine·MinIO client 또는 metadata/object/operation component를 만든 뒤 네 public factory 중 하나에 전달한다. `DmsServiceConfigs`는 host 설정 validation에 사용할 수 있지만 factory가 자동으로 소비하지 않는다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

DMS 내부 `DmsAssemblyPlan`은 connection selector가 아니라 metadata policy, file size, startup health, access policy, observer, audit hook, ownership 관련 조립 정책을 묶는다. 따라서 connection topology는 host/DocMesh composition에 남고, DMS는 document lifecycle·public/internal metadata·stable error를 책임진다. 이 경계의 세부는 [[dms-configuration-and-assembly]]에 정리한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## Security and masking

host configuration layer와 SDK logging 모두 secret/token/password/전체 DSN·URI 원문을 노출하지 않아야 한다. DMS v0.7.0의 operation event와 structured logging은 본문·credential·일반 외부 응답용 storage locator를 포함하지 않으며, host HTTP adapter는 `error_descriptor()` 또는 `recommended_http_error()`를 사용해 내부 메시지를 고정된 public descriptor로 바꾼다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Related pages

- [[dms-core]]
- [[dms-configuration-and-assembly]]
- [[settings-loading-and-validation]]
- [[keycloak-auth-service]]
- [[construction-paths-and-adapter-contracts]]
- [[docmesh-config]]
- [[docmesh-py-core]]
- [[service-health-orchestration]]
