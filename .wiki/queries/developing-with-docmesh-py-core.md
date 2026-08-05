---
title: Developing with docmesh-py-core
created: 2026-06-19
updated: 2026-08-04
type: query
tags: [sdk, python, integration, config, testing]
sources: [raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md, raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-examples-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-examples-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-api-reference-v0.6.0-2026-08-04.md, raw/articles/docmesh-py-core-configuration-v0.6.0-2026-08-04.md, raw/articles/docmesh-py-core-examples-v0.6.0-2026-08-04.md, raw/articles/docmesh-py-core-env-example-v0.6.0-2026-08-04.md]
confidence: medium
---

# Developing with docmesh-py-core

## Question

`docmesh-py-core`를 개발에 어떻게 활용하면 좋은가?

## Short answer

가장 좋은 활용 방식은 `docmesh-py-core`를 **애플리케이션의 공통 client/lifecycle SDK**로 두고, `docmesh-config`를 설정·진단·runtime plan의 canonical 경계로 두는 것이다. 비즈니스 로직은 앱/도메인 패키지에 두고, PostgreSQL·SQLite·MinIO·NATS·Ollama·Milvus·Keycloak 접속과 운영 규칙은 두 SDK의 config/assembly/health 경계에 위임한다. v0.6.0의 일반 애플리케이션 권장 경로는 registry 직접 조립이 아니라 `docmesh_config.RuntimePlan`을 `docmesh_py_core`의 assembly/lifespan API에 전달하는 **canonical split + assembly-first**다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0-2026-08-04.md]^[raw/articles/docmesh-py-core-configuration-v0.6.0-2026-08-04.md]

## Recommended development flow

1. `docmesh_config`에서 필요한 서비스와 required/optional/one-of 및 health policy를 포함한 `RuntimePlan`을 만든다.
2. 동기 서비스는 `assemble_services(plan=plan)`과 `ServiceBundle` context manager로 client와 cleanup을 조립한다.
3. NATS 또는 async lifecycle은 `await assemble_service_runtime(plan=plan)` 또는 `async with service_lifespan(plan=plan)`으로 조립하고 `runtime.require(Service.…)`로 client를 조회한다.
4. CLI·배치·테스트처럼 일부 서비스만 직접 다룰 때도 config model을 먼저 만들고 `create_*_client(config)`를 호출한다. 임의 kwargs나 별도 mapping을 전달하지 않는다.
5. health endpoint에서는 `check_all_services()`/`async_check_all_services()` 결과 또는 `HealthCheckError.result.to_dict()`를 응답으로 사용하고, startup policy는 `ServiceRuntime.check_with_policy()`에 맡긴다.

이 흐름은 [[docmesh-py-core]], [[service-factory-registry]], [[service-health-orchestration]]가 공통으로 전제하는 소비 패턴이다.

## Where it helps most

### 1. FastAPI / backend service bootstrap

Backend service의 lifespan에서는 `docmesh_config`로 plan을 만든 뒤 `with ServiceBundle` 또는 `async with service_lifespan(plan=plan)`으로 client 생성, startup healthcheck, rollback과 종료 cleanup을 응집시킬 수 있다. NATS persistent connection의 drain/close는 caller가 소유해야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.6.0-2026-08-04.md]^[raw/articles/docmesh-py-core-examples-v0.6.0-2026-08-04.md]

### 2. Worker / batch / CLI jobs

background worker나 배치 스크립트도 같은 설정 계약을 재사용할 수 있다. 이 점이 중요한 이유는 HTTP 서버만이 아니라 오프라인 ingest 작업, maintenance job, 운영 점검 스크립트도 동일한 외부 서비스 초기화 규칙을 따라야 하기 때문이다. [[settings-loading-and-validation]]의 환경변수 정책을 공유하면 환경 차이로 인한 drift를 줄일 수 있다.

### 3. Integration testing

통합 테스트에서도 `docmesh-py-core`는 유용하다. 테스트 코드가 서비스 mock wiring보다 실제 환경변수 계약과 readiness semantics를 검증하도록 만들 수 있기 때문이다. 특히 `.env.integration` 또는 CI secret 세트를 따로 두고, 테스트가 production bootstrap과 거의 같은 경로를 타게 하면 설정 누락이나 optional/required 서비스 분류 오류를 빨리 발견할 수 있다.

## Practical design rule

개발 시에는 `docmesh-py-core`를 **비즈니스 로직 프레임워크**로 보기보다 **공통 infra adapter layer**로 보는 편이 맞다.

- 애플리케이션이 결정할 것: 도메인 규칙, 요청 처리 흐름, 데이터 모델, 작업 orchestration
- `docmesh-config`에 맡길 것: 환경변수 parsing, typed config, 서비스 진단, `RuntimePlan` 정규화
- `docmesh-py-core`에 맡길 것: 서비스 client 생성, 인증/토큰 취급, health check, runtime lifecycle, 민감정보 마스킹

이 경계를 지키면 앱이 SDK 내부 구현 세부사항보다 안정적인 public surface에 의존하게 된다. 관련 import 원칙은 [[public-api-surface]]에 정리되어 있다.

## Usage recommendations

- 루트 import 경계를 우선 사용한다. 하위 내부 모듈 직접 import는 예외적으로만 허용한다.
- 서비스 선택은 `RuntimePlan`과 `SERVICE_CATALOG`으로 명시하고 실제 설정 존재 여부·진단 결과를 함께 사용한다.
- optional 서비스(Langfuse 등)와 required 서비스를 분리해서 readiness 정책을 설계한다.
- `ServiceBundle`/`ServiceRuntime` context manager로 종료 cleanup을 보장한다. 직접 생성한 client만 명시적으로 `close()`한다.
- NATS처럼 반환 계약이 다른 서비스는 앱 내부에서 얇은 래퍼를 둬 비동기 연결 차이를 흡수하는 것이 좋다.

## Common pitfalls

- 앱 코드가 `docmesh-py-core` 내부 모듈 경로에 직접 결합되면 SDK 업그레이드 내성이 약해진다.
- 설정 검증을 건너뛰고 서비스 client를 개별 생성하면 운영 환경에서 누락된 값이 늦게 터진다.
- config model 생성자에 kwargs나 환경 mapping을 전달하거나 `docmesh_py_core`가 설정 심볼을 재-export한다고 가정하면 v0.6.0 계약을 위반한다.
- optional 서비스를 required로 잘못 분류하면 배포 가용성이 불필요하게 떨어진다.
- 서비스별 반환 타입 차이(`ServiceClientWrapper` vs `NatsConnectionBuilder`)를 무시하면 bootstrap 코드가 복잡해진다.

## Recommendation

`docmesh-py-core`는 새 기능을 구현하는 도메인 코드의 중심이 아니라, **여러 Python 서비스가 공통 운영 규칙을 공유하게 만드는 기반 SDK**로 쓰는 것이 가장 효율적이다. 특히 DocMesh 계열 프로젝트처럼 API 서버, worker, ingest job, 운영 스크립트가 함께 존재하는 환경에서 가치가 크다.

## Related pages

- [[docmesh-py-core]]
- [[docmesh-config]]
- [[service-factory-registry]]
- [[service-health-orchestration]]
- [[settings-loading-and-validation]]
- [[public-api-surface]]
