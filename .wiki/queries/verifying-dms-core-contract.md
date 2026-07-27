---
title: Verifying the dms-core Contract
created: 2026-07-27
updated: 2026-07-27
type: query
tags: [sdk, testing, integration, config, persistence, security]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md]
confidence: medium
---

# Verifying the dms-core Contract

`dms-core` 계약 검증은 import 성공만 확인하는 작업이 아니다. 대상 version의 package-root 공개면, 네 조립 경로, 설정 선택, 문서 lifecycle, public/internal metadata 경계, 멱등성, 복구, 오류·HTTP 변환, 자원 소유권을 각각 검증한 뒤 소비 프로젝트의 실제 호출과 회귀 suite를 확인해야 한다. 기준 지식은 [[dms-core]], [[dms-configuration-and-assembly]], [[dms-document-lifecycle]], [[dms-metadata-and-recovery]]에 나뉘어 있다.

## 1. 검증 기준 고정

1. 소비 프로젝트의 `pyproject.toml`에서 `dms` source와 tag/revision을 확인한다.
2. 격리 환경에서 실제 설치 배포물의 `importlib.metadata.version("dms")`를 기록한다.
3. 같은 tag source의 commit SHA를 기록한다.
4. API 문서, tag source, 설치 배포물이 다르면 설치 배포물과 immutable tag source를 실행 계약의 우선 근거로 삼고 문서 drift를 별도로 보고한다.

2026-07-27 현재 이 프로젝트에는 `dms 0.6.0`이 설치되어 있고 package-root `dms.__all__`은 56개다. 프로젝트 Python source와 tests에는 아직 `dms` import나 SDK factory 호출이 없으므로, 현재 상태는 **의존성 설치 완료 / 소비 통합 미구현**으로 분류한다. 이 사실은 프로젝트 source inspection 결과이며 실제 도입 후 다시 검증해야 한다.

## 2. Package-root 공개 API와 signature

다음 항목을 live package에서 `inspect.signature()`로 수집하고 versioned inventory와 비교한다.

- 조립: `create_sdk_from_environment`, `create_sdk_from_service_configs`, `create_sdk_from_clients`, `create_sdk_from_components`
- 진단: `diagnose_environment`, `format_environment_diagnosis`
- SDK: `DefaultDocumentManagementSDK`
- 요청: bytes, known-size/unknown-size sync stream, async stream request dataclass
- metadata: `DefaultMetadataPolicy`, `StructuredMetadataValidator`
- HTTP: `recommended_http_error`
- model/error/export: `dms.__all__` 전체

모든 request dataclass가 keyword-only인지, factory의 positional/keyword-only 경계와 기본값이 정확한지 확인한다. 일반 소비 코드는 `from dms import ...`만 사용하고 내부 모듈 import를 금지한다.

특히 live `dms 0.6.0`의 `diagnose_environment`는 `diagnose_environment(env, *, runtime_plan=None, selection_mode=None)`로 `env`가 필수다. 수집된 wiki API 문서의 `env=None` 표기만 믿지 말고 실제 signature로 테스트해야 하는 대표적인 drift 지점이다.

## 3. 설정 진단 matrix

외부 연결 전에 `diagnose_environment(env)`만으로 다음 경우를 table-driven test로 검증한다.

| 경우 | 기대 계약 |
| --- | --- |
| 명시적 SQLite + MinIO 완전 설정 | SQLite 선택, valid |
| 명시적 PostgreSQL + MinIO 완전 설정 | PostgreSQL 선택, valid |
| backend 미지정 + PostgreSQL 단서 | PostgreSQL 자동 선택 |
| backend 미지정 + SQLite만 설정 | SQLite 자동 선택 |
| PostgreSQL·SQLite 동시 auto | PostgreSQL 선택 + warning |
| 동시 auto + strict=true | invalid 또는 `ConfigurationError` |
| `POSTGRES_DSN` 사용 | unsupported key 진단 |
| MinIO 필수 key 누락 | missing key와 invalid |
| production + insecure MinIO | 보안 validation 실패 |
| 잘못된 bool/int/range | structured configuration failure |

`format_environment_diagnosis()`와 `ConfigurationError.diagnosis`에 password, access key, secret key, DSN 원문이 노출되지 않는지도 검사한다. 환경 factory 호출 중 process environment를 변경하는 동시성 테스트는 피하고, 테스트별 `patch.dict(os.environ, ..., clear=True)` 또는 `monkeypatch`로 격리한다.

## 4. 네 조립 경로와 자원 소유권

### Environment factory

- 호출 시점의 process environment를 읽는지 확인한다.
- metadata backend 정확히 하나와 MinIO/bucket을 조립하는지 확인한다.
- startup healthcheck 실패나 중간 factory 실패에서 이미 만든 자원을 rollback하는지 확인한다.
- SDK가 만든 client를 `close()`/`aclose()`와 context manager 종료에서 정리하는지 확인한다.

### ServiceConfigs factory

- 검증된 `docmesh_py_core.ServiceConfigs`만 사용하고 environment를 다시 읽지 않는지 확인한다.
- PostgreSQL/SQLite가 정확히 하나인지, MinIO bucket이 필수인지 확인한다.
- `check_on_startup=False|True`가 healthcheck와 rollback을 제어하는지 확인한다.

### Client factory

- SQLAlchemy Engine dialect가 PostgreSQL/SQLite만 허용되는지 확인한다.
- 공백 bucket을 거부하는지 확인한다.
- 주입 engine/MinIO client를 기본적으로 닫지 않는지 확인한다.
- `close_callbacks`로 위임한 자원만 종료하는지 확인한다.

### Component factory

- metadata/object adapter만으로 최소 SDK를 만들 수 있는지 확인한다.
- `operation_store=None`일 때 idempotency operation 기능이 비활성임을 명시적으로 검증한다.
- `service_checks`, `close_callbacks`, custom validator를 정확히 전달하는지 확인한다.

## 5. 문서 lifecycle contract

외부 서비스 없이 deterministic fake/in-memory component로 먼저 검증한다.

1. bytes 업로드 → public metadata 조회 → 본문 조회 → 목록 → 삭제
2. known-size stream의 선언 크기 불일치와 checksum 불일치
3. unknown-size stream의 `max_size` 초과와 spool cleanup
4. sync/async 입력 stream을 SDK가 닫지 않는 caller-ownership 계약
5. sync/async 다운로드 stream의 context 종료·완료·오류·취소 cleanup
6. `close()`와 `aclose()` 반복 호출 안전성
7. 정상·예외 context manager 종료 시 callback 실행

업로드 결과, 공개 조회, 목록 결과에는 `storage_key`가 없어야 한다. `get_internal_document_metadata()`와 recovery model만 관리 경계에서 저장 위치를 노출할 수 있다.

## 6. 멱등성, pagination, 삭제

- idempotency key 없이 일반 업로드가 정상 동작해야 한다.
- key가 있으면 scope가 필수다.
- 동일 scope/key와 동일 요청 재실행은 같은 document ID와 `created=False`다.
- 같은 key의 다른 요청은 `IdempotencyConflictError`, 진행 중 요청은 retryable `IdempotencyInProgressError`다.
- cursor는 같은 `status`와 `limit`에서만 재사용할 수 있고 변조·조건 변경을 `ValidationError`로 거부해야 한다.
- soft-deleted 문서는 일반 조회·목록에서 숨고 본문은 `DocumentDeletedError`여야 한다.
- hard delete는 object와 metadata 영구 삭제 결과를 반환해야 한다.

## 7. Metadata·복구 계약

`DefaultMetadataPolicy`에 대해 JSON 비호환 값, 문자열이 아닌 key, depth 8 초과, 직렬화 16,384 bytes 초과, 중첩 blocked key를 검증한다. 입력 mapping을 변경하지 않고 새 정규화 dict를 반환하는지도 확인한다.

`StructuredMetadataValidator`는 schema version → parser → projector → policy 순서를 테스트한다. custom validator를 주입했을 때 factory의 size/depth 값이 자동으로 섞이지 않는지도 검증한다.

복구에서는 다음을 확인한다.

- `inspect_document()`가 metadata/object 부재를 결과로 표현
- recovery candidate가 `FAILED`·`DELETING`만 허용
- dry-run batch만 `to_plan()` 가능
- plan 실행 전 현재 상태 재검사
- batch의 항목별 실패 격리와 count 일관성
- audit hook 실패가 본 작업 결과를 뒤집지 않는 best-effort 계약

## 8. Error와 HTTP adapter

모든 `DmsError` 하위 오류에서 `code`, `category`, `retryable`, 선택적 `document_id`, `diagnosis` shape를 확인한다. `recommended_http_error()`의 status mapping을 validation 400, payload 413, not-found 404, conflict 409, in-progress 425, storage/health 503 등으로 검증한다. 응답 body는 JSON-safe하고 내부 endpoint·credential·storage key를 포함하지 않아야 한다.

## 9. Health와 실제 integration

component test에서는 성공·실패·예외 service check를 섞어 `HealthStatus.ok`, service별 latency/error shape와 deterministic 집계를 검증한다. 그다음 실제 integration 환경에서 다음 smoke test를 별도로 실행한다.

- SQLite 또는 PostgreSQL metadata schema 생성/재접속
- 실제 MinIO bucket upload/download/delete
- startup healthcheck
- SDK 재시작 후 metadata/object 조회
- partial failure 후 rollback 또는 recovery inspection

외부 서비스가 없으면 integration test는 이유를 명확히 표시해 skip하되 unit/contract suite 성공과 혼동하지 않는다.

## 10. 소비 프로젝트 회귀 검증

1. `dms` 내부 모듈 import, 제거된 export, 이전 factory/argument를 정적 검색한다.
2. 실제 live signature를 보존하는 narrow fake를 사용한다.
3. import/collection, focused DMS adapter tests, 전체 suite, compile/type/lint를 순서대로 실행한다.
4. `git diff --check`와 stale-symbol 재검색을 수행한다.
5. 환경 기반 경로는 mapping injection helper를 임의로 만들지 말고 process environment 계약을 그대로 테스트한다.
6. factory가 SDK를 소유하면 종료 경로를 application bootstrap에 노출하고 테스트한다.

이 프로젝트에서는 아직 DMS 소비 코드가 없으므로 향후 통합 시 먼저 document storage adapter의 책임을 기존 `DocumentStorage`와 DMS 중 어디에 둘지 결정해야 한다. DMS를 단순 object client처럼 부분 사용하면 [[construction-paths-and-adapter-contracts]]와 [[persistence-and-restart-recovery]]의 기존 metadata/vector/document asset 경계와 중복될 수 있다.

## 완료 판정

다음 조건을 모두 만족해야 계약 검증 PASS다.

- target version/tag/commit과 설치 배포물이 일치
- package-root export와 signature inventory 일치
- 설정 선택·strict·production security·secret-safe 진단 통과
- 네 assembly 경로와 소유권/rollback/lifecycle 통과
- bytes/sync/async upload, stream cleanup, idempotency, pagination, delete 통과
- public metadata에서 `storage_key` 비노출
- metadata policy, recovery, error/HTTP, health contract 통과
- 실제 storage integration 결과 또는 명시적 skip 근거 확보
- 소비 프로젝트 전체 suite와 stale-symbol 검사 통과

보고서에는 각 층의 pass/fail/skip, 실행 명령, 테스트 수, 실패 root cause, 외부 서비스 조건, 남은 통합 결정을 구분해 기록한다.
