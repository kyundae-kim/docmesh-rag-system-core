---
title: Verifying the dms-core Contract
created: 2026-07-27
updated: 2026-08-18
type: query
tags: [sdk, testing, integration, config, persistence, security, observability]
sources: [raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md, raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]
confidence: medium
---

# Verifying the dms-core Contract

`dms-core` v0.9.0 계약 검증은 import 성공만 확인하는 작업이 아니다. package-root 공개면, factory/direct 조립, host-owned resource, sync/async/scoped facade, 문서 작업, public/internal metadata 경계, idempotency, pagination, reset/recovery, stable error와 consumer adapter를 각각 검증해야 한다. 기준 지식은 [[dms-core]], [[dms-configuration-and-assembly]], [[dms-document-lifecycle]], [[dms-metadata-and-recovery]]에 나뉘어 있다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

## 1. 기준 version과 문서 경계 고정

1. 소비 프로젝트 manifest에서 `dms` source와 target tag/revision을 고정한다.
2. 격리 환경에서 실제 설치 배포물의 `importlib.metadata.version("dms")`와 package root를 기록한다.
3. 같은 tag source의 commit SHA를 기록한다. v0.9.0 Wiki 문서의 기준은 commit `f7a40f1`이다.
4. versioned wiki 문서, tag source, 설치 배포물이 다르면 설치 배포물과 immutable tag source를 실행 계약의 우선 근거로 삼고 문서 drift를 별도로 보고한다.
5. v0.6/v0.7 legacy environment factory와 assembly-plan symbols를 v0.9.0 성공 조건에 포함하지 않는다.

현재 이 페이지는 v0.9.0 Wiki 문서를 ingest한 것이며 installed package나 consumer repository를 새로 live 검증한 결과는 아니다. 사용자가 제공한 GitHub Wiki URL은 `source_url`로 보존했지만 immutable wiki commit URL은 아니므로 raw body는 ingest 시점 revision이다.

## 2. Package-root export와 facade surface

`from dms import ...`만 사용해 API reference의 54개 공개 이름과 실제 `dms.__all__`을 비교한다. 특히 다음 범위를 확인한다.

- assembly: `DocumentManagementSDKFactory`, `DefaultDocumentManagementSDK`
- facade: sync/async base 및 sync/async scoped facade
- policy/observation: `AccessContext`, `DmsOperationContext`, `DocumentAccessPolicy`, `OperationEvent`, `OperationObserver`
- capability protocol: writer/reader/lister/deleter/reset 및 aggregate client
- data/operation: upload request/result, public/internal metadata, page/content/copy, delete/reset
- recovery: inspection, issue/action, reconciliation result/plan/audit
- errors: `DmsError` hierarchy와 stable fields

API reference의 26개 facade 작업이 네 facade에 대응하는지 확인한다. `async for` iterator, async content stream, context manager와 `sdk.scoped(...)` 기본값이 문서와 실제 signature에 일치해야 한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## 3. Assembly와 ownership matrix

각 경로를 같은 component fake와 정책으로 table-driven 검증한다.

| 경로 | 검증할 계약 |
| --- | --- |
| client sync | `Engine` dialect, non-empty bucket, MinIO injection, operation store assembly |
| component sync | metadata/object/optional operation store injection |
| client async | sync client path와 동일한 작업 결과 및 resource non-ownership |
| scoped sync/async | context defaults, explicit override, shared SDK lifecycle non-ownership |

추가로 다음을 검증한다.

- 기본 injected engine/client/component는 caller-owned이고 자동 close하지 않는다.
- SDK가 직접 연 upload file과 반환 content source는 SDK가 정리하고 caller input stream/sink는 닫지 않는다.
- factory의 blank bucket과 unsupported dialect가 `ConfigurationError`인지 확인한다.
- factory/direct SDK의 `max_file_size` invalid 값이 각각 문서화된 오류를 내는지 확인한다.
- `operation_store`가 없을 때 idempotency upload와 operation lookup이 `ValidationError`인지 확인한다.
- DMS facade에 `close()`·`aclose()`·`check_health()`가 없다는 negative surface를 확인하고 host lifecycle/readiness를 별도로 검증한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

## 4. Document lifecycle contract

외부 서비스 없이 deterministic fake/in-memory component로 먼저 검증한다.

1. bytes/file/known-size stream upload와 filename/content-type/size validation
2. `max_file_size` 초과가 storage write 전에 거부되는지
3. known-size stream 실제 byte 수 불일치와 caller stream 미종료
4. upload object-first → metadata write → rollback/`ConsistencyError`
5. public upload/get/list 결과에 `storage_key`가 없는지
6. application-owned metadata가 보존되고 fingerprint에서 제외되는지
7. sync/async content stream의 정상·예외·취소·조기 종료 cleanup
8. `copy_document_to()`가 source는 닫고 caller sink는 닫지 않는지

## 5. Idempotency, pagination, deletion, reset

- persistent `operation_store`와 non-empty scope/key가 bytes idempotency에 필요한지 확인한다.
- 같은 scope/key와 같은 fingerprint가 같은 document ID와 `created=False`인지 확인한다.
- 다른 fingerprint는 `IdempotencyConflictError`, pending은 retryable `IdempotencyInProgressError`, 없는 operation은 not-found인지 확인한다.
- cursor의 status·limit 결합, 1~1000 범위, 변조/조건 변경 거부와 `iter_documents()` 전체 순회를 검증한다.
- soft delete가 일반 metadata/list에서 문서를 숨기고 content에는 `DocumentDeletedError`를 주는지, hard delete 결과와 상태를 확인한다.
- `clear_all_data()`/`initialize_for_data_load()`가 metadata·`documents/` objects·operations를 대상으로 하고 partial count, `failed_stores`, `ready_for_data_load`를 보존하는지 확인한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

API reference의 추적성 matrix는 persistent idempotency replay/conflict/lookup 일부를 `source-only` gap으로 표시한다. 따라서 facade membership test만으로 이 영역을 pass 처리하지 말고 별도 focused test 결과를 보고한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## 6. Metadata, policy, observer, recovery

- `PublicDocumentMetadata`와 `DocumentMetadata` projection에서 `storage_key`가 public 응답·event·callback으로 새지 않는지 확인한다.
- metadata가 DMS 내부 schema validator에 의해 변형되지 않고 host serialization 경계를 유지하는지 확인한다.
- access policy가 일반·관리·복구·reset 전 경로에서 적용되고, list filtering 뒤 cursor/page semantics가 유지되는지 확인한다.
- policy/observer/audit hook의 예외가 원래 작업 결과를 덮지 않는지, event에 body·credential·storage locator가 없는지 검사한다.
- metadata/object 부재를 `DocumentInspection`의 issue/boolean으로 표현하는지 확인한다.
- recovery candidate가 `FAILED`·`DELETING`만 허용하고, orphan purge에 명시적 `storage_key`가 필요한지 확인한다.
- dry-run batch만 `to_plan()` 가능하고 plan 실행 전 각 item을 재검사하는지, 항목별 실패와 요약 count를 보존하는지 확인한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

## 7. Error와 host transport adapter

모든 `DmsError`에서 stable `code`, `category`, `retryable`, 선택적 `document_id`/diagnosis shape를 확인한다. `DataResetError`의 partial result, `errors`, `failed_stores`를 별도로 확인한다. HTTP status, response body, retry header는 DMS가 결정하지 않으므로 host transport의 mapping을 별도 contract test로 둔다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

## 8. Documentation traceability

v0.9.0 API 문서가 제시한 검증 범위를 package source에 맞춰 실행한다.

```bash
# dms-core checkout에서 provisioned project interpreter 사용
.venv/bin/python -m pytest test_dms -q

# Wiki clone에서 Python fence 구문 검사
python - <<'PY'
import ast
from pathlib import Path

for path in (Path("API-Reference-v0.9.0.md"), Path("Examples-v0.9.0.md")):
    in_python = False
    block = []
    for line in path.read_text().splitlines():
        if line.strip() == "```python":
            in_python = True
            block = []
        elif in_python and line.strip() == "```":
            ast.parse("\n".join(block), filename=str(path))
            in_python = False
        elif in_python:
            block.append(line)
    assert not in_python, path
PY
```

API source baseline은 `f7a40f1`의 line 기준이며, source-only row를 behavior coverage로 과장하지 않는다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## 9. Consumer regression과 완료 판정

1. consumer가 `dms` 내부 module import나 v0.6/v0.7 legacy factory를 사용하지 않는지 정적 검색한다.
2. 실제 live signature를 보존하는 narrow fake로 DMS adapter contract를 실행한다.
3. import/collection → focused DMS tests → 전체 suite → compile/type/lint 순으로 실행한다.
4. 실제 SQLite/PostgreSQL + MinIO 환경에서 schema/reconnect/upload/download/delete/restart/recovery smoke를 별도로 실행한다. 외부 서비스가 없으면 명시적 skip 사유를 남긴다.
5. `git diff --check`와 stale-symbol 재검색을 수행한다.

PASS는 target version/source와 설치 배포물 일치, root export/signature 일치, factory/direct 조립과 ownership 통과, upload/read/idempotency/pagination/delete/reset/recovery/error 통과, public metadata의 locator 비노출, consumer regression과 integration 결과 또는 명시적 skip 근거 확보를 모두 의미한다. 각 층의 pass/fail/skip, 명령, 테스트 수, 실패 root cause, 외부 서비스 조건을 분리해 보고한다.

## Related pages

- [[dms-core]]
- [[dms-configuration-and-assembly]]
- [[dms-document-lifecycle]]
- [[dms-metadata-and-recovery]]
- [[public-api-surface]]
- [[applying-dms-core-as-document-storage]]
- [[construction-paths-and-adapter-contracts]]
