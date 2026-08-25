---
title: Service Configuration Topology
created: 2026-06-19
updated: 2026-08-25
type: concept
tags: [config, integration, architecture, security, observability]
sources: [raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md, raw/articles/dms-core-examples-v0.9.0-2026-08-18.md, raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md, raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]
confidence: medium
---

# Service Configuration Topology

`docmesh-py-core`와 `docmesh-config`은 Keycloak, PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS를 typed config·runtime plan·client/lifecycle 계층으로 나눈다. `docmesh-config`은 설정과 preflight metadata를 소유하고, `docmesh-py-core`는 검증된 모델로 client와 runtime을 조립한다. 서비스별 timeout/retry/pool·인증·health 의미가 다르므로 전체 env 집합을 한 번에 필수로 취급하지 않는 것이 중요하다.

## Canonical configuration foundation

`ServiceConfigs`는 common 설정과 서비스 설정을 bundle로 묶고 `RuntimePlan`은 required/optional 선택·대안 그룹·startup 정책을 표현한다. 이 계층은 외부 연결을 하지 않으므로 configuration topology와 실제 client/lifecycle topology를 분리해 관찰할 수 있다.

## DMS host-owned slice

`dms-core` v0.10.0은 이 topology의 설정 reader가 아니라 **주입된 document storage facade**다. DMS는 `POSTGRES_*`, `SQLITE_*`, `MINIO_*`, `DMS_METADATA_BACKEND`, `DMS_CONFIGURATION_STRICT` 같은 환경변수를 자동 해석하지 않고, host가 engine·MinIO client 또는 metadata/object/operation component를 만든 뒤 `DocumentManagementSDKFactory` 또는 `DefaultDocumentManagementSDK`에 전달한다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

DMS가 조립 시 자체 확인하는 범위는 지원 dialect, non-empty bucket, `max_file_size` 같은 SDK 입력 계약이다. 연결 readiness, engine/client/component의 생성과 종료, 서비스별 health는 host/DocMesh composition에 남는다. v0.7.0의 `DmsAssemblyPlan`·service check·health facade를 v0.10.0 현재 API로 전제하지 않는다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]

## v0.10 async and user-scope slice

native async 조립은 `AsyncDocumentManagementSDKFactory`가 담당하고, sync factory와 compatibility async wrapper를 같은 경로로 간주하지 않는다. `AccessContext.user_id`와 scoped operation context는 DMS document·object·operation·cursor 범위를 통일하지만, 전체 service readiness와 credential lifecycle은 여전히 host composition이 관리한다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

## Security and transport masking

host configuration layer와 SDK logging 모두 secret/token/password/전체 DSN·URI 원문을 노출하지 않아야 한다. v0.10.0의 operation event와 recovery audit 경계에도 document body, credential, 외부 응답용 storage locator를 넣지 않으며, host HTTP adapter는 DMS의 stable `code`, `category`, `retryable`을 자체 public response 규칙으로 바꾼다. DMS는 HTTP status나 response body를 결정하지 않는다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

## Related pages

- [[dms-core]]
- [[dms-configuration-and-assembly]]
- [[settings-loading-and-validation]]
- [[keycloak-auth-service]]
- [[construction-paths-and-adapter-contracts]]
- [[docmesh-config]]
- [[docmesh-py-core]]
- [[service-health-orchestration]]
