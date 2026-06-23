---
title: Settings Loading and Validation
created: 2026-06-19
updated: 2026-06-23
type: concept
tags: [config, sdk, python, security, decision]
sources: [raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-rag-core-config-guide-2026-06-23.md]
confidence: medium
---

# Settings Loading and Validation

`docmesh-py-core` 설정 가이드는 모든 설정을 환경변수에서 읽고 애플리케이션 시작 시 1회 로드/검증하는 것을 기본 정책으로 둔다. 공백 문자열은 미설정으로 간주하고, boolean은 대소문자와 무관하게 `true`/`false`로 해석하며, 숫자형은 허용 범위를 검증한다. 이 규칙은 `load_settings()`가 단순 매핑 로더가 아니라 운영 정책을 반영한 검증 게이트라는 점을 보여 준다.^[raw/articles/docmesh-py-core-config-guide-2026-06-19.md]

## Validation scope

검증 대상은 단순 필수 여부를 넘어 조건부 필수 규칙과 보안 규칙까지 포함한다. 예를 들어 `KEYCLOAK_TOKEN_GRANT_TYPE=password`이면 사용자명/비밀번호가 필요하고, `LANGFUSE_ENABLED=false`이면 Langfuse 관련 값은 선택 처리 가능하며, PostgreSQL은 `POSTGRES_DSN`이 없을 때 host/db/user/password 조합을 요구한다.^[raw/articles/docmesh-py-core-config-guide-2026-06-19.md]

## RAG-core reading model

RAG Core의 config guide는 모든 설정이 항상 필요한 것이 아니라, first-success 경로와 DocMesh-integrated 경로가 서로 다른 설정 집합을 요구한다고 정리한다. 즉 `load_docmesh_settings()`와 registry를 쓰는 bootstrap 경로에서는 공통 DocMesh config contract를 따르지만, helper + `RAGCore(...)` 직접 조립 경로에서는 사실상 `OLLAMA_HOST`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_GENERATION_MODEL`과 writable 경로가 우선이다. 이 차이는 설정 로딩 계층이 "단일 필수 집합"이 아니라 사용 경로에 따른 다층 계약임을 보여 준다.^[raw/articles/docmesh-rag-core-config-guide-2026-06-23.md]

## Operational policy

문서는 로컬/개발/스테이징/운영을 코드가 아니라 환경변수로 구분하고, 운영에서는 TLS 및 인증서 검증을 기본값으로 유지하라고 권장한다. 또한 integration 테스트는 운영 설정과 분리된 `.env.integration` 또는 별도 CI secret 세트를 사용해야 하므로, 설정 로딩 계층은 기능 스위치뿐 아니라 배포 격리 정책의 경계이기도 하다.^[raw/articles/docmesh-py-core-config-guide-2026-06-19.md]

## Related pages

- [[first-success-configuration]]
- [[keycloak-auth-service]]
- [[docmesh-py-core]]
- [[service-factory-registry]]
- [[service-configuration-topology]]
