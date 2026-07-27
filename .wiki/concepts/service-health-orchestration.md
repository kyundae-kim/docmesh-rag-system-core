---
title: Service Health Orchestration
created: 2026-06-19
updated: 2026-07-27
type: concept
tags: [sdk, integration, testing, deployment, observability]
sources: [raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md, raw/articles/docmesh-rag-core-srs-2026-06-23.md, raw/articles/docmesh-rag-core-prd-2026-06-23.md, raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-examples-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-examples-v0.5.0-2026-07-27.md]
confidence: medium
---

# Service Health Orchestration

`docmesh-py-core`의 SDK 소비 가이드는 단순한 설정 검증만으로 충분하지 않다고 보고, 각 서비스 client의 `check()`를 통해 실제 연결 가능성을 startup 초기에 검증하는 패턴을 권장한다. PostgreSQL과 SQLite는 `SELECT 1`, MinIO는 `list_buckets()`, NATS는 `connect()` 후 `flush()`까지 포함한 연결 확인이 기본 health 계약으로 제시된다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Aggregated readiness

여러 서비스를 함께 점검할 때는 `check_all_services()`로 health 함수를 맵으로 넘기고 `required_services` 집합으로 필수 의존성과 선택 의존성을 구분한다. `parallel=True`를 선택할 수 있으며, required 실패의 `HealthCheckError`는 결과를 보존하므로 서버 readiness 정책은 부분 장애와 필수 장애를 구별할 수 있다. async lifecycle에는 sync 함수와 awaitable을 함께 처리하고 서비스별·전체 timeout을 구분하는 `async_check_all_services()`를 사용한다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]

## Result and failure model

API reference와 예제는 `check_all_services()`의 반환/예외 모델도 명시한다. 반환값은 전체 성공 여부를 나타내는 `HealthCheckResult.ok`와 서비스별 상태를 포함하며, 필수 서비스 실패 시에는 `HealthCheckError`가 발생한다. 호출자는 단순 boolean만 볼 것이 아니라 `result.to_dict()`를 통해 필수 실패와 부분 실패를 분리해 관측/응답 정책을 설계해야 한다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]^[raw/articles/docmesh-py-core-examples-v0.5.0-2026-07-27.md]

## How the RAG SRS uses this pattern

RAG Core의 SRS는 모든 health-check 결과에 metadata health를 포함해야 하고, vector store / embedding client / generation client가 `check()`를 제공하면 그 정보도 포함해야 한다고 규정한다. 또한 DocMesh aggregate health path를 우선 시도하고 실패 시 local aggregation으로 fallback 해야 하므로, 이 페이지는 generic SDK 패턴이 아니라 현재 RAG 라이브러리의 명시적 요구사항 해석에도 직접 연결된다.^[raw/articles/docmesh-rag-core-srs-2026-06-23.md]^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Parallelism and lifecycle

동기 lifecycle은 `ServiceBundle`의 context manager와 `close()`로 관리할 수 있다. NATS를 포함하는 async lifecycle에는 `RuntimePlan`과 `ServiceRuntime`이 있으며, `HealthcheckPolicy`로 timeout·overall timeout·재시도·failure mode를 명시한다. 시작 또는 healthcheck 실패 시 assembly API는 이미 만든 client를 rollback하고, `async_close_service_clients()`는 종료 실패가 있어도 나머지 client를 best-effort로 정리한 뒤 집계된 `ServiceCloseError`를 낸다.^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]

## Risk points

서비스별 health check semantics가 서로 다르기 때문에 소비 프로젝트는 성공 기준을 동일하게 가정하면 안 된다. 특히 NATS는 비동기 builder 계약을 이해하지 못하면 readiness 코드에서 오용하기 쉽고, optional 서비스를 required로 잘못 분류하면 배포 가용성을 불필요하게 떨어뜨릴 수 있다. RAG Core 쪽에서는 이 리스크가 [[software-requirements-and-traceability]]의 health/composition 요구사항과 충돌하지 않도록 조정되어야 한다.

## Related pages

- [[software-requirements-and-traceability]]
- [[docmesh-py-core]]
- [[service-factory-registry]]
- [[product-scope-and-requirements]]
- [[project-roadmap]]
