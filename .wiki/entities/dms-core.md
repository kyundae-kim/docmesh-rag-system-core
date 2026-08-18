---
title: dms-core
created: 2026-07-27
updated: 2026-08-18
type: entity
tags: [sdk, python, api, config, integration, persistence, observability]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md, raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md, raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]
confidence: medium
---

# dms-core

`dms-core`는 문서 metadata와 object storage를 하나의 document-management facade로 묶어 업로드·조회·삭제·reset·정합성 복구를 제공하는 Python SDK다. v0.9.0의 권장 소비 경계는 `from dms import ...`이며, SDK는 host가 만든 SQLAlchemy `Engine`, MinIO client, 또는 storage component를 주입받는다. DMS는 독립 실행형 API 서버가 아니고, 주입 자원의 생성·readiness·종료도 소유하지 않는다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## v0.9.0 public surface

기본 조립은 `DocumentManagementSDKFactory(engine=..., minio_client=..., bucket_name=...)`이고, 이미 준비된 adapter를 사용할 때는 `DefaultDocumentManagementSDK(metadata_store=..., object_store=..., operation_store=...)`를 직접 만든다. package root에는 `dms.__all__` 기준 54개 공개 이름이 있으며, sync facade·async facade·sync/async scoped facade가 26개 document 작업을 같은 의미로 제공한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

현재 공개 계약에는 환경변수에서 client를 만드는 factory, `check_health()`, facade 전역 `close()`/`aclose()`, HTTP response 모델, 내부 store 구현이 포함되지 않는다. 따라서 v0.7.0에 기록된 `DmsAssemblyPlan`·resource ownership·health facade를 v0.9.0 runtime API로 재사용하지 말고, host composition과 transport adapter에서 별도로 책임져야 한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Integration role

RAG 시스템에 적용할 때는 원문 bytes/file/known-size stream, 파일 크기·checksum·문서 상태, 원문 삭제 및 metadata/object 정합성 복구를 DMS가 소유하는 경계로 둘 수 있다. RAG `MetadataStore`는 chunk·embedding·ingestion progress·user-scope 같은 RAG 고유 상태를 소유하고, 두 영역은 공개 `document_id`로 연결한다. 일반 결과인 `PublicDocumentMetadata`에는 내부 `storage_key`가 구조적으로 없으며, 저장 위치는 internal metadata·inspection·recovery 같은 관리 경로에서만 다룬다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Lifecycle and operations

v0.9.0은 bytes, file path, 정확한 크기를 선언한 동기 binary stream upload, persistent `operation_store` 기반 idempotency, opaque cursor pagination, sync/async content stream, copy helper, soft/hard delete, 전체 data reset, dry-run reconciliation plan을 공개한다. metadata는 application-owned opaque value이고 idempotency fingerprint에는 포함되지 않는다. `UploadOperationState`는 root export가 아니므로 operation 결과의 `state.value`를 사용한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

`AccessContext`·`DocumentAccessPolicy`, `DmsOperationContext`, `OperationObserver`, 기능별 capability protocol, stable `DmsError` fields는 host가 권한·관찰·transport mapping을 조립하는 seam이다. Observer와 recovery audit hook의 실패는 원래 document 작업을 덮지 않으며, host transport가 `code`, `category`, `retryable` 및 오류별 추가 정보를 자체 응답 규칙으로 변환한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

## Version transition and evidence boundary

v0.6.0과 v0.7.0 raw 문서는 과거 환경/service-config factory 및 assembly-plan 중심 설계를 기록한다. v0.9.0 API/Examples 문서는 `dms-core` commit `f7a40f1`, package version `0.9.0`을 기준으로 하며, persistent idempotency replay/conflict/lookup 일부는 현재 checkout의 test가 `source-only` gap임을 추적성 matrix에 명시한다. 이 페이지는 GitHub Wiki 문서 기반이며 설치 package나 소비 repository를 live 실행해 검증한 결과는 아니다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

GitHub Wiki URL은 사용자가 제공한 versioned page URL을 `source_url`로 보존했지만 immutable wiki commit URL은 아니므로, raw body는 ingest 시점의 해당 Wiki revision으로 해석한다.

## Related pages

- [[dms-document-lifecycle]]
- [[dms-metadata-and-recovery]]
- [[dms-configuration-and-assembly]]
- [[public-api-surface]]
- [[service-configuration-topology]]
- [[applying-dms-core-as-document-storage]]
- [[verifying-dms-core-contract]]
