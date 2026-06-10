# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [2026-06-11] create | Wiki initialized
- Domain: LLM을 활용한 Python 기반 RAG 시스템 (SDK 중심, 향후 API/MCP 등 인터페이스 확장 예정)
- Structure created with SCHEMA.md, index.md, log.md
- Directories created:
  - raw/articles/
  - raw/papers/
  - raw/transcripts/
  - raw/assets/
  - entities/
  - concepts/
  - comparisons/
  - queries/

## [2026-06-11] ingest | Project docs bootstrap (api/prd/test)
- Sources ingested:
  - docs/api.md
  - docs/prd.md
  - docs/test.md
- Raw files created:
  - raw/articles/docmesh-rag-core-api-reference-2026-06-11.md
  - raw/articles/docmesh-rag-core-prd-2026-06-11.md
  - raw/articles/docmesh-rag-core-test-spec-2026-06-11.md
- Wiki pages created:
  - entities/ragcore.md
  - concepts/public-api-surface.md
  - concepts/rag-service-architecture.md
  - concepts/ingestion-pipeline.md
  - concepts/user-scope-isolation.md
  - concepts/persistence-and-restart-recovery.md
  - concepts/interface-roadmap.md
- Navigation updated:
  - index.md

## [2026-06-11] query | SDK-first + API/MCP strategy evaluation
- Query filed to queries/sdk-first-with-api-and-mcp-evaluation.md
- Based on pages:
  - concepts/public-api-surface.md
  - concepts/rag-service-architecture.md
  - concepts/user-scope-isolation.md
  - concepts/persistence-and-restart-recovery.md
  - concepts/interface-roadmap.md

## [2026-06-11] query | Future considerations for SDK/API/MCP project
- Query filed to queries/future-considerations-for-sdk-api-mcp-rag-project.md
- Based on pages:
  - concepts/public-api-surface.md
  - concepts/rag-service-architecture.md
  - concepts/user-scope-isolation.md
  - concepts/persistence-and-restart-recovery.md
  - concepts/interface-roadmap.md
  - queries/sdk-first-with-api-and-mcp-evaluation.md

