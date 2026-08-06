# Software Requirements Specification (SRS)

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) defines the software requirements for the **DocMesh RAG Core Service v0.2.0 implementation baseline**. The document translates the product-level expectations in `docs/prd.md` into software requirements that can be implemented, verified, and maintained. The dependency contract baseline is `docmesh-py-core v0.5.0` and `dms-core v0.6.0`.

This SRS is intentionally implementation-aligned. When aspirational language conflicts with current behavior, this document prefers the behavior that is actually supported by the current codebase and reflected by the companion development documents.

### 1.2 Scope
DocMesh RAG Core Service is a Python RAG core library that ingests documents, stores metadata and vector representations, retrieves context under user scope constraints, and generates answers through model adapters.

At the software level, the system shall:

- expose a single primary public entry point centered on `RAGCore`
- support document ingestion from text, file streams, and file paths
- isolate stored data and retrieval results by authenticated user information
- persist metadata in SQLite and vector data in Milvus Lite
- support restart-time recovery by reopening the same metadata and vector storage
- support composition through helper factories and service-factory-based bootstrap paths
- provide an environment-based production bootstrap that assembles DocMesh and DMS resources and owns their lifecycle
- integrate with DocMesh configuration, assembled service bundles, dms-core document lifecycle, and aggregate health checks

This SRS covers the current library behavior. It does not define an external HTTP service contract or frontend behavior.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Meaning |
|---|---|
| SRS | Software Requirements Specification |
| PRD | Product Requirements Document |
| RAG | Retrieval-Augmented Generation |
| DocMesh | The surrounding configuration/runtime ecosystem referenced by this library |
| `RAGCore` | Primary public class for ingestion, retrieval, generation, and document management |
| user scope | The `AuthenticatedUser.sub` boundary used to isolate document storage and retrieval |
| resolved user identity | The `AuthenticatedUser.sub` value persisted and filtered as `user_id` |
| metadata store | SQLite-backed persistence for document, chunk, and ingestion progress records |
| vector store | Milvus Lite-backed storage for embeddings and similarity search |
| document asset storage | A port for original document content; the production implementation delegates to dms-core and stores an opaque `asset_reference` |
| restart recovery | Reopening the same metadata and vector-store configuration after process restart |
| health check | Aggregation of metadata and available Milvus, embedding, generation, and DMS checks |
| ingestion | Process of loading content, preprocessing, chunking, embedding, and storing it |

### 1.4 References

This document is derived from and aligned with the following repository documents:

- `docs/prd.md`
- `README.md`
- `pyproject.toml`

### 1.5 Overview
The remainder of this document is organized as follows:

- Section 2 describes the product context, users, assumptions, and constraints.
- Section 3 defines external interface requirements.
- Section 4 defines the system features and functional requirements.
- Section 5 defines nonfunctional requirements.
- Section 6 defines data requirements.
- Section 7 defines verification and traceability requirements.

---

## 2. Overall Description

### 2.1 Product Perspective
DocMesh RAG Core Service is a library component intended to be embedded inside a higher-level application or service. It is not itself an HTTP server or UI layer. The library coordinates seven major concerns:

1. ingestion of source content
2. metadata persistence
3. vector persistence and retrieval
4. generation of final answers
5. dms-core-backed source asset lifecycle
6. composition with helper factories and DocMesh runtime services
7. lifecycle and aggregate health management for environment-based production assembly

A simplified logical view is shown below.

```text
[Client/Application]
        |
        v
     [RAGCore]
   /     |      \
  v      v       v
Ingestion Retrieval Generation
   |        |        |
   v        v        v
Metadata  Vector   Model Clients
 Store    Store    (Embedding/Generation)
   |
   v
Document Storage

[Composition Layer]
 - DocmeshRAGServiceFactory.from_host_clients
 - DocmeshRAGServiceFactory
 - create_rag_embedding_client
 - create_rag_generation_client
 - create_rag_vector_store
 - docmesh_runtime: Ollama / Milvus settings and assembly
 - dms_runtime: DMS-prefixed settings adaptation

[Contract Layer]
 - types.py: public records
 - ports.py: dependency protocols
```

### 2.2 Product Functions
The system provides the following software functions:

- creation of a RAG core instance through direct construction or service-factory composition from explicit collaborators or host-owned clients
- ingestion of plain text, file streams, and file paths
- preprocessing and chunking of text content
- batch embedding generation for produced chunks
- storage of vectors through the standard Milvus adapter
- storage of document, chunk, and ingestion progress metadata in SQLite
- storage and soft deletion of source assets through dms-core in the production composition path
- user-scoped retrieval of relevant chunks
- prompt assembly and answer generation through a generation client
- listing, reading, and deleting user-scoped documents and document chunks
- health checking across metadata and available dependent services
- deterministic cleanup of owned DMS SDK and DocMesh `ServiceBundle` resources

### 2.3 User Classes and Characteristics

| User class | Description | Key expectation |
|---|---|---|
| Local consumer | Local or single-instance user ingesting and querying documents | Explicit user information and predictable behavior |
| Multi-user integrator | Application/service integrating this library for multiple users | Strict user-scope isolation |
| DocMesh-integrated developer | Developer using DocMesh settings, service-bundle assembly, and health integrations | Stable composition and reuse of runtime services |

### 2.4 Operating Environment
The software is expected to run in a Python environment with:

- Python `>= 3.11`
- `docmesh-py-core`
- `dms-core` (Python package name `dms`)
- `pydantic-settings`
- `pymilvus[milvus-lite]`
- Python package `ollama`, imported by the provided Ollama adapters

The runtime environment shall provide:

- writable directories for SQLite and for Milvus files when local file URIs are configured
- reachable MinIO-compatible object storage and a valid DMS metadata backend for the production environment bootstrap
- accessible embedding and generation model runtime(s)
- valid DocMesh settings when DocMesh-integrated paths are used

### 2.5 Design and Implementation Constraints
The current implementation imposes the following constraints:

- the standard composition factory creates `MilvusLiteVectorStore`, while the actual local or remote connection follows the Milvus client/configuration
- the standard composition factory provides SQLite metadata persistence through SQLAlchemy ORM
- file ingestion assumes UTF-8-decodable text inputs
- `RAGCore` is a dependency-injected assembly point, not a convenience constructor over paths/settings alone
- user-scoped methods require `docmesh_py_core.AuthenticatedUser`
- the system does not provide distributed transaction guarantees across vector, metadata, and asset storage
- service factories are assembled from caller-provided settings, service bundles, or clients; no path-only convenience constructor is provided

### 2.6 User Documentation
The primary companion development documents are:

- `README.md`
- `docs/prd.md`

### 2.7 Assumptions and Dependencies
The following assumptions and dependencies apply:

- embedding and generation clients satisfy their documented protocol contracts
- embedding/vector-store adapters are expected to preserve chunk/vector cardinality; the standard Milvus adapter rejects mismatched input counts
- the configured Milvus storage is reachable and reusable across restarts when configured consistently
- the calling application's composition layer is responsible for reaching Ollama, Milvus, DMS metadata, and MinIO using its selected configuration path
- authentication and `AuthenticatedUser` creation are owned by the calling application

---

## 3. External Interface Requirements

### 3.1 User Interfaces
No graphical user interface is defined by this SRS.

### 3.2 Hardware Interfaces
No special hardware interface is defined by this SRS.

### 3.3 Software Interfaces

#### 3.3.1 Public Construction Interfaces
The system shall expose the following public construction paths:

- `RAGCore(...)`
- `DocmeshRAGServiceFactory.from_host_clients(...)`

`DocmeshRAGServiceFactory.from_host_clients(...)` shall accept host-created SQLAlchemy `Engine`, MinIO client, Ollama client, Milvus client, model names, vector collection/timeout, and the DMS bucket name. It shall return a context-managed Factory that assembles the RAG adapters without loading DocMesh or DMS environment configuration. The transport clients shall remain caller-owned, and `create_rag_core(...)` shall assemble the final core. `DocmeshRAGServiceFactory.from_clients(...)` shall accept an explicitly created DMS SDK and explicit embedding, generation, and vector collaborators; it shall not store `ServiceConfigs` or `ServiceBundle` instances or lazily create collaborators from them.

#### 3.3.2 Public Operational Interfaces
The system shall expose the following public operational interfaces:

- `ingest_text(...)`
- `ingest_file_stream(...)`
- `ingest_file_path(...)`
- `query(...)`
- `list_documents(...)`
- `get_document(...)`
- `list_document_chunks(...)`
- `list_ingestion_progress(...)`
- `delete_document(...)`
- `health_check()`

#### 3.3.3 Public Data Types
The package root `rag_system_core` shall expose `AuthenticatedUser` and the following public record types:

- `DocumentRecord`
- `ChunkRecord`
- `IngestResult`
- `IngestionProgressRecord`
- `QueryResult`

#### 3.3.4 Client Protocol Interfaces
The package root `rag_system_core` shall expose the following protocol contracts, canonically owned by `rag_system_core.ports`:

- `EmbeddingClient.embed(texts: list[str]) -> list[list[float]]`
- `GenerationClient.generate(prompt: str) -> str`

#### 3.3.5 Composition Interfaces
The system shall distinguish composition interfaces by canonical import path:

| Surface | Canonical interfaces |
|---|---|
| Package root `rag_system_core` | `RAGCore`, `RAGServiceFactory`, `DocmeshRAGServiceFactory`, `OllamaEmbeddingClient`, `OllamaGenerationClient`, public records, client protocols, and `AuthenticatedUser` |
| `rag_system_core.composition` | `assemble_docmesh_services`, `load_docmesh_settings`, `create_docmesh_service_client`, `create_dms_sdk_from_clients`, `resolve_milvus_runtime_settings`, `run_health_checks`, and the two service-factory types |
| Advanced factory module `rag_system_core.composition.factories` | `create_rag_embedding_client`, `create_rag_generation_client`, `create_rag_vector_store` |

Module-qualified advanced helpers shall not be described as package-root exports.

#### 3.3.6 External Runtime Integrations
The system may integrate with the following external software services or packages:

- DocMesh settings and assembled `ServiceBundle` clients
- `docmesh_py_core.AuthenticatedUser` as the user information model
- Ollama-compatible embedding and generation adapters
- Milvus storage through an injected or DocMesh-assembled client
- SQLite metadata storage
- dms-core SDK with MinIO-compatible object storage and SQLite or PostgreSQL DMS metadata

### 3.4 Communications Interfaces
This SRS defines no standalone network protocol for the product itself. Any network communication occurs indirectly through configured client adapters.

---

## 4. System Features and Functional Requirements

### 4.1 Feature: User Identification and Scope Resolution

#### 4.1.1 Description and Priority
This feature resolves the current user identity and enforces user-scope isolation across ingestion, retrieval, listing, and deletion.

**Priority:** High

#### 4.1.2 Stimulus/Response Sequences
- When a caller invokes a user-scoped method, it provides an `AuthenticatedUser`.
- The system uses `AuthenticatedUser.sub` as `user_id`.
- When a user performs retrieval or management operations, the system limits results to that `user_id`.

#### 4.1.3 Functional Requirements

`SRS-FR-004`–`007` are retired identifiers from the pre-v0.2.0 user-resolution contract and shall not be reused.

- **SRS-FR-001** The system shall accept `docmesh_py_core.AuthenticatedUser` for user-scoped operations.
- **SRS-FR-002** User information shall be required for ingestion, retrieval, listing, progress lookup, and deletion.
- **SRS-FR-003** The system shall use `AuthenticatedUser.sub` as `user_id`.
- **SRS-FR-008** The system shall attach `user_id` to persisted document metadata.
- **SRS-FR-009** The system shall attach `user_id` to persisted chunk metadata.
- **SRS-FR-010** The system shall restrict query results to chunks belonging to the resolved `user_id`.
- **SRS-FR-011** The system shall restrict document retrieval, chunk retrieval, progress retrieval, and deletion to the resolved `user_id`.

### 4.2 Feature: Document Ingestion

#### 4.2.1 Description and Priority
This feature accepts source content, normalizes it into text, processes it into chunks, generates embeddings, and stores the resulting artifacts.

**Priority:** High

#### 4.2.2 Stimulus/Response Sequences
- A caller submits text, a file stream, or a file path.
- Before tracked progress begins, the system reads/decodes content as required by the selected API path, uploads the DMS asset, and creates document metadata when entering finalization.
- The system preprocesses the text.
- The system chunks the text.
- The system requests embeddings in batch.
- The system stores vectors, chunk metadata, and progress records after the earlier document-metadata creation.

#### 4.2.3 Functional Requirements

- **SRS-FR-012** The system shall provide `ingest_text(...)` for plain-text ingestion.
- **SRS-FR-013** The system shall provide `ingest_file_stream(...)` for file-stream ingestion.
- **SRS-FR-014** The system shall provide `ingest_file_path(...)` for file-path ingestion.
- **SRS-FR-015** `ingest_file_stream(...)` shall fail when `source` is missing or blank.
- **SRS-FR-016** The system shall preprocess input text using the current implementation-level normalization behavior.
- **SRS-FR-017** The current preprocessing behavior shall be equivalent to `strip()`-level trimming.
- **SRS-FR-018** The system shall reject empty text after preprocessing.
- **SRS-FR-019** The standard factory-provided chunker shall use a fixed-length window with overlap, require `chunk_size > 0`, require `chunk_overlap >= 0`, and require `chunk_overlap < chunk_size`. Directly assembled `RAGCore` instances may provide another `Chunker` implementation.
- **SRS-FR-020** After the API-specific source/DMS/document operations, the system shall record tracked ingestion stages in the following order: `load`, `preprocess`, `chunking`, `embedding`, `vector_store`, `chunk_persistence`. The tracked `load` stage shall not be interpreted as ownership of the preceding source read or DMS upload.
- **SRS-FR-021** The system shall create a `job_id` for each ingestion execution.
- **SRS-FR-022** The system shall record ingestion progress using statuses that can represent `running`, `completed`, and `failed`. It shall compensate vector insertion when generated ID count mismatches, chunk metadata persistence fails, or `vector_store=completed` progress persistence fails. If `chunk_persistence=completed` progress persistence fails, it shall attempt both metadata-chunk and vector cleanup. A compensation failure shall not prevent remaining compensations or replace the original pipeline error.
- **SRS-FR-023** The system shall limit ingestion progress queries by document and resolved user scope.

### 4.3 Feature: Document Asset Storage

#### 4.3.1 Description and Priority
This feature persists or references source document assets separately from metadata rows.

**Priority:** Medium

#### 4.3.2 Functional Requirements

- **SRS-FR-024** The production `DocmeshRAGServiceFactory` path shall provide `DmsDocumentStorage` backed by a dms-core SDK.
- **SRS-FR-025** DMS upload requests shall use the RAG `doc_id` as the public DMS `document_id`, and the returned identifier shall be persisted as opaque `asset_reference`.
- **SRS-FR-026** The system shall not store full document body content directly in the document metadata row.
- **SRS-FR-027** The public document record shall track the asset through `asset_reference`; the SQLite schema may retain the physical column name `storage_path` for compatibility.
- **SRS-FR-028** DMS uploads shall include `user_id` and `source` metadata, set `created_by` and idempotency scope to `user_id`, and use the ingestion `job_id` as idempotency key.
- **SRS-FR-029** DMS deletion shall use soft delete by `asset_reference`; an already missing or already deleted DMS document shall be treated as an idempotent completion.
- **SRS-FR-078** `ingest_text(...)` shall store stripped text, file-stream ingestion shall store the consumed byte payload, and file-path ingestion shall upload the source file content at upload time. DMS asset load shall decode UTF-8 content and return `None` when the asset is missing or already deleted.

### 4.4 Feature: Embedding and Generation

#### 4.4.1 Description and Priority
This feature transforms chunks into embeddings and transforms retrieved context into a final answer.

**Priority:** High

#### 4.4.2 Functional Requirements

- **SRS-FR-030** The system shall support embedding batch invocation.
- **SRS-FR-031** During ingestion, the system shall process all produced chunks through a single `embed(chunks)` batch call.
- **SRS-FR-032** Embedding/vector-store adapters shall preserve chunk/vector cardinality. The standard Milvus adapter shall reject mismatched chunk/vector input counts; directly injected adapters are responsible for honoring the same contract.
- **SRS-FR-033** The system shall pass a single completed prompt string to the generation client.
- **SRS-FR-034** The generation client shall return the final answer as a string.
- **SRS-FR-035** The prompt built for generation shall contain a `[System Prompt]` section.
- **SRS-FR-036** The prompt built for generation shall contain a `[Retrieved Context]` section.
- **SRS-FR-037** The prompt built for generation shall contain a `[User Query]` section.
- **SRS-FR-077** The provided Ollama adapters shall reject blank model names, wrap transport failures as `RuntimeError`, and reject malformed embedding or generation responses.

### 4.5 Feature: Retrieval and Vector Storage

#### 4.5.1 Description and Priority
This feature stores embeddings, retrieves relevant chunks, and applies user-scope filtering.

**Priority:** High

#### 4.5.2 Functional Requirements

- **SRS-FR-038** The standard `DocmeshRAGServiceFactory` vector store implementation shall be `MilvusLiteVectorStore`; its actual local or remote connection shall follow the injected or DocMesh-assembled Milvus client/configuration, and directly assembled cores may inject another `VectorStore` implementation.
- **SRS-FR-039** If the target collection does not exist, the system shall create it at first insert using the embedding dimension.
- **SRS-FR-040** Retrieval operations shall enforce a `user_id` filter.
- **SRS-FR-041** The system shall read configured Milvus collection and timeout values from DocMesh settings when available.
- **SRS-FR-042** The composition layer shall use an explicitly injected Milvus client or assemble one through DocMesh settings / `ServiceBundle`; if no client can be created, it shall raise `RuntimeError`. An explicit client replaces client construction only: when `settings` and `bundle` are both absent, the factory shall still load Milvus DocMesh settings to resolve collection and timeout.
- **SRS-FR-043** If neither an explicit collection override nor a configured collection is available, the system shall use `rag_chunks`.
- **SRS-FR-044** If neither an explicit timeout override nor a configured timeout is available, the system shall use `30.0`.

### 4.6 Feature: Metadata Persistence and Restart Recovery

#### 4.6.1 Description and Priority
This feature preserves structured records across process restarts and supports reopening the same vector and metadata stores.

**Priority:** High

#### 4.6.2 Functional Requirements

- **SRS-FR-045** The standard `DocmeshRAGServiceFactory` shall provide a SQLite metadata persistence backend; directly assembled cores may inject another `MetadataRepository` implementation.
- **SRS-FR-046** The standard SQLite metadata implementation shall use SQLAlchemy ORM.
- **SRS-FR-047** The system shall maintain a `documents` table.
- **SRS-FR-048** The system shall maintain a `chunks` table.
- **SRS-FR-049** The system shall maintain an `ingestion_progress` table.
- **SRS-FR-050** The system shall preserve metadata across process restarts.
- **SRS-FR-051** The system shall support retrieval recovery by reopening the same Milvus storage and collection.
- **SRS-FR-052** The SQLite metadata store shall not be responsible for regenerating embedding vectors.

### 4.7 Feature: Document Management and Deletion

#### 4.7.1 Description and Priority
This feature allows callers to inspect and remove previously ingested documents within the current user scope.

**Priority:** High

#### 4.7.2 Functional Requirements

- **SRS-FR-053** The system shall provide document listing within the current user scope.
- **SRS-FR-054** The system shall provide single-document retrieval within the current user scope.
- **SRS-FR-055** The system shall provide chunk listing for a document within the current user scope.
- **SRS-FR-056** The system shall provide ingestion progress listing for a document within the current user scope.
- **SRS-FR-057** On successful document deletion, the system shall remove document metadata.
- **SRS-FR-058** On successful document deletion, the system shall remove chunk metadata.
- **SRS-FR-059** On successful document deletion, the system shall remove ingestion progress metadata.
- **SRS-FR-060** On successful document deletion, the system shall invoke the configured asset-storage deletion. The production DMS adapter shall soft-delete the asset or complete idempotently when it is already absent/deleted.
- **SRS-FR-061** On successful document deletion, the system shall remove Milvus entries.
- **SRS-FR-062** If vector store deletion fails, the system shall not proceed with metadata or asset deletion.
- **SRS-FR-063** If vector deletion or DMS soft deletion fails, the system shall preserve RAG metadata and permit retry. Because vector deletion occurs first, DMS failure may leave vectors already removed; the retry path shall tolerate that state.

### 4.8 Feature: Health Check and Composition / DocMesh Integration

#### 4.8.1 Description and Priority
This feature reports operational status and supports composition with helper factories and the surrounding DocMesh runtime.

**Priority:** Medium

#### 4.8.2 Functional Requirements

- **SRS-FR-064** The system shall include metadata health checking in every health-check result.
- **SRS-FR-065** When the vector store provides `check()`, the system shall include vector-store health information.
- **SRS-FR-066** When the embedding client provides `check()`, the system shall include embedding-client health information.
- **SRS-FR-067** When the generation client provides `check()`, the system shall include generation-client health information.
- **SRS-FR-068** The system shall aggregate health checks through `docmesh_py_core.check_all_services()`.
- **SRS-FR-069** Errors from the aggregate health boundary shall propagate to the caller; the package defines no separate local result model.
- **SRS-FR-070** The system shall support settings loading through `docmesh_py_core.load_available_service_configs()`.
- **SRS-FR-071** The system shall support service assembly through `docmesh_py_core.assemble_services()` and `ServiceBundle` for standalone adapter construction, while `DocmeshRAGServiceFactory` shall consume only explicitly supplied DMS and RAG collaborators.
- **SRS-FR-073** When document asset storage provides `check()`, the system shall include DMS health information.
- **SRS-FR-075** DMS configuration shall be read from the current process environment using `DMS_METADATA_BACKEND`, `DMS_DOCMESH_*`, `DMS_SQLITE_*` or `DMS_POSTGRES_*`, and `DMS_MINIO_*` namespaces without reusing unprefixed shared-service values.
- **SRS-FR-079** The system shall provide a client-based bootstrap that accepts caller-created SQLAlchemy `Engine`, MinIO client, Ollama client, Milvus client, embedding/generation model names, and vector collection/timeout, passes the DMS inputs to dms-core's client assembly path, and assembles the RAG adapters without loading DMS or DocMesh environment configuration. The helper shall close only the created DMS SDK while leaving every transport client caller-owned.

---

## 5. Nonfunctional Requirements

### 5.1 Performance Requirements

- **SRS-NFR-001** Ingestion shall use batch embedding calls rather than one embedding call per chunk.
- **SRS-NFR-002** Retrieval shall use a top-k-based flow that remains simple and predictable.
- **SRS-NFR-003** Health-check execution shall synchronously aggregate metadata and available dependency checks through the configured runner; this package shall not claim a separate end-to-end health deadline beyond client-level timeout configuration.

### 5.2 Scalability and Extensibility Requirements

- **SRS-NFR-004** The system shall preserve a single primary public entry point while keeping internal responsibilities separated.
- **SRS-NFR-005** The system shall permit alternate chunker, vector-store, metadata, asset-storage, embedding, generation, and health-runner implementations through ports and `RAGServiceFactory` without changing the `RAGCore` operational method surface.

### 5.3 Data Isolation Requirements

- **SRS-NFR-006** The system shall prevent cross-user mixing of stored data and retrieval results.
- **SRS-NFR-007** User-scope isolation shall be preserved during storage, retrieval, listing, and deletion.

### 5.4 Reliability Requirements

- **SRS-NFR-008** Metadata persistence shall survive process restarts.
- **SRS-NFR-009** Retrieval shall remain recoverable when the same Milvus configuration is reused after restart.
- **SRS-NFR-010** On deletion failures, the system shall minimize metadata loss caused by partial cleanup.

### 5.5 Maintainability Requirements

- **SRS-NFR-011** The public API shall remain centered on `RAGCore`.
- **SRS-NFR-012** Public records shall be owned by `rag_system_core.types`, and dependency protocols shall have `rag_system_core.ports` as their canonical owner.
- **SRS-NFR-013** Composition/integration code and domain logic shall remain separable; DMS environment adaptation and RAG DocMesh runtime assembly shall have separate module owners.

### 5.6 Portability Requirements

- **SRS-NFR-014** The software shall operate in a Python 3.11-or-higher environment that satisfies the declared package dependencies.

### 5.7 Operational Requirements

- **SRS-NFR-015** Resource lifecycle ownership shall remain explicit: caller-supplied factories and transport clients are caller-owned, while the client bootstrap helper's created DMS SDK is context-owned.
- **SRS-NFR-016** RAG and DMS environment namespaces shall remain independently configurable within one process.

---

## 6. Data Requirements

### 6.1 Logical Data Model

#### 6.1.1 Document Record
The system shall maintain document records with at least the following fields:

```json
{
  "doc_id": "string",
  "user_id": "string",
  "source": "string",
  "created_at": "ISO-8601 string",
  "asset_reference": "string | null"
}
```

The SQLite `documents` table currently maps the public `asset_reference` field to the physical compatibility column named `storage_path`.

#### 6.1.2 Chunks Table Shape
The system shall maintain chunk data with at least the following logical fields:

```text
chunk_id (PK, Milvus auto-id mirrored to metadata DB)
doc_id (FK -> documents.doc_id)
user_id
chunk_index
content
metadata_json
```

#### 6.1.3 Ingestion Progress Table Shape
The system shall maintain ingestion progress data with at least the following logical fields:

```text
progress_id (PK)
job_id
doc_id (FK -> documents.doc_id)
user_id
source
step_name
step_order
status
created_at
```

### 6.2 Data Integrity Requirements

- **SRS-DR-001** Each document shall have a unique `doc_id`.
- **SRS-DR-002** Each chunk shall be associated with a document and a `user_id`.
- **SRS-DR-003** Each ingestion progress record shall be traceable by `job_id`, `doc_id`, `user_id`, `step_name`, and `status`.
- **SRS-DR-004** Chunk metadata shall be persistable as `metadata_json`.

### 6.3 Data Retention Characteristics

- **SRS-DR-005** SQLite-backed metadata shall persist across process restarts.
- **SRS-DR-006** Production document assets and their retention policy shall be owned by dms-core; RAG metadata shall retain only the opaque `asset_reference` needed to address that lifecycle.
- **SRS-DR-007** A DMS upload result whose `document_id` differs from the requested RAG `doc_id` shall be rejected as a contract violation.

---

## 7. Verification and Traceability

### 7.1 Acceptance Criteria
The implementation shall be considered conformant to this SRS when the following conditions are met:

1. User-scoped methods require an `AuthenticatedUser`.
2. `AuthenticatedUser.sub` becomes the persisted and filtered user scope.
3. Text, file stream, and file path ingestion paths all function as defined.
4. `ingest_file_stream()` fails when `source` is absent.
5. After source/DMS/document side effects, ingestion progress records reflect the required tracked pipeline order.
6. Chunk embedding occurs through a single batch call per ingestion execution.
7. Query results are restricted to the current user scope.
8. Generated prompts contain `[System Prompt]`, `[Retrieved Context]`, and `[User Query]`.
9. Metadata is stored in SQLite.
10. Retrieval remains possible after restart when the same Milvus configuration is reused.
11. Chunk listings and ingestion progress listings are available per document.
12. Successful deletion removes document metadata, chunk metadata, progress metadata, and Milvus entries and invokes asset deletion; the production DMS adapter uses soft delete.
13. Failed vector-store deletion preserves metadata for retry.
14. Health checking aggregates metadata and available dependency checks.
15. `DocmeshRAGServiceFactory.from_host_clients(...)` assembles embedding/generation/vector adapters from explicitly supplied Ollama/Milvus clients and settings without loading environment configuration, and closes only its created DMS SDK and MetadataStore.
16. DMS uploads preserve the RAG document identifier, user metadata, and ingestion idempotency information.
17. DMS soft-delete failure preserves RAG metadata for retry.

### 7.2 Traceability Source
Automated verification for these requirements is maintained under `test_rag_system_core/`.

### 7.3 Verification Approach
Verification of this SRS is performed primarily through:

- automated pytest scenarios under `test_rag_system_core/`
- code-level inspection of public exports and composition helpers
- document synchronization across `README.md`, `docs/prd.md`, and `docs/srs.md`

### 7.4 Requirements-to-Test Traceability

| Requirement range | Verification status | Primary evidence |
|---|---|---|
| `SRS-FR-001`–`011` | Verified | `test_rag_system_core/domain/test_ingestion_api.py`, `test_rag_system_core/domain/test_query.py`, `test_rag_system_core/domain/test_metadata_and_progress.py` |
| `SRS-NFR-006`–`007` | Partially verified | Query/get/progress isolation is automated; negative cross-user deletion and chunk-listing scenarios are not directly covered. |
| `SRS-FR-012`–`023`, `SRS-NFR-001` | Verified | `test_rag_system_core/domain/test_ingestion_api.py`, `test_rag_system_core/domain/test_metadata_and_progress.py`, `test_rag_system_core/domain/test_deletion_and_rollback.py` |
| `SRS-FR-024`–`029`, `SRS-FR-078`, `SRS-DR-006`–`007` | Verified | `test_rag_system_core/storage/test_dms_document_storage.py`, `test_rag_system_core/domain/test_ingestion_api.py` |
| `SRS-FR-030`–`031`, `033`–`037`, `SRS-FR-077` | Verified | `test_rag_system_core/adapters/`, `test_rag_system_core/domain/test_query.py`, `test_rag_system_core/domain/test_deletion_and_rollback.py` |
| `SRS-FR-032` | Partially verified | Standard-adapter validation exists in `rag_system_core/storage/vector_store.py`; there is no direct automated chunk/vector input-count mismatch test. |
| `SRS-FR-038`–`044`, `SRS-FR-070`–`071` | Verified | `test_rag_system_core/composition/test_core_configuration.py`, `test_rag_system_core/composition/test_docmesh_integration.py` |
| `SRS-FR-045`–`052`, `SRS-DR-001`–`005` | Verified | `test_rag_system_core/domain/test_metadata_and_progress.py` |
| `SRS-FR-053`–`062` | Verified | `test_rag_system_core/domain/test_deletion_and_rollback.py`, `test_rag_system_core/domain/test_metadata_and_progress.py` |
| `SRS-FR-063` | Partially verified | Vector retry and DMS-failure metadata preservation are automated; a second successful delete attempt after DMS failure is not directly covered. |
| `SRS-FR-064`–`069`, `SRS-FR-073` | Verified | `test_rag_system_core/composition/test_docmesh_integration.py`, `test_rag_system_core/storage/test_dms_document_storage.py` |
| `SRS-FR-079`, `SRS-NFR-013`, `015`–`016` | Verified | `test_rag_system_core/composition/test_bootstrap.py`, `test_rag_system_core/composition/test_docmesh_integration.py`, `test_rag_system_core/composition/test_runtime_boundaries.py` |

---

## 8. Constraints and Risks Summary

- The standard factory creates a Milvus adapter, but the actual local or remote deployment is owned by the supplied Milvus client/configuration.
- File ingestion assumes UTF-8 text inputs.
- `RAGCore` requires assembled dependencies rather than path-only convenience construction.
- The calling application must authenticate users and construct `AuthenticatedUser` instances.
- Deletion executes vector → asset → metadata. A DMS failure can leave vectors deleted and metadata retained; a metadata failure can occur after vector and asset cleanup. No distributed rollback is provided.
- Ingestion uploads the asset and creates document metadata before vector/chunk completion; a later failure can therefore leave retryable document/DMS state rather than performing a full distributed rollback.
- Directly assembled factories and transport clients remain caller-owned; client bootstrap callers use the helper context manager for its created DMS SDK only.

---

## 9. Summary

The current implementation of DocMesh RAG Core Service is a **composition-oriented Python RAG library** centered on `RAGCore`. Its software requirements emphasize user-scope isolation, SQLite + Milvus Lite search persistence, dms-core document lifecycle, predictable ingestion and retrieval flow, and explicit caller-owned composition with clear resource ownership. This SRS documents only behavior that is presently supported by code and companion tests.
