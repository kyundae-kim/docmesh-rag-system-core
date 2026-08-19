---
title: Verifying the docmesh-py-core Contract
created: 2026-07-27
updated: 2026-08-08
type: query
tags: [sdk, api, integration, testing, config]
sources: []
confidence: low
---

> **Source status (2026-08-08):** The `docmesh-py-core` raw captures previously cited by this page were removed during wiki cleanup. Re-ingest an authoritative source before relying on these implementation-specific claims.

# Verifying the docmesh-py-core Contract

## Question

소비 프로젝트에서 `docmesh-py-core` 버전 업데이트 전후의 계약을 어떻게 검증하는가?

## Verification principle

버전 태그가 지정된 API·설정 문서를 목표 계약으로 두되, 실제 설치된 배포물의 두 package-root export, callable signature, runtime type과 동작을 함께 검사한다. 문서만 맞거나 import만 성공하는 상태는 충분하지 않다. 검증 범위는 **공개 import → 설정 파싱 → 조립·lifecycle → health/error → 소비 프로젝트 회귀** 순으로 확장한다.

## 1. Version and package-root boundary

1. 소비 프로젝트의 dependency source와 대상 tag를 확인한다.
2. 격리된 환경에 해당 버전을 설치하고 `importlib.metadata.version("docmesh-py-core")`로 실제 설치 버전을 확인한다.
3. `docmesh_config.__all__`과 `docmesh_py_core.__all__`을 각각 versioned API inventory와 비교한다.
4. 소비 코드는 두 package root에서만 import하도록 검사하고 내부 모듈 import를 실패 대상으로 둔다.
5. 사용 중인 공개 callable은 `inspect.signature()`로 파라미터, keyword-only 여부와 제거된 인자를 비교한다.

v0.6.0 문서의 기준은 설정·plan·선택 타입은 `docmesh_config`, 조립·client·health·lifecycle은 `docmesh_py_core`가 소유하는 두 root inventory다. 핵심 이름은 `RuntimePlan`, `Service`, `HealthcheckPolicy`, `assemble_service_runtime`, `assemble_services`, `service_lifespan`, `ServiceRuntime`, `ServiceBundle`이며, `docmesh_py_core`가 config 심볼을 재-export하지 않는 것도 계약이다.

## 2. Stale-symbol audit

소비 프로젝트의 source, tests, docs를 함께 검색한다.

- 제거되거나 이름이 바뀐 factory, settings loader, runtime helper
- package 내부 경로 import
- 이전 버전 이름을 포함한 테스트명과 fixture
- legacy argument와 임의 SDK kwargs
- `ServiceBundle`과 `ServiceRuntime`의 소유권을 혼용하는 코드
- NATS를 동기 `assemble_services()`에 넣는 코드

검색 결과가 0건이어야 하는 항목은 명시적인 denylist로 테스트한다. 단순 문자열 교체보다 symbol 정의와 모든 usage를 추적해야 한다.

## 3. Configuration contract tests

각 서비스에 대해 최소 네 종류를 실제 parser로 검증한다.

| 구분 | 검증 내용 |
| --- | --- |
| valid | 최소 환경변수가 typed config로 로드됨 |
| absent | 선택하지 않은 서비스는 검증하지 않음 |
| partial | 일부 필수값만 있으면 `ConfigError` 발생 |
| invalid/security | 잘못된 bool·숫자·범위 또는 production TLS 위반이 거부됨 |

설정 객체는 인자 없이 프로세스 환경변수에서 직접 읽으며 mapping, 개별 연결값, 임의 SDK kwargs로 우회할 수 없다. `docmesh_config`에서 `ServiceConfigs`/`RuntimePlan`을 만들고, `load_service_configs()`·`load_available_service_configs()`와 diagnosis가 선택 서비스 및 partial 설정을 엄격히 처리하는지 확인한다.

네트워크 연결 전에는 `diagnose_services(plan=...)`를 호출해 `absent`, `complete`, `partial`, `invalid`, required/one-of 위반과 production 보안 문제를 검사한다. 진단 결과와 오류 메시지에는 secret 원문이 없어야 한다.

## 4. Assembly and lifecycle contract tests

`RuntimePlan`을 실제 공개 API로 만들고 다음을 검증한다.

1. required, optional, one-of 선택이 정규화된다.
2. 빈 plan, 중복 선택, 잘못된 대안 그룹은 `InvalidRuntimePlanError`다.
3. `assemble_service_runtime(plan=...)` 또는 `service_lifespan(plan=...)`은 선택 client를 한 번만 만들고 `runtime.require(Service.…)`로 조회된다.
4. 조립 또는 startup healthcheck가 실패하면 이미 만든 client를 rollback한다.
5. `async with runtime` 종료 시 sync/async client가 모두 정리된다.
6. 동기 전용 `assemble_services(plan=...)`는 NATS 선택을 거부하고, async NATS connection의 drain/close owner가 명확하다.
7. `ServiceBundle`/`ServiceRuntime`을 소유한 host 객체가 close 또는 context-manager 경로를 외부에 제공한다.

Lifecycle 검증에서는 “생성 성공”만 보지 말고 정상 종료, 중간 생성 실패, healthcheck 실패, close 일부 실패를 모두 테스트해야 한다. `ServiceCloseError`는 전체 종료 시도 후 실패를 집계하는 계약이다.

## 5. Health and error-shape tests

- required 서비스 실패는 `HealthCheckError`를 발생시키고 결과를 보존한다.
- optional 서비스 실패는 결과에 기록되지만 startup 정책에 따라 전체 시작을 막지 않는다.
- `HealthCheckResult.to_dict()`와 diagnosis 결과는 JSON-safe하다.
- `DocMeshError` 계열은 `service`, `reason_code`, `remediation`을 제공한다.
- `ConfigError.issues`는 환경변수 key, reason, remediation을 제공하되 secret을 노출하지 않는다.
- timeout, retry attempts, `StartupFailureMode.FAIL/REPORT`를 각각 검증한다.

이 단계는 [[service-health-orchestration]]과 [[settings-loading-and-validation]]의 운영 계약을 코드 수준에서 고정한다.

## 6. Consumer integration tests

소비 프로젝트에서는 mock package 전체를 만드는 대신 실제 대상 버전을 설치하고 다음 경계를 집중적으로 테스트한다.

1. production module import와 test collection이 성공한다.
2. composition root가 설정을 한 번만 로드하고 client/runtime을 중복 생성하지 않는다.
3. embedding, generation, storage adapter가 wrapper delegation과 runtime defaults를 보존한다.
4. bootstrap owner가 runtime cleanup을 위임한다.
5. 최소 실제 구성(SQLite 등)은 assembly부터 healthcheck, 종료까지 통과한다.
6. 전체 unit/integration suite, compile/import check와 stale-symbol search가 통과한다.

광범위한 autouse fake는 제거된 export, strict parser와 lifecycle 오류를 숨길 수 있으므로 피한다. 자세한 소비 경계는 [[developing-with-docmesh-py-core]], 공개 import 원칙은 [[public-api-surface]]를 함께 참조한다.

## Recommended gate order

1. 대상 버전/tag 고정
2. `docmesh_config`/`docmesh_py_core` package-root `__all__`·signature 검사
3. stale symbol/import 검색
4. 설정 및 diagnosis 계약 테스트
5. assembly·lifecycle RED/GREEN 테스트
6. health/error-shape 테스트
7. 실제 최소 서비스 smoke test
8. 소비 프로젝트 전체 테스트
9. 문서 예제와 테스트명을 새 계약으로 동기화

## Evidence rule

검증 보고서에는 설치된 버전, package-root inventory 차이, 실행한 테스트 명령, pass/fail 수, 남은 stale symbol과 lifecycle 미검증 지점을 포함한다. GitHub Wiki 문서는 tag 이름을 포함해도 immutable commit에 고정되지 않을 수 있으므로, 최종 migration 판단은 대상 tag의 실제 패키지와 source tree로 재확인한다.

## v0.6.0 additional gates

- `docmesh_config`가 `RuntimePlan`, `HealthcheckPolicy`, `ServiceConfigs`, `diagnose_services`의 canonical root인지 확인한다.
- `docmesh_py_core`가 config 심볼을 재-export하지 않고, config/settings/runtime_plan/factories 모듈이 호환 facade로만 남아 있는지 확인한다.
- `SERVICE_CATALOG`, `generate_environment_template()`, `generate_configuration_reference()` 결과가 deterministic하고 실제 config metadata와 일치하는지 비교한다.
- 모든 factory가 validated config model만 받으며 kwargs, mapping, test override를 우회 입력으로 허용하지 않는지 확인한다.
- `service_lifespan()`의 startup policy, rollback, cleanup과 NATS persistent connection의 caller ownership을 테스트한다.
- `DOCMESH_LOG_LEVEL`은 logging helper가 읽고 `DOCMESH_HEALTHCHECK_ENABLED` 같은 전역 toggle은 사용하지 않는지 stale-symbol 검색에 포함한다.

이 추가 gate는 v0.6.0의 package split과 lifecycle ownership을 검증하며, 아래 v0.5.0 실행 결과를 소급해 바꾸지 않는다.

## Executed validation: 2026-07-27

대상 소비 프로젝트 `/workspaces/docmesh-rag-system-core`와 tag `v0.5.0`의 실제 source commit `b17a5a8dae6ddda4011a278bbe3aea655499a438`을 비교했다. 프로젝트 `.venv`에 설치된 배포물도 `docmesh-py-core 0.5.0`이었다.

### Package contract result

- 설치 패키지와 tag source 모두 package-root `__all__` 86개를 제공했다.
- `load_service_configs`, `load_available_service_configs`, `assemble_services`는 positional 환경 mapping을 받지 않는 keyword-only API였다.
- upstream test suite는 임시 `pytest-asyncio` plugin 환경에서 `206 passed, 14 skipped`였다.
- 실제 `SQLITE_PATH=:memory:`로 strict config load, diagnosis, 동기 `ServiceBundle` assembly/healthcheck가 통과했다.
- 같은 SQLite 구성의 `RuntimePlan` + `assemble_service_runtime()` async smoke test도 assembly, `require()`, `SELECT 1`, healthcheck, context cleanup을 통과했다.

따라서 검증 범위에서 SDK v0.5.0 자체의 공개·설정·동기/비동기 runtime 계약은 일관됐다.

### Consumer contract failures

소비 프로젝트 전체 suite는 `38 passed, 30 failed`였다. 30건은 모두 `rag_system_core/composition/docmesh_runtime.py:18`의 동일한 root cause로 수렴했다.

1. `load_docmesh_settings()`가 `load_available_service_configs(source, services=...)`로 환경 mapping을 positional 전달한다. 실제 v0.5.0은 `load_available_service_configs(*, services=...)`이므로 `TypeError`다.
2. `assemble_docmesh_services()`도 `assemble_services(source, ...)`로 같은 금지된 positional mapping을 전달하며 직접 smoke probe에서 `TypeError`가 재현됐다.
3. `test_rag_system_core/composition/test_docmesh_integration.py`의 fake 함수는 여전히 `env` positional 인자를 받기 때문에 첫 번째 오류를 가린다.
4. 같은 파일의 테스트명 두 개가 `v020`을 유지해 검증 기준 버전도 stale하다.

최초 판정은 **SDK contract PASS / consumer integration FAIL**이었다.

### Consumer fix verification

같은 날 소비 프로젝트를 v0.5.0 계약에 맞게 수정했다.

- `load_docmesh_settings()`와 `assemble_docmesh_services()`에서 positional 환경 mapping 인자를 제거했다.
- 두 wrapper는 process environment를 직접 읽는 SDK의 keyword-only API만 호출한다.
- 당시 v0.5.0 소비자 검증에서는 `DocmeshRAGServiceFactory.from_env()`도 별도 mapping을 전달하지 않고 process environment 기반 assembly를 위임했다. 이는 historical contract이며 현재 source의 public API가 아니다.
- fake SDK 함수들을 실제 keyword-only signature로 바꾸고 테스트명의 `v020` 표기를 `v050`으로 갱신했다.
- 새 계약 테스트 네 개가 수정 전 모두 예상한 `TypeError`로 실패했고, 수정 후 모두 통과했다.
- 집중 통합 suite는 `13 passed`, 전체 소비 프로젝트 suite는 `69 passed`였다.
- compileall, `git diff --check`, stale `v020`/positional-env 검색도 통과했다.

최종 판정은 **SDK contract PASS / consumer integration PASS**다.

## Related pages

- [[docmesh-py-core]]
- [[docmesh-config]]
- [[public-api-surface]]
- [[settings-loading-and-validation]]
- [[service-health-orchestration]]
- [[developing-with-docmesh-py-core]]
