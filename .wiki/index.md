# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: 2026-06-11 | Total pages: 9

## Entities
<!-- Alphabetical within section -->
- [[ragcore]] — DocMesh RAG Core의 단일 public SDK 진입점과 역할, 제약, 관련 인터페이스를 정리한 엔티티 페이지.

## Concepts
- [[ingestion-pipeline]] — 문서 입력, 청킹, 임베딩, progress 추적, vector store 적재까지의 ingest 흐름.
- [[interface-roadmap]] — SDK 중심 현재 구조에서 API/MCP 등 후속 인터페이스 확장 방향.
- [[persistence-and-restart-recovery]] — SQLite, Milvus Lite, storage_path 기반 자산 관리와 재시작 복원 요구.
- [[public-api-surface]] — 공식 import 경로, public 메서드, adapter contract를 정리한 API 개념 페이지.
- [[rag-service-architecture]] — RAGCore facade 아래 ingestion/retrieval/generation/metadata 책임 분리 구조.
- [[user-scope-isolation]] — token 기반 user scope와 데이터 격리 계약, 적용 지점, 향후 인증 확장 고려사항.

## Comparisons

## Queries
- [[future-considerations-for-sdk-api-mcp-rag-project]] — SDK 중심 RAG 코어를 API/MCP로 확장할 때의 구조, 운영, 버전, 보안, 비동기 고려사항.
- [[sdk-first-with-api-and-mcp-evaluation]] — SDK를 canonical core로 두고 API/MCP를 별도 adapter product로 확장하는 전략 평가.
