---
title: Verifying the dms-core Contract
created: 2026-07-27
updated: 2026-08-04
type: query
tags: [sdk, testing, integration, config, persistence, security, observability]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]
confidence: medium
---

# Verifying the dms-core Contract

`dms-core` v0.7.0 계약 검증은 import 성공만 확인하는 작업이 아니다. package-root 공개면, host-owned 조립, plan 정책, caller/SDK 자원 소유권, sync/async lifecycle, 문서 작업, public/internal metadata 경계, idempotency, pagination, reset/recovery, stable error와 consumer adapter를 각각 검증해야 한다. 기준 지식은 [[dms-core]], [[dms-configuration-and-assembly]], [[dms-document-lifecycle]], [[dms-metadata-and-recovery]]에 나뉘어 있다.

## 1. 기준 version과 문서 경계 고정

1. 소비 프로젝트 manifest에서 `dms` source와 target tag/revision을 고정한다.
2. 격리 환경에서 실제 설치 배포물의 `importlib.metadata.version("dms")`와 package root를 기록한다.
3. 같은 tag source의 commit SHA를 기록한다.
4. versioned wiki/API 문서, tag source, 설치 배포물이 다르면 설치 배포물과 immutable tag source를 실행 계약의 우선 근거로 삼고 문서 drift를 별도로 보고한다.
5. v0.7.0에서는 환경 factory/diagnosis가 공개 계약이 아니므로, 존재한다고 가정한 legacy symbol을 성공 조건에 포함하지 않는다.

현재 이 페이지는 v0.7.0 Wiki 문서를 ingest한 것이며 installed package나 consumer repository를 새로 live 검증한 결과는 아니다. 실제 도입 전에는 아래 matrix를 실행한다.

## 2. Package-root export와 signature

`from dms import ...`만 사용해 다음 공개 면을 수집하고 문서/실제 signature와 비교한다.

- 조립: `create_sdk_from_clients`, `create_async_sdk_from_clients`, `create_sdk_from_components`, `create_async_sdk_from_components`
- facade: `DefaultDocumentManagementSDK`, `AsyncDocumentManagementSDK`, scoped sync/async facade
- policy/lifecycle: `DmsAssemblyPlan`, `DmsServiceConfigs`, `ManagedResource`, `ResourceOwnership`, `AccessContext`, `DocumentAccessPolicy`, `DmsOperationContext`
- capability protocol: writer/reader/lister/deleter/reset/health와 aggregate client
- data/operation: upload request/result, public/internal metadata, page/content/copy, delete/reset, health, operation result
- recovery: inspection, candidate, action, reconciliation result/plan/audit
- errors/transport: `DmsError` hierarchy, `ErrorDescriptor`, `RecommendedHttpError`, descriptor merge/projection

모든 request와 plan이 keyword-only인지, async facade의 awaitable·async iterator·context manager surface가 문서와 일치하는지 확인한다. v0.6.0에 있던 `create_sdk_from_environment`, `create_sdk_from_service_configs`, `diagnose_environment`는 v0.7.0 current docs에 포함되지 않으므로 stale-symbol 검출 대상으로 분리한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

## 3. 네 조립 경로와 ownership matrix

각 경로를 같은 component fake와 정책으로 table-driven 검증한다.

| 경로 | 검증할 계약 |
| --- | --- |
| client sync | PostgreSQL/SQLite dialect, non-empty bucket, operation store assembly |
| component sync | metadata/object/optional operation store injection, service checks |
| client async | sync client path와 동일한 policy·ownership, worker execution |
| component async | sync component path와 동일한 public 작업 및 async cleanup |

추가로 다음을 검증한다.

- 기본 injected engine/client/component는 caller-owned이고 자동 close하지 않는다.
- `ManagedResource(SDK)`와 `close_callbacks`만 등록 역순으로 정확히 한 번 종료한다.
- SDK-owned cleanup 하나가 실패해도 나머지를 시도하고 `ResourceCleanupError.errors`에 모두 모은다.
- `DmsAssemblyPlan`이 개별 option보다 우선하고 size/depth/max-file/startup-timeout의 양수 검증을 수행한다.
- `check_on_startup=True`에서 service check 실패/timeout이 `HealthCheckFailedError`가 되고 SDK-owned resource만 rollback한다.
- scoped facade가 shared SDK lifecycle을 닫지 않는다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

## 4. Document lifecycle contract

외부 서비스 없이 deterministic fake/in-memory component로 먼저 검증한다.

1. bytes/file/known-size stream 업로드와 filename/content-type/size validation
2. `max_file_size` 초과가 storage write 전에 거부되는지
3. known-size stream의 실제 byte 수 불일치와 caller stream 미종료
4. upload object-first → metadata write → rollback/`ConsistencyError`
5. public upload/get/list 결과에 `storage_key`가 없는지
6. sync/async content stream의 정상·예외·취소·조기 종료 cleanup
7. `copy_document_to()`가 source는 닫고 caller sink는 닫지 않는지
8. `close()`/`aclose()`와 context manager의 반복 종료 안전성

## 5. Idempotency, pagination, deletion, reset

- bytes idempotency에 persistent `operation_store`와 non-empty scope/key가 필요한지 확인한다.
- 같은 scope/key 같은 fingerprint는 같은 document ID와 `created=False`인지 확인한다.
- 다른 fingerprint는 `IdempotencyConflictError`, pending은 retryable `IdempotencyInProgressError`, 정확하지 않은 operation 조회는 not-found인지 확인한다.
- cursor의 `status`·`limit` 결합, 1~1000 범위, 변조/조건 변경 거부와 `iter_documents()` 전체 순회를 검증한다.
- soft delete가 일반 metadata/list에서 문서를 숨기고 content에는 `DocumentDeletedError`를 주는지, hard delete 결과와 상태를 확인한다.
- `clear_all_data()`/`initialize_for_data_load()`가 metadata·objects·operations를 대상으로 하고 partial count, `failed_stores`, `ready_for_data_load`를 보존하는지 확인한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## 6. Metadata, policy, observer, recovery

`DefaultMetadataPolicy`에 JSON 비호환 값, non-string key, depth 8 초과, 16,384-byte 초과, blocked credential key와 입력 mapping mutation을 검증한다. `StructuredMetadataValidator`는 schema version → parser → projector → policy 순서를 검증하고 field-level issue shape를 확인한다.

`AccessContext`와 custom policy는 일반·관리·복구·reset 전 경로를 검증한다. 목록 filtering 뒤 cursor/page semantics가 유지되는지, policy/observer/audit hook의 예외가 원래 작업 결과를 덮지 않는지 확인한다. `OperationEvent`와 `RecoveryAuditEvent`에 content·credential·storage locator가 없는지도 검사한다.

복구에서는 다음을 확인한다.

- metadata/object 부재를 `DocumentInspection`의 issue/boolean으로 표현
- recovery candidate가 `FAILED`·`DELETING`만 허용
- dry-run batch만 `to_plan()` 가능
- plan 실행 전 각 항목 재검사
- orphan purge에 명시적 `storage_key`가 필요
- batch 항목별 실패 격리와 count property 일관성

## 7. Error와 HTTP adapter

모든 `DmsError`에서 stable `code`, `category`, `retryable`, 선택적 document/diagnosis shape를 확인한다. `error_descriptor()`가 canonical 분류를 보존하고 내부 설정·storage 메시지를 secret-safe public message로 바꾸는지, `merge_error_descriptor()`가 host external code/message/retry-after만 추가하는지 검증한다. `recommended_http_error()`의 권장 status는 access 403, validation 400, payload 413, not-found 404, conflict/deleted 409, in-progress 425, storage/metadata/health 503, 기타 500 범주로 확인한다.

## 8. Documentation traceability

v0.7.0 API 문서가 제시한 검증 명령을 package source에 맞춰 실행한다.

```bash
python .hermes/skills/software-development/requirements-documentation/scripts/verify_sdk_doc_traceability.py \
  --package-init dms/sdk/__init__.py \
  --extra-export DocumentStatus \
  --sdk-file dms/sdk/implementation.py \
  --sdk-class DefaultDocumentManagementSDK \
  --api-doc docs/api.md
```

환경변수를 읽는 SDK source가 현재 계약이 아니므로 environment-source/config-doc/env-example 인자는 v0.7.0 DMS API 검증에 임의로 추가하지 않는다. 설정 문서는 host가 component/client를 준비하는 contract로 별도 확인한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## 9. Consumer regression과 완료 판정

1. consumer가 `dms` 내부 module import나 v0.6 legacy factory를 사용하지 않는지 정적 검색한다.
2. 실제 live signature를 보존하는 narrow fake로 DMS adapter contract를 실행한다.
3. import/collection → focused DMS tests → 전체 suite → compile/type/lint 순으로 실행한다.
4. 실제 SQLite/PostgreSQL + MinIO 환경에서 schema/reconnect/upload/download/delete/health/restart/recovery smoke를 별도로 실행한다. 외부 서비스가 없으면 명시적 skip 사유를 남긴다.
5. `git diff --check`와 stale-symbol 재검색을 수행한다.

PASS는 target version/source와 설치 배포물 일치, root export/signature 일치, 네 조립 경로와 ownership/rollback/lifecycle 통과, upload/read/idempotency/pagination/delete/reset/recovery/error/health 통과, public metadata의 locator 비노출, consumer regression과 integration 결과 또는 명시적 skip 근거 확보를 모두 의미한다. 각 층의 pass/fail/skip, 명령, 테스트 수, 실패 root cause, 외부 서비스 조건을 분리해 보고한다.

## Related pages

- [[dms-core]]
- [[dms-configuration-and-assembly]]
- [[dms-document-lifecycle]]
- [[dms-metadata-and-recovery]]
- [[public-api-surface]]
- [[applying-dms-core-as-document-storage]]
- [[construction-paths-and-adapter-contracts]]
