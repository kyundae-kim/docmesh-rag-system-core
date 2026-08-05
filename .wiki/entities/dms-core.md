---
title: dms-core
created: 2026-07-27
updated: 2026-08-04
type: entity
tags: [sdk, python, api, config, integration, persistence, observability]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]
confidence: medium
---

# dms-core

`dms-core`는 문서 metadata와 object storage를 하나의 document-management facade로 묶어 업로드·조회·삭제·복구를 제공하는 Python SDK다. v0.7.0의 안정된 소비 경계는 `dms` package root이며, SDK가 PostgreSQL·SQLite·MinIO client를 직접 찾는 것이 아니라 호스트가 만든 client 또는 저장소 component를 주입한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

## Integration role

RAG 시스템에 적용할 때는 원문 bytes/file/known-size stream, 크기와 문서 상태, 원문 삭제 및 정합성 복구를 DMS가 소유하는 경계로 둘 수 있다. checksum은 bytes/file 업로드와 본문 복사처럼 현재 계약이 지원하는 경로에서 DMS가 다룬다. RAG `MetadataStore`는 chunk·embedding·ingestion progress·user-scope 같은 RAG 고유 상태를 소유하고, 두 영역은 공개 `document_id`로 연결한다. 일반 조회 결과인 `PublicDocumentMetadata`에는 내부 `storage_key`가 구조적으로 없으며, 저장 위치는 internal metadata·inspection·recovery 같은 관리 경로에서만 다룬다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## v0.7.0 public surface

- 조립: `create_sdk_from_clients()` / `create_async_sdk_from_clients()`, `create_sdk_from_components()` / `create_async_sdk_from_components()`
- facade: `DefaultDocumentManagementSDK`, `AsyncDocumentManagementSDK`, immutable scoped facade
- 공통 정책: `DmsAssemblyPlan`, `ManagedResource`, `ResourceOwnership`, `AccessContext`, `DocumentAccessPolicy`, `DmsOperationContext`
- 작업: bytes·file·known-size stream upload, operation store를 사용하는 bytes idempotency, cursor pagination, sync/async content stream, copy helper, soft/hard delete, 전역 reset, reconciliation
- 운영: `HealthStatus`, `OperationObserver`, stable `DmsError` descriptor와 transport-neutral HTTP projection

기능별 `DocumentWriter`, `DocumentReader`, `DocumentLister`, `DocumentDeleter`, `DataResetter`, `DocumentHealth` protocol도 공개되어 concrete SDK 전체에 결합하지 않는 host 함수와 test double을 구성할 수 있다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Assembly and ownership

현재 권장 조립은 다음 경계다.

1. 호스트가 설정·secret manager에서 값을 읽고 SQLAlchemy `Engine`과 MinIO client를 만들거나 metadata/object/operation store를 준비한다.
2. DMS factory에 주입하고 필요하면 `DmsAssemblyPlan`, `service_checks`, access policy, observer, `managed_resources`/`close_callbacks`를 함께 전달한다.
3. 기본 주입 자원은 caller-owned이며, `ManagedResource(ownership=ResourceOwnership.SDK, ...)` 또는 `close_callbacks`로 명시한 자원만 SDK가 역순으로 정리한다.
4. `with sdk` 또는 `async with sdk`의 종료 경계를 애플리케이션 lifecycle에 연결한다. scoped facade는 shared SDK lifecycle을 소유하지 않는다.

`DmsServiceConfigs`는 호스트 설정 계층에서 사용할 수 있는 immutable value object지만, v0.7.0 public factory가 이를 자동으로 읽거나 client를 생성하지는 않는다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

## Version transition

v0.6.0 raw 문서에는 환경·`ServiceConfigs`·환경 진단을 포함한 조립 경로가 기록되어 있다. 그러나 v0.7.0 configuration 문서는 환경변수, `.env`, DMS connection 생성, `create_sdk_from_environment()`/service-config 자동 조립을 현재 공개 계약에서 제외한다. 따라서 v0.7.0을 현재 문서 계약으로 사용할 때는 기존 환경 factory 전제를 그대로 재사용하지 말고, 설치 package의 실제 signature를 별도로 확인해야 한다.

## Related pages

- [[dms-document-lifecycle]]
- [[dms-metadata-and-recovery]]
- [[dms-configuration-and-assembly]]
- [[public-api-surface]]
- [[service-configuration-topology]]
- [[applying-dms-core-as-document-storage]]
- [[verifying-dms-core-contract]]
