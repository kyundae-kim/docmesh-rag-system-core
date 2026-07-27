---
title: Applying dms-core as Document Storage
created: 2026-07-27
updated: 2026-07-27
type: query
tags: [architecture, integration, sdk, persistence, decision]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/docmesh-rag-core-api-reference-2026-06-23.md, raw/articles/docmesh-rag-core-prd-2026-06-23.md, raw/articles/docmesh-rag-core-srs-2026-06-23.md]
confidence: medium
---

# Applying dms-core as Document Storage

## 질문

`dms-core`를 DocMesh RAG Core의 `DocumentStorage`로 어떻게 적용해야 하는가?

## 결론

권장 방식은 `dms-core`를 단순 MinIO client로 축소하지 않고 **원문 자산의 저장·조회·삭제·무결성·복구를 소유하는 document-management 경계**로 적용하는 것이다. RAG Core의 `MetadataStore`는 청크, ingestion progress, 검색 및 user-scope 관계처럼 RAG 고유 상태만 유지한다. 두 경계는 동일한 `document_id`로 연결한다.

기존 `DocumentStorage`가 로컬 `storage_path`를 반환한다면 DMS adapter에서 내부 `storage_key`를 노출하지 말아야 한다. 대신 공개 `document_id`를 opaque asset reference로 사용하도록 계약을 바꾸거나 별도 `DmsDocumentStorage` port를 둔다. `dms-core`의 `DocumentMetadata.storage_key`와 internal 조회는 관리·복구 경계에만 남겨야 한다.^[raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md]

## 책임 분리

| 책임 | 권장 소유자 |
| --- | --- |
| 원문 bytes/stream 저장과 다운로드 | `dms-core` |
| 원문 checksum, 크기 제한, content type | `dms-core` |
| 원문 soft/hard delete와 복구 검사 | `dms-core` |
| DMS 문서 상태와 object `storage_key` | `dms-core` 내부 |
| RAG document와 DMS document 연결 | RAG `MetadataStore`의 `dms_document_id` 또는 동일 `document_id` |
| chunk, embedding/vector ID, ingestion progress | RAG Core |
| user scope와 검색 필터 | RAG Core |
| API/MCP 오류 변환 | 전송 adapter; 필요하면 `recommended_http_error()` 사용 |

이 분리는 [[rag-service-architecture]]의 원문 자산과 RAG metadata 분리를 유지하면서 [[dms-metadata-and-recovery]]의 관리 경계를 보존한다. DMS metadata store를 RAG의 `documents`, `chunks`, `ingestion_progress` 전체 저장소로 재사용하려 하면 두 SDK의 상태 모델과 삭제 의미가 결합되므로 초기 적용 범위를 넘는다.

## 조립 위치

DMS SDK는 `composition` 계층에서 애플리케이션 수명주기당 한 번 조립하고 adapter에 주입한다. 요청이나 ingestion 호출마다 SDK를 만들고 닫지 않는다.

1. 이미 `docmesh_py_core.ServiceConfigs`를 조립하는 bootstrap이 있으면 `create_sdk_from_service_configs(configs, check_on_startup=True)`를 우선한다.
2. 독립 실행 애플리케이션이면 `diagnose_environment(dict(os.environ))` 후 `create_sdk_from_environment()`를 사용한다.
3. 기존 SQLAlchemy Engine과 MinIO client를 공유해야 할 때만 `create_sdk_from_clients(...)`를 사용하고 자원 종료 주체를 명시한다.
4. 테스트에서는 fake metadata/object adapter와 `create_sdk_from_components(...)`를 사용한다.

환경·설정 factory가 만든 client는 DMS SDK가 소유한다. client/component factory에 주입한 자원은 기본적으로 호출자 소유다. 이 원칙은 [[dms-configuration-and-assembly]]와 [[construction-paths-and-adapter-contracts]]의 composition 책임에 맞춰 bootstrap 종료 시 `close()` 또는 `aclose()`로 연결한다.^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]

## Adapter 계약

`DmsDocumentStorage`는 package-root 공개 API만 사용하며 다음 의미를 제공해야 한다.

- `save`: `UploadDocumentRequest` 또는 stream request를 만들고 `sdk.upload_document*()`를 호출한다.
- `read`: 작은 본문은 `get_document_content()`, 큰 본문은 context manager 기반 `get_document_content_stream()`을 사용한다.
- `delete`: 사용자 요청은 기본적으로 `soft_delete_document()`에 매핑한다. `hard_delete_document()`는 관리자·보존정책 경계로 제한한다.
- `exists`/metadata 조회: `get_document_metadata()`를 사용하고 `DocumentNotFoundError`와 `DocumentDeletedError`를 port 수준 결과로 변환한다.
- `health`: `sdk.check_health()`를 전체 service readiness에 합친다.
- `close`: adapter 또는 bootstrap이 SDK 소유권에 따라 정확히 한 lifecycle을 제공한다. 반복 종료는 안전하지만 소유권은 모호하면 안 된다.

Adapter 반환값은 로컬 path가 아니라 최소 `document_id`, checksum, size, content type을 포함하는 공개-safe 참조여야 한다. 내부 `storage_key`를 기존 `storage_path` 필드에 복사하는 구현은 피한다.

## Ingestion 흐름

권장 순서는 다음과 같다.

1. token에서 `user_id`를 해석한다.
2. 애플리케이션 `document_id`를 먼저 확정한다.
3. DMS에 원문을 업로드한다. 재시도 가능한 요청이면 `idempotency_scope=user_id`, `idempotency_key=job_id` 또는 안정적인 요청 ID를 사용한다.
4. DMS public metadata와 동일 `document_id`를 RAG document record에 연결한다.
5. 원문을 preprocess, chunk, embed하고 vector store와 chunk metadata에 적재한다.
6. 모든 단계가 끝나면 ingestion progress를 `completed`로 기록한다.
7. 중간 실패는 `failed` progress와 보상 작업을 기록한다. DMS 업로드 후 실패했다면 즉시 hard delete로 숨기기보다 soft delete 또는 명시적 cleanup/recovery job으로 처리한다.

처리 과정이 업로드 원본 stream을 계속 필요로 하면 stream 소유권을 지켜야 한다. DMS는 입력 stream을 닫지 않으며, DMS가 반환한 다운로드 stream은 호출자가 닫아야 한다. 이 흐름은 [[ingestion-pipeline]]과 [[dms-document-lifecycle]]을 결합한 saga이며 SQL/MinIO/vector store를 하나의 ACID transaction으로 가정해서는 안 된다.

## User scope

`dms-core`의 공개 계약은 `user_id` 기반 접근제어를 자동 제공한다고 보장하지 않는다. 따라서 DMS 호출 전에 RAG metadata에서 `document_id`와 현재 `user_id`의 소유 관계를 검증해야 한다. 업로드 시 DMS `extra_metadata`에 `user_id`, `source`, schema version을 넣을 수 있지만, 이것만으로 인가를 대체하지 않는다.

목록 API도 DMS 전체 목록을 사용자에게 직접 노출하지 않는다. 사용자별 문서 목록은 RAG `MetadataStore`에서 조회하고, 각 항목의 DMS public metadata가 필요할 때 결합한다. 이는 [[user-scope-isolation]]의 저장·조회·삭제 전 구간 격리 계약을 유지한다.

## 삭제와 장애 복구

기존 RAG 계약은 vector 삭제 실패 시 metadata와 원문을 보존한다. DMS 적용 후에도 다음 순서가 안전하다.

1. RAG document를 논리적 `deleting` 상태로 전환한다.
2. vector entry를 먼저 삭제한다. 실패하면 DMS와 RAG metadata를 보존하고 재시도한다.
3. DMS 원문을 soft delete한다.
4. chunk와 progress metadata를 정책에 따라 정리하거나 감사용 tombstone을 남긴다.
5. hard delete는 retention 만료 또는 관리자 작업으로 분리한다.

단계 2 이후 단계 3이 실패할 수 있으므로 삭제 작업은 멱등적인 재시도 상태를 가져야 한다. DMS의 `inspect_document()`, `list_recovery_candidates()`, dry-run reconciliation plan은 DMS metadata/object 불일치 복구에 사용하되, vector/RAG metadata 불일치는 별도 애플리케이션 reconciliation이 담당한다. 자세한 기존 요구는 [[persistence-and-restart-recovery]]를 따른다.

## 설정 기준

로컬 첫 적용은 `DMS_METADATA_BACKEND=sqlite`, writable `SQLITE_PATH`, MinIO 네 필수값으로 시작할 수 있다. SQLite는 DMS metadata만 대체하며 MinIO는 여전히 필수다. 운영에서는 PostgreSQL을 명시하고 `DMS_CONFIGURATION_STRICT=true`, startup healthcheck, `MINIO_SECURE=true`, `MINIO_CERT_CHECK=true`를 권장한다.^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]

## 구현 순서

1. 현재 `DocumentStorage` protocol과 `storage_path` 사용처를 조사해 DMS의 opaque `document_id`와 충돌하는 지점을 식별한다.
2. DMS SDK를 소유하는 composition provider와 종료 경로를 추가한다.
3. `DmsDocumentStorage` adapter의 save/read/delete/health/error mapping contract test를 먼저 작성한다.
4. ingestion에서 동일 `document_id`, idempotency scope/key, 실패 보상을 연결한다.
5. get/list/delete에서 user-scope 검사를 강제한다.
6. vector → DMS → metadata 삭제 순서와 재시도 상태를 검증한다.
7. fake component test 후 SQLite+MinIO smoke test, 재시작 복원, 전체 소비 프로젝트 회귀 test를 수행한다.

## 적용 판단

DMS를 적용할 때 가장 먼저 바꿔야 하는 것은 storage 구현체보다 **저장 참조 계약**이다. `storage_path`를 외부 계약으로 유지한 채 DMS를 끼우면 internal `storage_key` 노출이나 중복 metadata가 생긴다. `document_id`를 자산 참조로 승격하고 DMS는 원문 lifecycle, RAG MetadataStore는 검색 lifecycle을 소유하도록 나누는 것이 장기적으로 가장 안정적이다.

실제 repository 구현 전에는 설치된 `dms` 버전의 signature와 현재 `DocumentStorage` protocol을 함께 검증해야 한다. 현재 위키 기준 프로젝트 상태는 DMS 의존성만 설치되어 있고 소비 통합은 아직 구현되지 않았으며, 검증 절차는 [[verifying-dms-core-contract]]에 정리되어 있다.

## Related pages

- [[dms-core]]
- [[dms-configuration-and-assembly]]
- [[dms-document-lifecycle]]
- [[dms-metadata-and-recovery]]
- [[rag-service-architecture]]
- [[ingestion-pipeline]]
- [[user-scope-isolation]]
- [[persistence-and-restart-recovery]]
- [[verifying-dms-core-contract]]
