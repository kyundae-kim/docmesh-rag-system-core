# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: 2026-07-28 | Total pages: 32

## Entities
- [[dms-core]] — PostgreSQL/SQLite metadata와 MinIO object storage를 조합해 문서 lifecycle을 제공하는 DMS Python SDK.
- [[docmesh-py-core]] — 설정 로드, 서비스 client 생성, health check, Keycloak 인증을 공통화하는 DocMesh Python SDK 엔티티 페이지.
- [[ragcore]] — DocMesh RAG Core의 단일 public SDK 진입점과 역할, 제약, 관련 인터페이스를 정리한 엔티티 페이지.
<!-- Alphabetical within section -->

## Concepts
- [[construction-paths-and-adapter-contracts]] — RAGCore 직접 조립 경로, bootstrap 경로, helper fallback, adapter 계약을 정리한 개념 페이지.
- [[dms-configuration-and-assembly]] — DMS metadata backend 선택, factory별 자원 소유권, healthcheck·보안 설정을 정리한 개념 페이지.
- [[dms-document-lifecycle]] — DMS 업로드·stream·idempotency·cursor 조회·삭제의 lifecycle 계약.
- [[dms-metadata-and-recovery]] — DMS metadata policy, structured validation, reconciliation, HTTP error adapter를 정리한 개념 페이지.
- [[first-success-configuration]] — single-user, local storage, Ollama + Milvus Lite fallback 기준의 최소 성공 설정 경로.
- [[ingestion-pipeline]] — 문서 입력, 청킹, 임베딩, progress 추적, vector store 적재까지의 ingest 흐름.
- [[interface-roadmap]] — SDK 중심 현재 구조에서 API/MCP 등 후속 인터페이스 확장 방향.
- [[keycloak-auth-service]] — Keycloak 토큰 발급, JWT 검증, provisioning 경계를 정리한 인증 API 개념 페이지.
- [[persistence-and-restart-recovery]] — SQLite, Milvus Lite, storage_path 기반 자산 관리와 재시작 복원 요구.
- [[product-scope-and-requirements]] — 현재 PRD 기준 제품 범위, 제외 범위, acceptance contract를 요약한 개념 페이지.
- [[project-roadmap]] — SDK canonical core를 기준으로 API, 비동기 운영, MCP, 저장소 확장까지 단계별 실행 순서를 정리한 로드맵.
- [[public-api-surface]] — 공식 import 경로, public 메서드, adapter contract를 정리한 API 개념 페이지.
- [[rag-service-architecture]] — RAGCore facade 아래 ingestion/retrieval/generation/metadata 책임 분리 구조.
- [[service-configuration-topology]] — 서비스별 환경변수 체계, timeout/retry, 보안 마스킹 규칙을 정리한 구성 토폴로지 페이지.
- [[service-factory-registry]] — load_settings와 create_client 패턴을 중심으로 한 서비스 초기화/선택 조정 계층.
- [[service-health-orchestration]] — check/check_all_services 기반 startup readiness와 required/optional 서비스 정책.
- [[settings-loading-and-validation]] — 환경변수 로드, 조건부 필수값 검증, 운영/테스트 분리 규칙을 정리한 설정 개념 페이지.
- [[software-requirements-and-traceability]] — SRS 기준 기능/비기능/데이터 요구사항과 docs/test 추적성 경계를 정리한 개념 페이지.
- [[user-scope-isolation]] — token 기반 user scope와 데이터 격리 계약, 적용 지점, 향후 인증 확장 고려사항.

## Comparisons

## Queries
- [[applying-dms-core-as-document-storage]] — dms-core를 원문 lifecycle 경계로 적용하고 RAG metadata·user scope·삭제 복구와 결합하는 방법.
- [[directory-refactoring-plan-for-docmesh-runtime-integration]] — docmesh runtime 연동을 domain/storage/adapters/composition 경계로 재배치하는 디렉터리 리팩터링안.
- [[developing-with-docmesh-py-core]] — docmesh-py-core를 공통 infra SDK로 활용하는 개발 흐름, 적용 지점, 운영상 주의점을 정리한 질의 응답 페이지.
- [[future-considerations-for-sdk-api-mcp-rag-project]] — SDK 중심 RAG 코어를 API/MCP로 확장할 때의 구조, 운영, 버전, 보안, 비동기 고려사항.
- [[optimizing-docmesh-py-core-adoption]] — lifecycle 소유 environment bootstrap, 병렬 startup health, deterministic cleanup을 포함한 docmesh-py-core 적용 최적화와 구현 결과.
- [[sdk-first-with-api-and-mcp-evaluation]] — SDK를 canonical core로 두고 API/MCP를 별도 adapter product로 확장하는 전략 평가.
- [[separating-dms-service-environment-variables-with-prefixes]] — DMS용 PostgreSQL·SQLite·MinIO 환경변수를 `DMS_` 접두사로 격리하는 SDK 제약, composition 구현 및 검증 결과.
- [[structural-integration-of-docmesh-py-core-into-docmesh-rag-system-core]] — docmesh-py-core를 config/auth/bootstrap 계층으로 두고 rag-system-core와 분리 결합하는 구조 제안.
- [[verifying-dms-core-contract]] — dms-core의 공개 API, 설정·조립, 문서 lifecycle, 멱등성, 복구, 보안 및 소비 프로젝트 회귀 계약을 검증하는 절차.
- [[verifying-docmesh-py-core-contract]] — 버전 업데이트 시 공개 API, 설정, assembly·lifecycle, health/error 및 소비 프로젝트 회귀 계약을 검증하는 절차.
