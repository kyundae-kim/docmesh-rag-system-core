# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: 2026-06-19 | Total pages: 16

## Entities
- [[docmesh-py-core]] — 설정 로드, 서비스 client 생성, health check, Keycloak 인증을 공통화하는 DocMesh Python SDK 엔티티 페이지.
- [[ragcore]] — DocMesh RAG Core의 단일 public SDK 진입점과 역할, 제약, 관련 인터페이스를 정리한 엔티티 페이지.
<!-- Alphabetical within section -->

## Concepts
- [[ingestion-pipeline]] — 문서 입력, 청킹, 임베딩, progress 추적, vector store 적재까지의 ingest 흐름.
- [[interface-roadmap]] — SDK 중심 현재 구조에서 API/MCP 등 후속 인터페이스 확장 방향.
- [[keycloak-auth-service]] — Keycloak 토큰 발급, JWT 검증, provisioning 경계를 정리한 인증 API 개념 페이지.
- [[persistence-and-restart-recovery]] — SQLite, Milvus Lite, storage_path 기반 자산 관리와 재시작 복원 요구.
- [[project-roadmap]] — SDK canonical core를 기준으로 API, 비동기 운영, MCP, 저장소 확장까지 단계별 실행 순서를 정리한 로드맵.
- [[public-api-surface]] — 공식 import 경로, public 메서드, adapter contract를 정리한 API 개념 페이지.
- [[rag-service-architecture]] — RAGCore facade 아래 ingestion/retrieval/generation/metadata 책임 분리 구조.
- [[service-configuration-topology]] — 서비스별 환경변수 체계, timeout/retry, 보안 마스킹 규칙을 정리한 구성 토폴로지 페이지.
- [[service-factory-registry]] — load_settings와 create_client 패턴을 중심으로 한 서비스 초기화/선택 조정 계층.
- [[service-health-orchestration]] — check/check_all_services 기반 startup readiness와 required/optional 서비스 정책.
- [[settings-loading-and-validation]] — 환경변수 로드, 조건부 필수값 검증, 운영/테스트 분리 규칙을 정리한 설정 개념 페이지.
- [[user-scope-isolation]] — token 기반 user scope와 데이터 격리 계약, 적용 지점, 향후 인증 확장 고려사항.

## Comparisons

## Queries
- [[future-considerations-for-sdk-api-mcp-rag-project]] — SDK 중심 RAG 코어를 API/MCP로 확장할 때의 구조, 운영, 버전, 보안, 비동기 고려사항.
- [[sdk-first-with-api-and-mcp-evaluation]] — SDK를 canonical core로 두고 API/MCP를 별도 adapter product로 확장하는 전략 평가.
