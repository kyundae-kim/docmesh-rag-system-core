---
title: DMS Metadata and Recovery
created: 2026-07-27
updated: 2026-08-04
type: concept
tags: [sdk, schema, persistence, security, api, testing]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]
confidence: medium
---

# DMS Metadata and Recovery

## Public and internal metadata

v0.7.0은 `PublicDocumentMetadata`와 `DocumentMetadata`를 구조적으로 분리한다. 일반 upload/get/list/content 결과에는 `storage_key`가 없고, `public_metadata()`·`to_public_dict()`·JSON schema도 public-safe projection을 유지한다. `DocumentMetadata.storage_key`는 `get_internal_document_metadata()`, `inspect_document()`, reconciliation 같은 명시적인 관리·복구 경로에서만 사용한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Metadata validation

`DefaultMetadataPolicy`는 mapping과 문자열 key, JSON serializability, 최대 serialized byte, 중첩 depth, `password`·`secret`·`token`·`api_key`·`authorization`·`credential` 등 민감 key를 검사한다. 기본 limit은 16,384 bytes와 depth 8이며 upload가 storage를 건드리기 전에 검증한다. 입력 mapping을 변형하지 않고 독립된 normalized mapping을 반환하는 것이 핵심 계약이다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

`StructuredMetadataValidator`는 schema version 확인 → parser → optional projector → 후속 policy 순서로 동작한다. `DmsAssemblyPlan`의 `metadata_validator`, serialized size, depth 옵션을 조립 정책으로 전달하되, custom validator를 사용할 때 어떤 공통 policy를 적용할지는 validator의 `policy`를 포함해 명시적으로 고정하는 편이 안전하다. field-level 오류가 필요하면 `MetadataValidationIssue` 목록을 가진 `MetadataSchemaValidationError`를 사용한다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Inspection and reconciliation

`inspect_document()`은 metadata가 없어도 `DocumentNotFoundError` 대신 `metadata_exists=False`인 `DocumentInspection`을 반환한다. `RecoveryIssue`는 metadata/object 부재, 불완전 삭제, failed 상태를 구분하고, recovery candidate는 `FAILED` 또는 `DELETING` 상태를 대상으로 한다. 지원 action은 soft/hard deletion 완료, failed 표시, 명시적 storage key를 이용한 orphan object purge다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

`reconcile_document()`과 batch `reconcile_documents()`는 단일·제한 범위 복구를 제공한다. dry-run `BatchReconciliationResult`에서만 `ReconciliationPlan`을 만들 수 있고, plan 실행 시 각 항목을 다시 inspect한다. 결과는 항목별 applied/failed/skipped를 보존하며 audit hook 실패가 다른 항목 또는 원래 복구 결과를 뒤집지 않는 best-effort 경계를 갖는다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Access, observation, and error adaptation

`AccessContext`와 host-defined `DocumentAccessPolicy`는 일반 조회·목록·본문·삭제뿐 아니라 internal metadata·recovery·reset에도 적용할 수 있다. 정책 callback에는 public metadata만 전달되므로 내부 storage locator가 권한 판단 또는 로그 밖으로 새지 않는다. `OperationObserver`는 성공·실패 `OperationEvent`를 받고 observer/audit hook 자체의 실패는 원래 작업 결과를 바꾸지 않는다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

모든 공개 오류는 `DmsError` 계층의 stable `code`, `category`, `retryable`을 제공한다. `error_descriptor()`는 transport-neutral 표현을 만들고 `recommended_http_error()`는 host HTTP adapter가 사용할 status/body/header를 권고한다. 내부 endpoint, credential, storage key는 외부 error body에 포함하지 않는다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Related pages

- [[dms-core]]
- [[dms-document-lifecycle]]
- [[dms-configuration-and-assembly]]
- [[public-api-surface]]
- [[user-scope-isolation]]
- [[verifying-dms-core-contract]]
