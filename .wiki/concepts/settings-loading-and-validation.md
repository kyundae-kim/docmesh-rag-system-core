---
title: Settings Loading and Validation
created: 2026-06-19
updated: 2026-07-27
type: concept
tags: [config, sdk, python, security, decision]
sources: [raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-rag-core-config-guide-2026-06-23.md, raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md, raw/articles/docmesh-py-core-env-example-v0.5.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]
confidence: medium
---

# Settings Loading and Validation

`docmesh-py-core` v0.5.0은 모든 설정을 환경변수에서 읽는다. 공백 문자열은 미설정으로 처리하고 boolean·숫자·CSV 목록은 typed parsing과 범위 검증을 통과해야 한다. 선택한 서비스만 검증하려면 `load_service_configs(services={...})`, 후보 중 인식 가능한 환경변수가 있는 서비스만 탐색하려면 `load_available_service_configs(services={...})`를 사용한다. 후자는 부분 설정을 유효한 것으로 보지 않고 오류로 처리하며, 이 로딩 경로의 검증 실패는 remediation을 포함하는 `ConfigError.issues`로 제공된다.^[raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md]

## Validation scope

검증 대상은 단순 필수 여부를 넘어 조건부 필수 규칙과 보안 규칙까지 포함한다. `LANGFUSE_ENABLED=false`이면 Langfuse 연결 값 없이 로딩할 수 있고, PostgreSQL은 지원하지 않는 legacy DSN 없이 host/db/user/password 조합을 요구한다. `KEYCLOAK_TOKEN_GRANT_TYPE=password`는 설정 로딩 단계에서는 username/password를 강제하지 않으며, 실제 `fetch_access_token()` 호출 시 함수 인자와 config 양쪽에 완전한 자격증명이 없을 때 오류가 난다.^[raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md]

## RAG-core reading model

RAG Core의 config guide는 모든 설정이 항상 필요한 것이 아니라, first-success 경로와 DocMesh-integrated 경로가 서로 다른 설정 집합을 요구한다고 정리한다. 즉 `load_docmesh_settings()`와 registry를 쓰는 bootstrap 경로에서는 공통 DocMesh config contract를 따르지만, helper + `RAGCore(...)` 직접 조립 경로에서는 사실상 `OLLAMA_HOST`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_GENERATION_MODEL`과 writable 경로가 우선이다. 이 차이는 설정 로딩 계층이 "단일 필수 집합"이 아니라 사용 경로에 따른 다층 계약임을 보여 준다.^[raw/articles/docmesh-rag-core-config-guide-2026-06-23.md]

## DMS diagnosis before assembly

`dms-core`는 `diagnose_environment(env)`로 입력 mapping을 바꾸거나 연결을 만들지 않고 metadata backend 선택, object backend, startup healthcheck, 누락 key, warning, unsupported key를 판정한다. 환경 factory는 이 규칙을 따라 PostgreSQL/SQLite와 MinIO를 조립하며, legacy `POSTGRES_DSN`은 항상 unsupported로 진단한다. 따라서 host application은 [[dms-configuration-and-assembly]]에 따라 배포 전 secret-safe 진단을 수행하고, 실패한 `ConfigurationError.diagnosis`를 운영자용 오류 처리에 활용할 수 있다.^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]

## Operational policy

운영 판정은 `DOCMESH_SECURITY_MODE`가 있으면 이를 우선하고, 없으면 자유 문자열인 `DOCMESH_ENV`를 `DOCMESH_PRODUCTION_ALIASES`(기본 `prod,production`)와 비교한다. production에서는 `KEYCLOAK_VERIFY_SSL=false`, `MINIO_SECURE=false`, `MINIO_CERT_CHECK=false`, `MILVUS_SECURE=false`, `OLLAMA_VERIFY_SSL=false`가 금지된다. startup healthcheck는 환경변수가 아니라 `RuntimePlan.healthcheck`로 명시하며, `diagnose_services(plan=...)`는 네트워크 연결 전에 설정/보안 위반을 반환한다.^[raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md]^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]

## Related pages

- [[first-success-configuration]]
- [[keycloak-auth-service]]
- [[docmesh-py-core]]
- [[service-factory-registry]]
- [[service-configuration-topology]]
