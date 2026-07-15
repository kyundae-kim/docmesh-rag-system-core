---
title: Service Configuration Topology
created: 2026-06-19
updated: 2026-07-16
type: concept
tags: [config, integration, architecture, security, observability]
sources: [raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-rag-core-config-guide-2026-06-23.md, raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md]
confidence: medium
---

# Service Configuration Topology

`docmesh-py-core` v0.2.0은 Keycloak, PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS를 독립된 config 모델로 분리한다. 서비스별 기본값·timeout/retry·인증 입력·healthcheck 의미가 다르며, 공통 timeout/retry/pool로 평탄화하지 않는다. 또한 모든 config 값이 SDK 생성자에 직접 전달되는 것은 아니다. MinIO의 bucket/timeout/retry, Milvus의 collection/connect timeout/retry/secure, Ollama의 model/retry는 각 typed `RuntimeDefaults`에 보존되어 소비 계층이 활용할 수 있다.^[raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md]

## Service-specific behavior

이 구조는 같은 SDK 안에서도 서비스마다 운영 의미가 다름을 전제로 한다. PostgreSQL은 DSN 우선 또는 host/db/user/password 조합과 pool 설정을 쓰고, SQLite는 `:memory:`, readonly, WAL, busy timeout을 지원하되 상위 디렉터리를 생성하지 않는다. Langfuse는 `LANGFUSE_ENABLED=false`로 비활성화 가능하다. NATS는 user/password, token, creds-file 중 최대 하나의 인증 방식만 허용하며, NATS builder의 healthcheck는 임시 연결 후 `flush()`를 확인한다.^[raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md]

## RAG-core specific slice

RAG Core config guide는 이 topology 중 첫 성공 호출에 실제로 자주 필요한 값을 좁혀 보여 준다. 실질적으로 중요한 값은 `OLLAMA_HOST`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_GENERATION_MODEL`, 선택적 `OLLAMA_REQUEST_TIMEOUT_SECONDS`, 선택적 `MILVUS_URI`, `MILVUS_COLLECTION`, `MILVUS_REQUEST_TIMEOUT_SECONDS`, `MILVUS_CONNECT_TIMEOUT_SECONDS`, 그리고 조건부 `DOCMESH_AUTH_MODE`다. 반면 Keycloak 관련 상세 설정은 DocMesh 통합 경로에서만 필요하므로, RAG 설정 topology는 "전부 다 채우기"가 아니라 실행 경로별 부분집합 이해가 더 중요하다.^[raw/articles/docmesh-rag-core-config-guide-2026-06-23.md]

## Security and masking

문서는 secret/token/password/전체 DSN 또는 URI의 원문 노출을 금지하고, 필요 시 사용자명·비밀번호·query 민감값을 마스킹하라고 규정한다. production 판정 환경에서는 Keycloak SSL 검증, MinIO HTTPS, Milvus TLS를 비활성화할 수 없다. Keycloak 프로비저닝은 service account secret 또는 admin username/password 중 정확히 하나의 인증 방식을 요구하므로, 서비스 구성 topology는 단순 연결 정보 모음이 아니라 보안 운영 규약의 집합이기도 하다.^[raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md]

## Related pages

- [[first-success-configuration]]
- [[settings-loading-and-validation]]
- [[keycloak-auth-service]]
- [[construction-paths-and-adapter-contracts]]
- [[docmesh-py-core]]
- [[service-health-orchestration]]
