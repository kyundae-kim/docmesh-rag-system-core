---
title: DMS Metadata and Recovery
created: 2026-07-27
updated: 2026-08-18
type: concept
tags: [sdk, schema, persistence, security, api, testing]
sources: [raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md, raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]
confidence: medium
---

# DMS Metadata and Recovery

## Public and internal metadata

v0.9.0은 `PublicDocumentMetadata`와 `DocumentMetadata`를 구조적으로 분리한다. 일반 upload/get/list/content 결과에는 `storage_key`가 없고, `public_metadata()`·`to_public_dict()`·JSON schema도 public-safe projection을 유지한다. `DocumentMetadata.storage_key`는 `get_internal_document_metadata()`, `inspect_document()`, recovery candidate와 reconciliation 같은 명시적 관리 경계에서만 사용한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

`DocumentMetadata`를 일반 HTTP 응답, operation event, tenant callback에 그대로 전달하지 않는다. `to_dict()`는 기존 `extra_metadata` field명을 유지하고 `to_public_dict()`는 외부 canonical `metadata` field를 사용한다. public schema와 canonical dump에는 `storage_key`가 없어야 한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Application-owned metadata

v0.9.0의 upload metadata와 scoped default metadata는 `object` 타입의 application-owned 값이다. DMS는 metadata 업무 schema, 민감 key 차단, JSON serialization, normalization을 정의하거나 검증하지 않으며 입력 값을 idempotency fingerprint에도 포함하지 않는다. 따라서 기존 v0.7.0 문서에 있던 `DefaultMetadataPolicy`·`StructuredMetadataValidator` 전제는 v0.9.0 current API에 자동 적용되는 계약으로 간주하지 않는다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Inspection and reconciliation

`inspect_document()`은 metadata가 없어도 `DocumentNotFoundError` 대신 `metadata_exists=False`, `issue=METADATA_MISSING`인 typed `DocumentInspection`을 반환한다. `RecoveryIssue`는 metadata/object 부재, 불완전 삭제, failed 상태를 구분하고, recovery candidate는 `FAILED` 또는 `DELETING` 상태만 대상으로 한다. `PURGE_ORPHAN_OBJECT`는 metadata가 없고 caller가 정확한 `storage_key`를 제공한 경우에만 사용한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

`reconcile_document()`과 batch `reconcile_documents()`는 dry-run 여부와 action 조건을 확인한다. `dry_run=True`인 `BatchReconciliationResult`에서만 `ReconciliationPlan`을 만들 수 있고, plan 실행 시 각 item을 다시 inspect하므로 stale plan을 성공으로 간주하지 않는다. 결과는 항목별 `applied`, `error_type`, `error_message`와 scanned/failed/eligible/applied/skipped 요약을 보존한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Access, observation, and error adaptation

`AccessContext`와 host-defined `DocumentAccessPolicy`는 일반 조회·목록·본문·삭제뿐 아니라 internal metadata·recovery·reset에도 적용된다. 정책 callback에는 public metadata만 전달되며 전역 작업에서는 metadata가 `None`일 수 있다. 목록은 policy 허용 항목을 모으면서 cursor/page-size semantics를 유지해야 한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

`OperationObserver`와 `recovery_audit_hook`는 성공·실패 event를 받지만 callback failure가 원래 작업을 뒤집지 않는 best-effort 경계를 갖는다. 모든 공개 오류는 stable `code`, `category`, `retryable`을 제공하며, HTTP status·response body·retry header는 DMS가 결정하지 않고 host transport가 변환한다. `DataResetError`는 partial result와 failed store를 별도 보존한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

## Related pages

- [[dms-core]]
- [[dms-document-lifecycle]]
- [[dms-configuration-and-assembly]]
- [[public-api-surface]]
- [[user-scope-isolation]]
- [[verifying-dms-core-contract]]
