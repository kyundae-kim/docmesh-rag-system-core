---
title: Minimizing Consumer Implementation with docmesh-py-core Improvements
created: 2026-07-30
updated: 2026-07-30
type: query
tags: [sdk, integration, architecture, config, api, testing, roadmap]
sources: [raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-examples-v0.5.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]
confidence: medium
---

# Minimizing Consumer Implementation with docmesh-py-core Improvements

## 질문

소비 프로젝트의 bootstrap·설정 변환·client 조회·health·cleanup 구현을 최소화하려면 `docmesh-py-core` 자체를 어떻게 개선해야 하는가?

## 경계 원칙

`docmesh-py-core`는 **서비스 연결의 설정·조립·진단·lifecycle이라는 반복 가능한 인프라 책임**을 소유하고, 소비 프로젝트는 **어떤 서비스를 왜 사용하는지와 domain adapter의 의미**만 소유해야 한다. 목표는 소비자 코드를 무조건 없애는 것이 아니라, 여러 프로젝트가 반복하는 기계적 composition 코드를 SDK의 안정적인 계약으로 끌어올리는 것이다. RAG의 `EmbeddingClient`나 DMS의 문서 lifecycle처럼 제품 의미가 있는 adapter까지 SDK로 이동시키면 오히려 [[rag-service-architecture]]와 [[dms-configuration-and-assembly]]의 경계가 무너진다.

## 현재 문서화된 상태

v0.5.0은 이미 `RuntimePlan`, `assemble_services()`, `assemble_service_runtime()`, `ServiceBundle`/`ServiceRuntime`, startup healthcheck, rollback과 context-manager cleanup을 제공한다. 따라서 개별 client factory를 앱마다 연결하던 초기 구조보다 소비자 구현량이 크게 줄어든 상태다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]

다만 설정 객체와 loader는 process environment의 고정 key만 직접 읽고 mapping·prefix·개별 값을 받지 않는다. 동기 bundle과 비동기 runtime의 조회/plan API도 완전히 대칭적이지 않으며, NATS의 지속 연결은 runtime이 아니라 호출자가 별도로 소유한다. 이 세 지점이 현재 소비 프로젝트에 남는 설정 변환, 분기, 자원 정리 코드의 주된 원인이다.^[raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md]^[raw/articles/docmesh-py-core-examples-v0.5.0-2026-07-27.md]

## 반복 구현과 upstream 개선점

| 소비 프로젝트에 남는 반복 코드 | 현재 원인 | 권장 upstream 계약 |
| --- | --- | --- |
| prefixed env를 canonical key/config model로 수동 변환 | loader가 고정 process env만 읽음 | 명시적 `env` mapping과 `prefix`/namespace 지원 |
| sync/async 경로마다 plan·조회 코드가 달라짐 | `assemble_services()`와 `ServiceRuntime` API 비대칭 | 두 container의 plan·`require()`·health 계약 통일 |
| 같은 서비스 유형의 두 연결을 별도 lifecycle로 조립 | runtime key가 서비스 종류 하나만 표현 | 이름 있는 service instance 또는 scoped assembly |
| 진단 후 다시 assembly하고 오류 payload를 재가공 | preflight와 assembly 결과가 분리 | diagnosis를 보존하는 단일 bootstrap result/error |
| NATS `connect()`/`drain()`을 앱이 직접 관리 | runtime은 builder만 소유 | 지속 연결을 선택적으로 소유하는 managed handle |
| SDK 오류와 Keycloak 오류를 별도로 catch/직렬화 | 오류 계층이 분리됨 | 공통 최상위 SDK 오류와 일관된 `to_dict()` |
| 테스트마다 env patch와 wrapper fake를 반복 | mapping 주입과 typed override 경계 부족 | public factory override 및 in-memory config 경계 |

## P0 — 가장 먼저 개선할 계약

### 1. 환경변수 대신 명시적 설정 소스를 주입할 수 있게 한다

`load_service_configs()`와 `load_available_service_configs()`, `diagnose_services()`, assembly API가 동일한 `Mapping[str, str]` 입력을 선택적으로 받게 하는 것이 최우선이다. process environment는 기본 adapter로 유지하되, 소비자가 전달한 mapping이 있으면 그것만 읽어야 한다. 여기에 `prefix="DMS_"` 또는 동등한 namespace 변환을 제공하면 동일 process에서 RAG와 DMS가 서로 다른 PostgreSQL·SQLite·MinIO 연결을 가져도 `os.environ` 변경이나 수동 config model 조립이 필요 없다.

현재 위키에 기록된 `load_dms_settings()`는 이 SDK 기능이 없어서 소비 repository가 구현한 보완 계층이다. upstream이 mapping/namespace를 지원하면 이 코드는 제거 후보가 된다. 단, prefix precedence와 중복 key 충돌은 명시적이어야 하며 secret-safe 진단에는 소비자가 사용한 원래 key 이름을 보존해야 한다.^[raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md]^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]

권장 최소 계약:

- 모든 config/diagnose/assembly 진입점에서 같은 설정-source 인자 사용
- process environment와 주입 mapping을 암묵적으로 병합하지 않음
- prefix 제거 후 key 충돌·부분 설정을 `ConfigError.issues`로 보고
- config model 직접 생성보다 loader를 canonical validation 경계로 유지
- 임의 SDK kwargs는 계속 금지하고 공식 config field만 허용

### 2. 동기·비동기 container의 소비 API를 대칭으로 만든다

`ServiceRuntime.require(Service.X)`에 대응하는 `ServiceBundle.require(Service.X)` 또는 `require_client(Service.X)`를 제공하고, string 기반 `get_client("...")`와 wrapper `unwrap()` 의존을 일반 경로에서 제거하는 편이 좋다. `assemble_services()`도 별도 `services`·`required`·`one_of` 인자 대신 `RuntimePlan`을 받을 수 있어야 동일 plan을 CLI, API, worker에서 재사용할 수 있다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]

반환 타입은 overload 또는 typed service key로 구체화해 소비 adapter가 `Any`와 구현형 검사에 기대지 않게 한다. 이 개선은 기능을 추가하기보다 이미 존재하는 sync/async 계약의 표면을 맞추는 것이므로 위험 대비 효과가 크다.

### 3. 단일 bootstrap에서 diagnosis를 보존한다

현재 예제는 `diagnose_services(plan=...)` 후 `assemble_service_runtime(plan=...)`을 다시 호출한다. assembly가 동일한 진단을 수행하고 결과를 `ServiceRuntime.diagnosis`, `ServiceBundle.diagnosis` 또는 구조화 assembly error에 보존하면 소비자는 preflight 분기와 오류 변환을 중복 구현하지 않아도 된다.^[raw/articles/docmesh-py-core-examples-v0.5.0-2026-07-27.md]

중요한 것은 진단을 숨기는 convenience 함수가 아니라, 다음을 한 계약으로 묶는 것이다.

1. 선택 서비스와 namespace 결정
2. 설정 로드 및 diagnosis
3. required/one-of 검증
4. client 조립
5. startup readiness
6. 실패 rollback
7. 구조화된 결과 또는 오류 반환

## P1 — 여러 서비스/런타임의 반복 제거

### 4. 이름 있는 service instance를 지원한다

`Service.POSTGRES` 하나만 key로 쓰는 구조는 같은 process의 `rag-postgres`와 `dms-postgres`를 동시에 표현하기 어렵다. `ServiceInstance(service=Service.POSTGRES, name="dms", prefix="DMS_")`와 같은 명시적 scoped key를 도입하면 여러 config 묶음과 lifecycle을 하나의 runtime plan에서 안전하게 소유할 수 있다.

이 기능은 단일 연결 소비자에게 복잡도를 노출하지 않아야 한다. 기존 `Service.POSTGRES`는 default instance의 축약형으로 유지하고, 다중 instance가 실제로 필요한 소비자만 이름을 사용하도록 한다. [[separating-dms-service-environment-variables-with-prefixes]]의 수동 분리 구현을 일반화하되 DMS 자체를 SDK가 알게 해서는 안 된다.

### 5. NATS 지속 연결도 runtime 소유 옵션으로 만든다

현재 `NatsConnectionBuilder.check()`의 임시 연결은 자동 정리되지만 `connect()`가 만든 지속 연결은 호출자가 `drain()`해야 한다. worker/API의 일반 경로에서는 `RuntimePlan`에 연결 소유 정책을 선언하고 `ServiceRuntime`이 연결된 NATS handle을 반환·정리하도록 선택할 수 있어야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]^[raw/articles/docmesh-py-core-examples-v0.5.0-2026-07-27.md]

builder 직접 사용은 특수 reconnect/JetStream 조정용 escape hatch로 남긴다. 자동 연결을 기본으로 강제하면 startup side effect가 커질 수 있으므로 opt-in 계약이 적절하다.

### 6. 오류 직렬화 계약을 하나로 수렴한다

설정·assembly·health·shutdown 오류는 `DocMeshError` 계층이지만 Keycloak token/JWT 오류는 별도 계층이다. 소비 API가 일관된 HTTP/CLI 오류 응답을 만들 수 있도록 모든 공개 오류가 최소한 `service`, `reason_code`, `remediation`, `to_dict()`를 공유해야 한다. 상속을 즉시 통합하기 어렵다면 `serialize_sdk_error(exc)` 같은 단일 공개 adapter부터 제공할 수 있다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]

### 7. 테스트용 조립 seam을 공식화한다

환경 mapping, typed config aggregate, service별 factory override를 package-root public contract로 고정한다. 소비 테스트가 `os.environ` patch, 내부 registry monkeypatch, 반환 wrapper 모방을 반복하지 않고 production과 같은 plan/assembly 경로에 fake client만 주입할 수 있어야 한다. override는 서비스별 callable과 소유권(`runtime-owned`/`caller-owned`)을 명시하고 임의 kwargs override로 확장하지 않는다.

## P2 — 편의 계층과 계측

- API/worker/CLI별 계획을 코드 복사 없이 재사용하도록 작은 `RuntimePlan` preset builder를 추가한다. preset은 서비스 선택과 health 정책만 포함하고 domain 조립은 포함하지 않는다.
- framework-neutral lifespan 예제와 adapter를 별도 integration 모듈로 제공한다. core가 FastAPI 같은 특정 framework를 필수 의존하지 않게 한다.
- bootstrap latency, 서비스별 health latency, 생성·종료 횟수를 callback/observer hook으로 노출한다. SDK가 logging backend를 강제하지 않고 소비자가 metric sink를 연결하게 한다.
- `SERVICE_CATALOG`에서 환경변수 템플릿과 설정 문서를 생성해 문서·`.env.example` drift를 줄인다.

## SDK에 넣지 말아야 할 것

- `RAGCore`, embedding/generation protocol, document lifecycle 같은 domain 조립
- DMS 전용 `DMS_` 이름을 SDK 자체의 고정 정책으로 만드는 것
- 여러 설정 source를 암묵적 precedence로 병합하는 것
- 미지원 SDK constructor 옵션을 `**kwargs`로 우회하는 것
- 모든 서비스를 자동 탐지해 optional/required 정책을 소비자 대신 결정하는 것
- sync 소비자까지 NATS 때문에 강제로 async runtime으로 전환하는 것

이 항목들은 소비자 LOC를 줄이는 것처럼 보여도 ownership을 흐리고 업그레이드 위험을 높인다. [[optimizing-docmesh-py-core-adoption]]의 단일 composition entrypoint는 유지하되, 그 entrypoint가 사용하는 generic 반복 부품만 upstream으로 이동해야 한다.

## 검증 가능한 성공 기준

1. 대표 소비 프로젝트의 production bootstrap LOC가 현재 대비 50% 이상 감소한다.
2. 설정 namespace 분리를 위해 작성한 `os.environ` mutation 또는 config-model 수동 매핑이 0건이다.
3. sync/async 경로가 같은 `RuntimePlan`과 typed `require()` 호출을 사용한다.
4. 동일 process에서 같은 서비스 유형의 두 instance가 key 충돌 없이 조립·진단·종료된다.
5. startup 실패와 정상/예외 종료 모두에서 각 자원이 정확히 한 번 닫힌다.
6. NATS managed mode에서는 소비 코드에 직접 `connect()`/`drain()` 쌍이 없다.
7. 모든 공개 오류가 하나의 JSON-safe 직렬화 경로를 가진다.
8. production bootstrap 테스트가 process environment나 내부 module monkeypatch 없이 실행된다.
9. package-root export와 signature contract test가 신규 API를 고정한다.
10. 기존 단일 서비스·직접 factory 경로는 호환성을 유지한다.

## 권장 rollout

- **P0.1:** mapping 기반 설정 source와 prefix/namespace 계약 추가
- **P0.2:** `RuntimePlan` 기반 sync assembly와 typed `ServiceBundle.require()` 추가
- **P0.3:** diagnosis를 assembly result/error에 보존
- **P1.1:** 이름 있는 service instance와 lifecycle ownership 모델 도입
- **P1.2:** NATS managed connection과 공통 오류 직렬화 추가
- **P1.3:** public factory override seam 및 contract test 고정
- **P2:** framework adapter, preset, observer hook, catalog 기반 문서 생성

각 단계는 소비 프로젝트에서 실제 삭제 가능한 코드와 함께 검증해야 한다. 이 페이지는 수집된 v0.5.0/v0.6.0 문서에서 도출한 upstream 개선 제안이며, 현재 설치 패키지나 live repository에 이 기능이 이미 구현됐는지는 검증하지 않았다. 실제 변경 전에는 [[verifying-docmesh-py-core-contract]]으로 최신 공개 계약을 다시 확인해야 한다.

## Related pages

- [[docmesh-py-core]]
- [[optimizing-docmesh-py-core-adoption]]
- [[service-factory-registry]]
- [[service-health-orchestration]]
- [[settings-loading-and-validation]]
- [[separating-dms-service-environment-variables-with-prefixes]]
- [[verifying-docmesh-py-core-contract]]
