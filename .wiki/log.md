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

## [2026-06-11] update | Project roadmap document
- Created concepts/project-roadmap.md
- Updated index.md
- Roadmap synthesized from:
  - concepts/interface-roadmap.md
  - queries/sdk-first-with-api-and-mcp-evaluation.md
  - queries/future-considerations-for-sdk-api-mcp-rag-project.md

## [2026-06-19] ingest | docmesh-py-core SDK guide
- Source ingested:
  - https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/sdk.md
- Raw file created:
  - raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md
- Wiki pages created:
  - entities/docmesh-py-core.md
  - concepts/service-factory-registry.md
  - concepts/service-health-orchestration.md
- Navigation updated:
  - index.md

## [2026-06-19] ingest | docmesh-py-core API guide
- Source ingested:
  - https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/api.md
- Raw file created:
  - raw/articles/docmesh-py-core-api-guide-2026-06-19.md
- Wiki pages created:
  - concepts/keycloak-auth-service.md
- Wiki pages updated:
  - entities/docmesh-py-core.md
  - concepts/service-factory-registry.md
  - concepts/service-health-orchestration.md
  - concepts/public-api-surface.md
- Navigation updated:
  - index.md

## [2026-06-19] ingest | docmesh-py-core config guide
- Source ingested:
  - https://github.com/kyundae-kim/docmesh-py-core/blob/main/docs/config.md
- Raw file created:
  - raw/articles/docmesh-py-core-config-guide-2026-06-19.md
- Wiki pages created:
  - concepts/settings-loading-and-validation.md
  - concepts/service-configuration-topology.md
- Wiki pages updated:
  - entities/docmesh-py-core.md
  - concepts/service-factory-registry.md
  - concepts/keycloak-auth-service.md
- Navigation updated:
  - index.md

## [2026-06-19] query | developing with docmesh-py-core
- Question:
  - docmesh-py-core를 개발에 활용하는 방법은?
- Wiki pages consulted:
  - entities/docmesh-py-core.md
  - concepts/public-api-surface.md
  - concepts/settings-loading-and-validation.md
  - concepts/service-factory-registry.md
  - concepts/service-health-orchestration.md
- Wiki pages created:
  - queries/developing-with-docmesh-py-core.md
- Navigation updated:
  - index.md

## [2026-06-19] query | structural integration of docmesh-py-core into docmesh-rag-system-core
- Question:
  - docmesh-rag-system-core에 어떻게 연결할지 구조 제안
- Wiki pages consulted:
  - concepts/interface-roadmap.md
  - concepts/rag-service-architecture.md
  - concepts/project-roadmap.md
  - concepts/user-scope-isolation.md
  - queries/future-considerations-for-sdk-api-mcp-rag-project.md
- Wiki pages created:
  - queries/structural-integration-of-docmesh-py-core-into-docmesh-rag-system-core.md
- Navigation updated:
  - index.md

## [2026-06-19] query | directory refactoring plan for docmesh runtime integration
- Question:
  - 이 구조 기준 디렉터리 리팩터링안
- Wiki pages created:
  - queries/directory-refactoring-plan-for-docmesh-runtime-integration.md
- Supporting plan created:
  - .hermes/plans/2026-06-19_171139-docmesh-runtime-directory-refactor.md
- Navigation updated:
  - index.md

## [2026-06-23] ingest | docs/prd.md
- Source captured:
  - raw/articles/docmesh-rag-core-prd-2026-06-23.md
- Source drift noted:
  - raw/articles/docmesh-rag-core-prd-2026-06-11.md and docs/prd.md now differ for the same source path
- Wiki pages created:
  - concepts/product-scope-and-requirements.md
- Wiki pages updated:
  - entities/ragcore.md
  - concepts/rag-service-architecture.md
  - concepts/public-api-surface.md
  - concepts/ingestion-pipeline.md
  - concepts/user-scope-isolation.md
  - concepts/persistence-and-restart-recovery.md
- Navigation updated:
  - index.md

## [2026-06-23] ingest | docs/srs.md
- Source captured:
  - raw/articles/docmesh-rag-core-srs-2026-06-23.md
- Wiki pages created:
  - concepts/software-requirements-and-traceability.md
- Wiki pages updated:
  - concepts/product-scope-and-requirements.md
  - concepts/public-api-surface.md
  - concepts/persistence-and-restart-recovery.md
  - concepts/service-health-orchestration.md
  - concepts/rag-service-architecture.md
- Navigation updated:
  - index.md

## [2026-06-23] ingest | docs/api.md
- Source captured:
  - raw/articles/docmesh-rag-core-api-reference-2026-06-23.md
- Source drift noted:
  - raw/articles/docmesh-rag-core-api-reference-2026-06-11.md and docs/api.md now differ for the same source path
- Wiki pages created:
  - concepts/construction-paths-and-adapter-contracts.md
- Wiki pages updated:
  - concepts/public-api-surface.md
  - entities/ragcore.md
  - concepts/service-factory-registry.md
  - concepts/user-scope-isolation.md
- Navigation updated:
  - index.md
