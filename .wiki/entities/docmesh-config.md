---
title: docmesh-config
created: 2026-08-04
updated: 2026-08-08
type: entity
tags: [sdk, python, config, security, integration, testing]
sources: []
confidence: low
---

> **Source status (2026-08-08):** The raw captures previously cited by this page were removed during wiki cleanup. Re-ingest authoritative sources before relying on these implementation-specific claims.

# docmesh-config

`docmesh-config`는 DocMesh 계열 Python 애플리케이션의 환경 설정, 서비스 선택 진단, runtime plan 메타데이터, 민감정보 보호를 공통화하는 설정 SDK다. v0.1.0 문서는 package root의 `__all__`을 안정 API 기준으로 삼고, `docmesh_config.config`는 설정 모델·로딩·진단 중심의 호환 facade로 둔다.

## 역할과 경계

이 패키지는 외부 서비스에 연결하거나 client를 생성하지 않는다. 설정 모델은 `Model()` 형태로만 만들며 constructor keyword 인자로 값을 주입할 수 없고, 그런 인자는 `TypeError`로 거부된다. `load_service_configs(services=...)`처럼 서비스를 명시하면 선택한 모든 서비스가 완전하고 유효해야 한다. `services`를 생략하면 환경변수가 존재하는 서비스를 optional 후보로 자동 감지한다. `load_available_service_configs()`는 관련 환경변수가 전혀 없는 서비스는 생략하지만, 부분 설정은 조용히 건너뛰지 않고 `ConfigError`를 발생시킨다. 환경이 실제로 구성되었는지는 `diagnose_services()`가 네트워크 연결 없이 판정한다.

`docmesh-py-core` v0.6.0은 `RuntimePlan`을 기준으로 `assemble_services()`, `assemble_service_runtime()`, `service_lifespan()`에서 client 생성·lifecycle·실제 health check를 조립한다. 따라서 `docmesh-config`는 그 앞단의 typed configuration과 선택 정책을 소유하고, 두 패키지의 설정 검증과 runtime assembly/lifespan 경계를 분리한다. 이 관계는 [[settings-loading-and-validation]]과 현재 조립 경계를 설명하는 [[service-factory-registry]]에서 함께 확인할 수 있다.

## 지원 서비스와 설정 계약

`CommonConfig`와 8개 서비스 설정 모델이 총 98개 환경변수를 추적한다.

- Keycloak: discovery, token, provisioning, realm/client metadata; provisioning 활성화 시 admin 인증 방식 정확히 하나
- PostgreSQL: host/db/user/password, pool 및 timeout metadata
- SQLite: path, readonly, WAL, busy timeout
- MinIO: endpoint, credentials, secure/cert check, bucket
- Milvus: `MILVUS_ENDPOINT`, token, database/collection, secure 정책; `MILVUS_URI`/`.uri` compatibility alias 없음
- Ollama: host, TLS 검증, generation/embedding model, timeout/retry
- Langfuse: 기본 enabled 상태, 활성화 시 host/public key/secret key 필수, tracing 및 flush 설정
- NATS: 하나 이상의 server URL 목록, 세 인증 방식 중 최대 하나, reconnect/heartbeat 설정

환경변수는 대소문자를 구분하지 않고 공백 값은 미설정으로 처리한다. `.env` 파일을 자동 로드하지 않으므로 애플리케이션이나 배포 도구가 프로세스 환경으로 주입해야 한다. 라이브러리가 생성하는 `repr`·`str`·직렬화·validation error·diagnosis 결과에는 secret, token, password, endpoint credential 원문이 노출되지 않는다. 다만 호출자가 별도로 남기는 로그나 외부 SDK 오류 메시지까지 자동 정제하는 것은 아니다.

## Runtime plan과 진단

`RuntimePlan`은 선택 서비스, required 여부, `one_of` 대안 그룹, MinIO bucket 요구, startup healthcheck 정책을 immutable 값으로 묶는다. 최소 한 서비스가 필요하고, 중복 서비스·빈 `one_of` 그룹·선택 목록에 없는 `one_of` 서비스는 허용하지 않는다. `minio_bucket_required=True`이면 MinIO가 선택되어야 한다. `HealthcheckPolicy`는 상태 확인을 직접 실행하지 않고 timeout, retry, 병렬성, startup failure mode 같은 runtime 정책만 표현한다.

`diagnose_services()`의 서비스 상태는 `absent`, `complete`, `partial`, `invalid` 중 하나다. `auto`와 `explicit`에서는 대안 그룹에 구성된 서비스가 하나 이상이면 충족하고, `strict`에서는 정확히 하나만 구성되어야 한다. `build_runtime_plan_metadata()`는 plan과 진단 결과를 결합하지만 executable object나 설정 원문은 포함하지 않는 secret-safe 결과를 만든다.

## 보안 규칙과 오류 모델

`DOCMESH_SECURITY_MODE=production`은 `DOCMESH_ENV`보다 우선하며 `DOCMESH_PRODUCTION_ALIASES`도 production 판정에 사용된다. production 환경에서는 Keycloak SSL 검증, MinIO secure/cert check, Milvus secure, Ollama SSL 검증을 끌 수 없고 placeholder secret과 개발용 endpoint도 문제로 보고한다. `load_service_configs()`·`validate_service_requirements()`·`require_minio_bucket()`의 로딩/요구사항 검증 실패는 `ConfigError`로 표현한다. 반면 `diagnose_services()`는 예외 대신 `EnvironmentDiagnosis`의 `ok`, `issues`, `warnings`와 서비스별 상태를 반환하며, 직접 설정 모델 생성의 validation 오류는 Pydantic `ValidationError`다.

## Related pages

- [[docmesh-py-core]]
- [[settings-loading-and-validation]]
- [[service-configuration-topology]]
- [[service-factory-registry]]
- [[service-health-orchestration]]
