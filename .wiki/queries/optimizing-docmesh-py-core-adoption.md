---
title: Optimizing docmesh-py-core adoption
created: 2026-07-28
updated: 2026-08-18
type: query
tags: [sdk, integration, architecture, config, performance, testing]
sources: []
confidence: medium
---

# Optimizing docmesh-py-core adoption

## 질문

`docmesh-rag-system-core`에서 `docmesh-py-core` 적용을 어떻게 최적화해야 하는가?

## 결론

최적화의 핵심은 SDK 호출 수를 미세 조정하는 것이 아니라 **조립 경로를 하나로 수렴하고, 설정·client·health·cleanup의 소유권을 composition 계층에 집중하는 것**이다. v0.6.0에서는 `docmesh_config`가 설정·진단·`RuntimePlan`을 소유하고, `docmesh_py_core`가 validated config를 client/runtime으로 조립한다. 일반 동기 RAG 실행은 `assemble_services(plan=...)`와 `ServiceBundle`, NATS가 필요한 실행은 `RuntimePlan`과 `service_lifespan()` 또는 `assemble_service_runtime()`을 사용한다. `RAGCore`는 완성된 domain dependency만 받고, 환경변수 해석이나 SDK client lifecycle을 직접 소유하지 않는다.

이 방향은 [[docmesh-py-core]], [[developing-with-docmesh-py-core]], [[construction-paths-and-adapter-contracts]]의 권장 소비 경로를 현재 composition 구조에 맞게 압축한 것이다.

## v0.6.0 canonical split

구성 계층은 `docmesh_config`에서 `ServiceConfigs`와 `RuntimePlan`을 만들고 `diagnose_services(plan=...)`로 네트워크 연결 전에 설정·required/one-of·production 보안을 확인한다. 조립 계층은 `docmesh_py_core`의 `assemble_services(plan=...)`, `assemble_service_runtime(plan=...)`, `service_lifespan(plan=...)`만 사용해 client·health·rollback·cleanup을 소유한다. 두 package root를 섞어 import하거나 SDK factory에 임의 kwargs를 전달하지 않는다.

## 최적화 원칙

### 1. Production 조립 경로를 하나로 고정한다

일반 애플리케이션 경로에서는 registry나 개별 `create_*_client()` 호출을 여러 곳에서 조합하지 않는다. 하나의 bootstrap/factory가 다음을 순서대로 수행해야 한다.

1. 필요한 서비스 집합 결정
2. 해당 서비스 설정만 로드·검증
3. startup 전 진단
4. client 묶음 조립
5. required dependency readiness 확인
6. RAG adapter와 `RAGCore` 조립
7. 역순 cleanup

직접 factory API는 CLI, 격리 테스트, 특수 배치처럼 일부 서비스만 명시적으로 제어해야 할 때의 보조 경로로 제한한다. v0.6.0 factory는 validated config model을 받고 kwargs·factory override를 허용하지 않으므로, 테스트 대체는 config/plan 생성 경계에서 명시한다. 이렇게 해야 생성 경로별 설정·health·종료 semantics가 갈라지는 것을 막을 수 있다.

### 2. 설정은 실행 경로의 최소 부분집합만 검증한다

`docmesh_config`에서 실제 실행에 필요한 서비스만 포함한 `RuntimePlan`을 만들고, 해당 plan에 맞춰 config를 로드·진단한다. RAG 기본 경로라면 Ollama·Milvus가 중심이고, Keycloak·NATS·Langfuse를 무조건 포함하지 않는다. 설정을 전부 한 번에 강제하면 사용하지 않는 서비스의 누락값 때문에 bootstrap이 실패하고 테스트 fixture도 불필요하게 커진다.

반대로 선택한 서비스의 부분 설정은 조용히 무시하지 않는다. `diagnose_services(plan=...)`와 `ConfigError.issues`를 startup 오류로 변환해 어떤 key와 보안 규칙이 실패했는지 secret-safe하게 보여 주는 것이 좋다. 관련 규칙은 [[settings-loading-and-validation]]과 [[service-configuration-topology]]에 정리되어 있다.

### 3. lifecycle은 요청 단위가 아니라 프로세스 단위로 관리한다

외부 서비스 client, connection pool, SDK bundle을 query/ingest 호출마다 만들지 않는다. API lifespan, worker process, CLI command의 최상위 context에서 한 번 조립하고 재사용한다. 종료는 `ServiceBundle`, `ServiceRuntime`, `service_lifespan()` context manager에 맡겨 실패 중 rollback과 정상 종료 cleanup을 같은 경로로 보장한다. NATS persistent connection의 drain/close는 caller가 소유한다.

NATS가 없으면 동기 bundle을 유지한다. 단지 SDK가 async runtime을 제공한다는 이유로 전체 RAG 호출 경로를 비동기화하면 복잡도만 증가한다. NATS 또는 실제 async lifecycle이 추가될 때만 `assemble_service_runtime()`으로 승격한다.

### 4. composition과 domain의 의존 방향을 고정한다

`docmesh-py-core`는 공통 infra SDK이고 `rag_system_core`는 RAG domain을 소유한다. 따라서 composition 계층이 SDK의 `ServiceBundle`/wrapper를 RAG의 `EmbeddingClient`, `GenerationClient`, vector/document storage 계약으로 변환해야 한다. `RAGCore`가 환경변수, `RuntimePlan`, SDK config model, 내부 factory를 직접 알게 해서는 안 된다.

권장 의존 방향은 다음과 같다.

`environment -> docmesh config/assembly -> RAG-specific adapters -> RAGCore`

이 경계는 [[structural-integration-of-docmesh-py-core-into-docmesh-rag-system-core]]와 [[directory-refactoring-plan-for-docmesh-runtime-integration]]의 핵심이며, 향후 API·worker·MCP가 동일 bootstrap을 재사용할 수 있게 한다.

### 5. readiness는 required와 optional을 구분한다

startup health는 실제 필수 서비스에만 배포 차단 권한을 준다. 예를 들어 현재 실행에 Ollama와 Milvus가 필수라면 required로 두고, Langfuse 같은 관측 서비스는 optional로 유지한다. 병렬 healthcheck와 서비스별·전체 timeout, `StartupFailureMode.FAIL/REPORT`를 사용하되, 단순 boolean 대신 `HealthCheckResult.to_dict()` 또는 `HealthCheckError.result`를 보존해 부분 장애를 관측 가능하게 한다.

healthcheck를 매 요청마다 반복하지 않는다. startup readiness, 주기적 운영 probe, 사용자 요청 실패 처리는 서로 다른 정책이어야 한다. 상세 lifecycle과 rollback 규칙은 [[service-health-orchestration]]을 따른다.

### 6. DMS 설정과 lifecycle은 RAG 서비스 묶음과 분리한다

동일 process에서 RAG와 DMS가 서로 다른 PostgreSQL·SQLite·MinIO 설정을 사용할 때 process-global canonical key를 임시 변경하지 않는다. application composition 계층이 `DMS_` prefixed 설정을 별도로 파싱해 `ServiceConfigs`를 만들고 DMS factory에 전달한다. RAG bundle은 Ollama·Milvus 등 RAG 서비스만 소유하게 한다.

현재 위키에 기록된 repository 경로는 이 분리를 이미 적용했으며, DMS SDK를 먼저 닫고 RAG bundle을 닫는 lifecycle을 테스트한다. 이 계약은 [[separating-dms-service-environment-variables-with-prefixes]]와 [[dms-configuration-and-assembly]]를 기준으로 유지한다.

### 7. public root API와 얇은 adapter에만 결합한다

통합 코드는 `docmesh_config`와 `docmesh_py_core`의 package root 경계를 사용하고 내부 모듈 import를 피한다. RAG 쪽에는 SDK wrapper의 반환 차이를 흡수하는 얇은 adapter를 둔다. 특히 NATS builder처럼 다른 lifecycle을 가진 서비스 때문에 domain 코드가 분기하지 않게 한다. 이 규칙은 [[public-api-surface]]의 업그레이드 내성 원칙과 같다.

## 우선순위별 적용안

### P0 — 경로 수렴과 자원 소유권

- production bootstrap을 `DocmeshRAGServiceFactory.from_env()` 같은 단일 entrypoint로 고정
- 설정 로드와 bundle 생성은 process lifecycle에서 한 번만 수행
- `RAGCore`에는 완성된 adapter/storage/chunker만 주입
- bundle, DMS SDK, RAGCore가 각각 무엇을 닫는지 명시하고 역순 cleanup 검증

### P1 — 실패 비용과 운영성 개선

- assembly 전 `diagnose_services(plan=...)` 실행
- required/optional 서비스 분류와 startup timeout 명시
- config/health 오류를 secret-safe structured result로 노출
- optional 서비스 장애가 RAG 전체 readiness를 차단하지 않도록 정책 테스트

### P2 — 성능 계측과 확장

- bootstrap 시간, 서비스별 health latency, client 재생성 횟수, pool 사용량 측정
- startup health의 병렬화 효과를 실제 지표로 확인
- NATS가 도입될 때만 async runtime으로 전환
- API·worker·CLI가 동일 composition entrypoint를 재사용하는 계약 테스트 추가

## 피해야 할 최적화

- `RAGCore` 안에서 환경변수를 다시 읽거나 client를 생성하는 것
- 요청마다 `load_service_configs()`와 `assemble_services()`를 호출하는 것
- 사용하지 않는 모든 서비스 설정을 필수로 검증하는 것
- optional observability 서비스를 required readiness로 승격하는 것
- 접두사 분리를 위해 `os.environ`을 임시 변경하는 것
- SDK 내부 모듈 import나 반환 구현형에 직접 결합하는 것
- 실제 계측 없이 sync 경로를 전부 async로 바꾸는 것

## 검증 체크리스트

1. 한 process lifecycle에서 서비스 bundle이 한 번만 생성되는가?
2. query/ingest 반복 호출에서 client 생성 횟수가 증가하지 않는가?
3. 필요한 서비스 설정만 검증하면서 부분 설정 오류는 즉시 실패하는가?
4. required 장애와 optional 장애가 readiness 결과에서 구분되는가?
5. startup 실패 시 이미 생성된 client가 rollback되는가?
6. 정상 종료와 예외 종료 모두에서 DMS SDK와 RAG bundle이 정확히 한 번 닫히는가?
7. domain tests가 실제 environment나 SDK concrete client 없이 실행되는가?
8. 통합 코드가 package root public API만 import하는가?
9. DMS prefixed 설정이 RAG의 canonical 설정과 섞이지 않는가?
10. bootstrap/health latency가 변경 전후 계측으로 개선되었는가?

## 종합 권고

현 상태에서 가장 효과가 큰 최적화는 새로운 abstraction을 더 만드는 것이 아니라 **단일 composition entrypoint, 최소 서비스 설정 로드, process-scope client 재사용, 명시적 health 정책, deterministic cleanup**을 고정하는 것이다. 그 다음에 실제 bootstrap 및 health 지표를 측정해 병렬화·timeout·async 전환 여부를 결정한다.

## Repository 적용 상태

2026-07-28에 production bootstrap과 lifecycle 최적화를 실제 repository에 적용했다.

- `bootstrap_rag_core_from_env(...)` context manager를 package root와 composition package의 공개 진입점으로 추가했다. 이 helper는 환경 기반 service factory를 한 번 생성하고 `RAGCore`를 조립하며, context 종료 시 factory가 소유한 DMS SDK와 RAG service bundle을 정리한다.
- `DocmeshRAGServiceFactory` 자체에 context manager 계약을 추가해 고급 사용자 정의 조립에서도 deterministic cleanup을 사용할 수 있게 했다.
- `DocmeshRAGServiceFactory.from_env(...)`에 `parallel_healthchecks`를 추가했다. 새 production helper는 `check_on_startup=True`, `parallel_healthchecks=True`를 기본값으로 사용해 Ollama와 Milvus startup readiness를 병렬 실행한다.
- 기존 DMS 설정 분리, DMS 우선 종료, DMS assembly 실패 시 RAG bundle rollback 계약은 그대로 유지했다.
- `README.md`의 production 사용 경로를 새 context manager 중심으로 변경하고 public root export를 동기화했다.

설치된 `docmesh-py-core` v0.5.0의 `assemble_services(..., parallel_healthchecks=...)`, `ServiceBundle` context manager, health API signature를 실행 환경에서 확인했다. 신규 테스트는 public export, 환경 bootstrap, 병렬 health 전달, DMS→bundle 종료 순서를 검증하며 전체 repository 테스트 83개, `compileall`, `git diff --check`가 통과했다. mypy는 변경 전후 모두 기존 15개 오류로 동일해 신규 type regression은 없었다. 이후 SDK 버전 변경 시에는 [[verifying-docmesh-py-core-contract]] 절차로 이 경계를 다시 확인해야 한다.

## Related pages

- [[docmesh-py-core]]
- [[docmesh-config]]
- [[developing-with-docmesh-py-core]]
- [[construction-paths-and-adapter-contracts]]
- [[settings-loading-and-validation]]
- [[service-health-orchestration]]
- [[separating-dms-service-environment-variables-with-prefixes]]
- [[verifying-docmesh-py-core-contract]]
- [[minimizing-consumer-implementation-with-docmesh-py-core-improvements]]
