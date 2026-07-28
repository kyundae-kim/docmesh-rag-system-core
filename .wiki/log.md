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

## [2026-06-23] ingest | docs/config.md
- Source captured:
  - raw/articles/docmesh-rag-core-config-guide-2026-06-23.md
- Wiki pages created:
  - concepts/first-success-configuration.md
- Wiki pages updated:
  - concepts/settings-loading-and-validation.md
  - concepts/service-configuration-topology.md
  - concepts/construction-paths-and-adapter-contracts.md
- Navigation updated:
  - index.md

## [2026-06-23] lint | 4 issues found
- Pages scanned: 23
- Raw sources scanned: 10
- Broken links: 0
- Orphans: 3
- Source drift/hash mismatches: 0
- Frontmatter issues: 0
- Tag issues: 1
- Index issues: 0
- Quality issues: 0
- Oversized pages: 0

## [2026-06-23] update | lint remediation
- Schema updated:
  - Added `persistence` to tag taxonomy in SCHEMA.md
- Inbound links added:
  - concepts/service-configuration-topology.md -> [[keycloak-auth-service]]
  - concepts/settings-loading-and-validation.md -> [[keycloak-auth-service]]
  - entities/docmesh-py-core.md -> [[developing-with-docmesh-py-core]]
  - concepts/rag-service-architecture.md -> [[directory-refactoring-plan-for-docmesh-runtime-integration]]
  - concepts/interface-roadmap.md -> [[directory-refactoring-plan-for-docmesh-runtime-integration]]

## [2026-07-16] ingest | docmesh-py-core API Reference v0.2.0
- Source ingested:
  - https://github.com/kyundae-kim/docmesh-py-core/blob/v0.2.0/docs/api.md
- Raw source created:
  - raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md
- Wiki pages updated:
  - entities/docmesh-py-core.md
  - concepts/public-api-surface.md
  - concepts/service-factory-registry.md
  - concepts/service-health-orchestration.md
- Navigation updated:
  - index.md


## [2026-07-16] ingest | docmesh-py-core Configuration Guide v0.2.0
- Source ingested:
  - https://github.com/kyundae-kim/docmesh-py-core/blob/v0.2.0/docs/config.md
- Raw source created:
  - raw/articles/docmesh-py-core-config-reference-v0.2.0-2026-07-16.md
- Wiki pages updated:
  - entities/docmesh-py-core.md
  - concepts/settings-loading-and-validation.md
  - concepts/service-configuration-topology.md
  - concepts/keycloak-auth-service.md
- Navigation checked:
  - index.md (no new page; already dated 2026-07-16)


## [2026-07-16] ingest | docmesh-py-core Examples v0.2.0
- Source ingested:
  - https://github.com/kyundae-kim/docmesh-py-core/blob/v0.2.0/docs/examples.md
- Raw source created:
  - raw/articles/docmesh-py-core-examples-v0.2.0-2026-07-16.md
- Wiki pages updated:
  - queries/developing-with-docmesh-py-core.md
  - concepts/service-health-orchestration.md
- Navigation checked:
  - index.md (no new page; already dated 2026-07-16)

## [2026-07-16] lint | 1 issue found and remediated
- Pages scanned: 23
- Raw sources scanned: 13
- Broken links: 0
- Orphans: 0
- Source drift/hash mismatches: 0
- Frontmatter issues: 0
- Tag issues: 0
- Index issues: 0
- Quality issues: 0
- Oversized pages: 0
- Stale pages: 0
- Contested pages: 0
- Log rotation: not required
- Remediation:
  - Removed accidental line-number prefixes from log.md and restored append-only log formatting.

## [2026-07-27] ingest | docmesh-py-core v0.5.0 API, configuration, examples, and environment template
- Sources ingested:
  - https://github.com/kyundae-kim/docmesh-py-core/wiki/API-Reference-v0.5.0
  - https://github.com/kyundae-kim/docmesh-py-core/wiki/Configuration-v0.5.0
  - https://github.com/kyundae-kim/docmesh-py-core/wiki/Examples-v0.5.0
  - https://github.com/kyundae-kim/docmesh-py-core/blob/v0.5.0/.env.example
- Raw sources created:
  - raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md
  - raw/articles/docmesh-py-core-configuration-v0.5.0-2026-07-27.md
  - raw/articles/docmesh-py-core-examples-v0.5.0-2026-07-27.md
  - raw/articles/docmesh-py-core-env-example-v0.5.0-2026-07-27.md
- Wiki pages updated:
  - entities/docmesh-py-core.md
  - concepts/public-api-surface.md
  - concepts/service-configuration-topology.md
  - concepts/settings-loading-and-validation.md
  - concepts/service-health-orchestration.md
  - queries/developing-with-docmesh-py-core.md
  - index.md
- Version update: v0.5.0 introduces RuntimePlan/Service assembly, diagnose_services(), and RuntimePlan.healthcheck; legacy PostgreSQL DSN and the prior healthcheck environment switch are not part of the v0.5.0 contract.

## [2026-07-27] ingest | dms-core v0.6.0 API, configuration, examples, and environment template
- Sources ingested:
  - https://github.com/kyundae-kim/dms-core/wiki/API-Reference-v0.6.0
  - https://github.com/kyundae-kim/dms-core/wiki/Configuration-v0.6.0
  - https://github.com/kyundae-kim/dms-core/wiki/Examples-v0.6.0
  - https://github.com/kyundae-kim/dms-core/blob/v0.6.0/.env.example
- Raw sources created:
  - raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md
  - raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md
  - raw/articles/dms-core-examples-v0.6.0-2026-07-27.md
  - raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md
- Wiki pages created:
  - entities/dms-core.md
  - concepts/dms-document-lifecycle.md
  - concepts/dms-metadata-and-recovery.md
  - concepts/dms-configuration-and-assembly.md
- Wiki pages updated:
  - concepts/public-api-surface.md
  - concepts/service-configuration-topology.md
  - concepts/settings-loading-and-validation.md
  - index.md
- Source note: GitHub Wiki raw endpoints expose the current wiki body; the supplied `v0.6.0` page names were preserved in source URLs and filenames, but no immutable wiki commit was supplied.

## [2026-07-27] query | docmesh-py-core 계약 검증 방법
- Query filed:
  - queries/verifying-docmesh-py-core-contract.md
- Navigation updated:
  - index.md
- Scope: package-root API, signature, strict configuration, RuntimePlan assembly, lifecycle cleanup, health/error shape, stale-symbol and consumer regression verification.
- Verification: 28 pages indexed; the new query page passed page/index/link checks.
- Pre-existing findings: 13 historical raw captures have body hash mismatches; immutable raw files were not modified.

## [2026-07-27] update | docmesh-py-core v0.5.0 계약 검증 실행
- Validated installed package version 0.5.0 against tag commit `b17a5a8dae6ddda4011a278bbe3aea655499a438`.
- Upstream result: 206 passed, 14 skipped; package-root exports: 86.
- SQLite sync bundle and async RuntimePlan smoke tests passed.
- Consumer result: 38 passed, 30 failed.
- Root cause: positional environment mapping passed to keyword-only `load_available_service_configs()`; the same violation exists in `assemble_services()` integration.
- Wiki page updated:
  - queries/verifying-docmesh-py-core-contract.md

## [2026-07-27] update | docmesh-py-core v0.5.0 소비 계약 오류 수정
- Removed positional environment mappings from config loading and service assembly wrappers.
- Aligned `DocmeshRAGServiceFactory.from_env()` and SDK test doubles with v0.5.0 keyword-only signatures.
- Renamed stale `v020` integration tests to `v050`.
- TDD result: 4 expected RED failures, then 4 passed after the production fix.
- Verification: 13 focused integration tests passed; full consumer suite 69 passed; compileall, diff check, and stale-symbol scan passed.
- Files updated:
  - rag_system_core/composition/docmesh_runtime.py
  - rag_system_core/composition/factories.py
  - test_rag_system_core/composition/test_docmesh_integration.py
  - README.md
  - queries/verifying-docmesh-py-core-contract.md

## [2026-07-27] query | dms-core 계약 검증 방법
- Query filed:
  - queries/verifying-dms-core-contract.md
- Navigation updated:
  - index.md
- Scope: package-root API, four assembly paths, configuration diagnosis, document lifecycle, idempotency, pagination, metadata safety, recovery, health/error semantics, and consumer regression verification.
- Live inspection: installed `dms 0.6.0`, 56 package-root exports; no current DMS imports or factory calls in the consumer source/tests.
- Documentation drift noted: live `diagnose_environment(env, ...)` requires the environment mapping although the collected API wiki text says `env=None`.

## [2026-07-27] query | dms-core를 DocumentStorage로 적용하는 방법
- Question:
  - dms-core를 DocMesh RAG Core의 document storage로 적용하는 방법
- Query filed:
  - queries/applying-dms-core-as-document-storage.md
- Navigation updated:
  - index.md
- Recommendation: use DMS as the original-document lifecycle boundary, keep RAG-specific chunk/progress/vector metadata in RAG Core, and connect both sides with the public `document_id` rather than exposing DMS `storage_key` as `storage_path`.
- Verification: 30 pages indexed; the new query page passed frontmatter, index, and wikilink checks.
- Pre-existing findings: 13 historical raw captures have body hash mismatches; immutable raw files were not modified.

## [2026-07-28] query | DMS 서비스 환경변수 접미사 분리 관리
- Question:
  - DMS용 PostgreSQL·SQLite·MinIO 환경변수를 특정 접미사로 분리 관리하는 방법
- Query filed:
  - queries/separating-dms-service-environment-variables-with-suffixes.md
- Navigation updated:
  - index.md
- Conclusion: current DMS/docmesh environment factories read fixed canonical process-environment keys; use deployment-time key translation for a separate process, or parse suffixed application settings and inject explicitly created clients/components when sharing one process.
- Verification: 31 pages indexed; the new query page passed frontmatter, index, and wikilink checks.
- Pre-existing findings: 13 historical raw captures have body hash mismatches; immutable raw files were not modified.

## [2026-07-28] update | DMS 서비스 환경변수 분리 규칙 정정
- User correction: 접미사 방식이 아니라 접두사 방식으로 분리 관리.
- Query page renamed:
  - queries/separating-dms-service-environment-variables-with-suffixes.md
  - queries/separating-dms-service-environment-variables-with-prefixes.md
- Naming examples updated:
  - `DMS_POSTGRES_HOST`
  - `DMS_SQLITE_PATH`
  - `DMS_MINIO_ENDPOINT`
- Navigation updated:
  - index.md
- Verification: 31 pages indexed; renamed page passed frontmatter, index, and wikilink checks; no suffix-named query file or suffix wording remains in the corrected page.
- Pre-existing findings: 13 historical raw captures have body hash mismatches; immutable raw files were not modified.

## [2026-07-28] update | DMS 접두사 환경변수 repository 적용
- Added `load_dms_settings()` with isolated `DMS_DOCMESH_*`, `DMS_POSTGRES_*`, `DMS_SQLITE_*`, and `DMS_MINIO_*` config models.
- Preserved canonical DMS control keys `DMS_METADATA_BACKEND` and `DMS_CONFIGURATION_STRICT` without a duplicated prefix.
- Split runtime assembly: Ollama/Milvus remain in the RAG service bundle; DMS receives a separately constructed `ServiceConfigs` instance.
- Avoided temporary or global `os.environ` mutation.
- Updated configuration surfaces:
  - `.env.example`
  - `README.md`
- Updated implementation and tests:
  - `rag_system_core/composition/docmesh_runtime.py`
  - `rag_system_core/composition/factories.py`
  - `test_rag_system_core/composition/test_docmesh_integration.py`
- Wiki pages updated:
  - `queries/separating-dms-service-environment-variables-with-prefixes.md`
  - `index.md`
- Verification: 32 composition tests and all 79 repository tests passed; compileall and `git diff --check` passed.

## [2026-07-28] query | docmesh-py-core 적용 최적화
- Synthesized the preferred adoption strategy: one composition entrypoint, selective config validation, process-scope client reuse, required/optional readiness, deterministic cleanup, and isolated DMS configuration/lifecycle.
- Filed: `queries/optimizing-docmesh-py-core-adoption.md`
- Navigation updated: `index.md` (32 pages indexed).
- Verification: the new query page passed required frontmatter, index presence, and wikilink checks.
- Pre-existing findings: 13 historical raw captures have body hash mismatches; immutable raw files were not modified.

## [2026-07-28] update | docmesh-py-core bootstrap 최적화 repository 적용
- Added public `bootstrap_rag_core_from_env(...)` context manager with startup checks and parallel Ollama/Milvus healthchecks enabled by default.
- Added context-manager lifecycle ownership to `DocmeshRAGServiceFactory` and exposed `parallel_healthchecks` through `from_env(...)`.
- Preserved DMS-first cleanup and RAG bundle rollback when DMS assembly fails.
- Updated implementation, tests, and public usage documentation:
  - `rag_system_core/composition/bootstrap.py`
  - `rag_system_core/composition/factories.py`
  - `rag_system_core/composition/__init__.py`
  - `rag_system_core/__init__.py`
  - `test_rag_system_core/composition/test_bootstrap.py`
  - `test_rag_system_core/composition/test_docmesh_integration.py`
  - `README.md`
  - `queries/optimizing-docmesh-py-core-adoption.md`
  - `index.md`
- Verification: installed v0.5.0 API signatures checked; 36 composition tests and all 83 repository tests passed; compileall and `git diff --check` passed; mypy remained at the same 15 pre-existing errors as `HEAD` with no new regression.
- Pre-existing findings: 13 historical raw captures have body hash mismatches; immutable raw files were not modified.
