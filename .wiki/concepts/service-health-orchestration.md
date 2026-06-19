---
title: Service Health Orchestration
created: 2026-06-19
updated: 2026-06-19
type: concept
tags: [sdk, integration, testing, deployment, observability]
sources: [raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md]
confidence: medium
---

# Service Health Orchestration

`docmesh-py-core`의 SDK 소비 가이드는 단순한 설정 검증만으로 충분하지 않다고 보고, 각 서비스 client의 `check()`를 통해 실제 연결 가능성을 startup 초기에 검증하는 패턴을 권장한다. PostgreSQL과 SQLite는 `SELECT 1`, MinIO는 `list_buckets()`, NATS는 `connect()` 후 `flush()`까지 포함한 연결 확인이 기본 health 계약으로 제시된다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Aggregated readiness

여러 서비스를 함께 점검할 때는 `check_all_services()`로 health 함수를 맵으로 넘기고 `required_services` 집합으로 필수 의존성과 선택 의존성을 구분한다. 이 패턴은 필수 경로는 엄격하게 차단하면서도 Langfuse나 MinIO 같은 선택 서비스는 부분 장애로 처리할 수 있게 하므로 서버 readiness 정책 설계에 유용하다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Result and failure model

API 가이드는 `check_all_services()`의 반환/예외 모델도 명시한다. 반환값은 전체 성공 여부를 나타내는 `HealthCheckResult.ok`와 서비스별 상태 목록인 `HealthCheckResult.services`를 포함하며, 필수 서비스 실패 시에는 실패한 서비스명과 마스킹된 오류 메시지를 담은 `HealthCheckError`가 발생한다. 따라서 호출자는 단순 boolean만 볼 것이 아니라 필수 실패와 부분 실패를 분리해 관측/응답 정책을 설계해야 한다.^[raw/articles/docmesh-py-core-api-guide-2026-06-19.md]

## Parallelism and lifecycle

문서는 병렬 점검이 필요하면 `parallel=True`를 사용하라고 안내한다. 또한 FastAPI lifespan 예제처럼 시작 시점에 check를 수행하고 종료 시점에 registry close를 보장하는 구조를 제시하므로, health orchestration은 [[service-factory-registry]]의 생성/정리 수명주기와 분리해서 볼 수 없다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Risk points

서비스별 health check semantics가 서로 다르기 때문에 소비 프로젝트는 성공 기준을 동일하게 가정하면 안 된다. 특히 NATS는 비동기 builder 계약을 이해하지 못하면 readiness 코드에서 오용하기 쉽고, optional 서비스를 required로 잘못 분류하면 배포 가용성을 불필요하게 떨어뜨릴 수 있다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Related pages

- [[docmesh-py-core]]
- [[service-factory-registry]]
- [[project-roadmap]]
