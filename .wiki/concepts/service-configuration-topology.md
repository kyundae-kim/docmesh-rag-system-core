---
title: Service Configuration Topology
created: 2026-06-19
updated: 2026-06-23
type: concept
tags: [config, integration, architecture, security, observability]
sources: [raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-rag-core-config-guide-2026-06-23.md]
confidence: medium
---

# Service Configuration Topology

`docmesh-py-core` 설정 가이드는 외부 서비스별 환경변수 체계를 명시적으로 분리한다. Keycloak, PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS 각각이 독립된 기본값, timeout/retry, 인증 입력, health check 의미를 가지며, 공통 timeout/retry/pool을 두지 않고 서비스별 환경변수로 관리하는 점이 중요한 설계 원칙이다.^[raw/articles/docmesh-py-core-config-guide-2026-06-19.md]

## Service-specific behavior

이 구조는 같은 SDK 안에서도 서비스마다 운영 의미가 다름을 전제로 한다. 예를 들어 PostgreSQL은 DSN 우선 규칙과 connection pool 파라미터를 갖고, SQLite는 `:memory:` 및 WAL/busy-timeout 같은 로컬 저장소 특성을 가진다. Langfuse는 선택적 기능으로 비활성화 가능하지만 Keycloak과 MinIO는 기본적으로 명시적인 연결 정보를 요구한다.^[raw/articles/docmesh-py-core-config-guide-2026-06-19.md]

## RAG-core specific slice

RAG Core config guide는 이 topology 중 첫 성공 호출에 실제로 자주 필요한 값을 좁혀 보여 준다. 실질적으로 중요한 값은 `OLLAMA_HOST`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_GENERATION_MODEL`, 선택적 `OLLAMA_REQUEST_TIMEOUT_SECONDS`, 선택적 `MILVUS_URI`, `MILVUS_COLLECTION`, `MILVUS_REQUEST_TIMEOUT_SECONDS`, `MILVUS_CONNECT_TIMEOUT_SECONDS`, 그리고 조건부 `DOCMESH_AUTH_MODE`다. 반면 Keycloak 관련 상세 설정은 DocMesh 통합 경로에서만 필요하므로, RAG 설정 topology는 "전부 다 채우기"가 아니라 실행 경로별 부분집합 이해가 더 중요하다.^[raw/articles/docmesh-rag-core-config-guide-2026-06-23.md]

## Security and masking

문서는 secret/token/password/전체 DSN 또는 URI의 원문 노출을 금지하고, 필요 시 사용자명·비밀번호·query 민감값을 마스킹하라고 규정한다. 또한 Keycloak 관리자 계정은 최소 권한 원칙을 따르고 가능하면 사용자명/비밀번호보다 service account 방식을 우선 사용하도록 권장하므로, 서비스 구성 topology는 단순 연결 정보 모음이 아니라 보안 운영 규약의 집합이기도 하다.^[raw/articles/docmesh-py-core-config-guide-2026-06-19.md]

## Related pages

- [[first-success-configuration]]
- [[settings-loading-and-validation]]
- [[construction-paths-and-adapter-contracts]]
- [[docmesh-py-core]]
- [[service-health-orchestration]]
