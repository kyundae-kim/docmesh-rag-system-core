---
source_url: https://github.com/kyundae-kim/dms-core/wiki/Configuration-v0.6.0
ingested: 2026-07-27
sha256: 91594367444281559dcc96c35ab2ec1b3875d7a857e3065497853edfe1d3892d
---
# DMS SDK 설정 레퍼런스

이 문서는 DMS SDK 조립 방법, 환경변수 선택 규칙, lifecycle 소유권을 설명한다.

- 공개 타입과 메서드: [API 레퍼런스](api.md)
- 복사해 조정할 흐름: [사용 예제](examples.md)
- 전체 템플릿: [`.env.example`](../.env.example)

## 조립 방식 선택

| 방식 | 설정 원천 | 자원 소유권 | 용도 |
| --- | --- | --- | --- |
| `create_sdk_from_environment()` | 호출 시점의 프로세스 환경 | SDK | 일반 애플리케이션 bootstrap |
| `create_sdk_from_service_configs()` | 이미 검증된 `ServiceConfigs` | SDK | 환경을 다시 읽지 않는 조립 |
| `create_sdk_from_clients()` | 호출자가 만든 Engine·MinIO client | 기본은 호출자 | 기존 client를 공유하는 호스트 |
| `create_sdk_from_components()` | 호출자가 만든 adapter | callback으로 명시 | 테스트, 확장, 사용자 저장소 |

## 환경 기반 조립

DMS에는 문서 정보 저장소 하나와 MinIO가 필요하다.

### 저장소 선택 순서

1. `DMS_METADATA_BACKEND=postgresql|sqlite`가 있으면 해당 저장소만 명시적으로 선택한다.
2. 명시값이 없고 `POSTGRES_*`가 하나라도 있으면 PostgreSQL을 선택한다.
3. PostgreSQL 단서가 없고 `SQLITE_PATH`가 있으면 SQLite를 선택한다.
4. 둘 다 없으면 PostgreSQL 또는 SQLite가 필요하다는 진단을 반환한다.
5. 자동 선택에서 PostgreSQL과 SQLite가 모두 있으면 PostgreSQL을 선택하고 경고한다.
6. 이 모호한 구성을 `DMS_CONFIGURATION_STRICT=true`로 거부할 수 있다.

명시하지 않은 저장소의 불완전한 설정은 조립 대상이 아니다. 그러나 `POSTGRES_DSN`은 지원하지 않는 legacy key로 항상 진단한다.

### 사전 진단

```python
from dms import diagnose_environment, format_environment_diagnosis

diagnosis = diagnose_environment(env)
if not diagnosis.valid:
    raise RuntimeError(format_environment_diagnosis(diagnosis))
```

진단은 연결이나 client 생성을 수행하지 않는다. 전달한 mapping을 사용하며 프로세스 환경을 변경하지 않는다. 결과는 선택 backend, 필수 누락 key, 경고, 미지원 key, 시작 상태 확인 여부를 포함한다. `ConfigurationError.diagnosis`로 같은 구조를 확인할 수 있다.

## DMS 환경변수

| 환경변수 | 값·기본값 | 효과 | 비밀값 |
| --- | --- | --- | --- |
| `DMS_METADATA_BACKEND` | 미설정, `postgresql`, `sqlite` | 문서 정보 저장소 명시 선택 | 아니요 |
| `DMS_CONFIGURATION_STRICT` | 기본 `false`; true/false 계열 | 자동 선택의 중복 저장소 구성을 거부 | 아니요 |
| `DOCMESH_HEALTHCHECK_ENABLED` | 기본 `true`; `0`, `false`, `no`, `off`는 false | 환경 기반 조립의 startup 상태 확인 | 아니요 |

`DOCMESH_HEALTHCHECK_ENABLED`는 DMS가 typed core runtime plan의 `HealthcheckPolicy.on_startup`으로 변환한다.

## docmesh-py-core 공통 설정

| 환경변수 | 기본값 | 효과 |
| --- | --- | --- |
| `DOCMESH_ENV` | `development` | 실행 환경 이름과 production alias 판정 |
| `DOCMESH_SECURITY_MODE` | 미설정 | 설정되면 환경 alias보다 우선하는 `development|production` 보안 모드 |
| `DOCMESH_PRODUCTION_ALIASES` | `prod,production` | production으로 간주할 환경 이름 CSV |

production에서는 MinIO 암호화 연결과 인증서 확인을 끌 수 없다. `.env.example`의 endpoint와 credential은 예시일 뿐 실제 배포값으로 교체해야 한다.

## PostgreSQL 설정

PostgreSQL을 선택하면 `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`가 필수다.

| 환경변수 | 타입 | 기본값 | 비밀값·효과 |
| --- | --- | --- | --- |
| `POSTGRES_HOST` | string | 없음 | host |
| `POSTGRES_PORT` | int >= 1 | `5432` | port |
| `POSTGRES_DB` | string | 없음 | database |
| `POSTGRES_USER` | string | 없음 | 사용자 |
| `POSTGRES_PASSWORD` | string | 없음 | 비밀값 |
| `POSTGRES_SSLMODE` | string | `prefer` | PostgreSQL SSL mode |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | int >= 1 | `10` | 연결 timeout |
| `POSTGRES_POOL_SIZE` | int >= 1 | `5` | SQLAlchemy pool size |
| `POSTGRES_MAX_OVERFLOW` | int >= 0 | `10` | pool overflow |
| `POSTGRES_POOL_PRE_PING` | bool | `false` | checkout 전 연결 검사 |
| `POSTGRES_POOL_RECYCLE_SECONDS` | int >= -1 | `-1` | 연결 recycle |
| `POSTGRES_ECHO` | bool | `false` | SQLAlchemy SQL log |
| `POSTGRES_APPLICATION_NAME` | string | 미설정 | PostgreSQL application name |

`POSTGRES_DSN`은 지원하지 않는다. 개별 `POSTGRES_*` 필드를 사용한다.

## SQLite 설정

SQLite를 선택하면 `SQLITE_PATH`가 필수다. SQLite는 문서 정보 저장소만 대체하므로 MinIO는 여전히 필요하다.

| 환경변수 | 타입 | 기본값 | 효과 |
| --- | --- | --- | --- |
| `SQLITE_PATH` | string | 없음 | 파일 경로 또는 `:memory:` |
| `SQLITE_READONLY` | bool | `false` | 읽기 전용 연결 |
| `SQLITE_ENABLE_WAL` | bool | `false` | WAL 활성화 |
| `SQLITE_BUSY_TIMEOUT_MS` | int >= 0 | `5000` | busy timeout |
| `SQLITE_CHECK_SAME_THREAD` | bool | `false` | sqlite thread 검사 |
| `SQLITE_ECHO` | bool | `false` | SQLAlchemy SQL log |

상대 경로는 호스트의 현재 작업 디렉터리를 기준으로 하며 SDK가 상위 디렉터리를 만들지 않는다.

## MinIO 설정

DMS 조립에서는 `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`이 모두 필수다. core의 일반 MinIO 연결에서는 bucket이 선택값이지만 DMS 문서 저장에는 필수다.

| 환경변수 | 타입 | 기본값 | 비밀값·효과 |
| --- | --- | --- | --- |
| `MINIO_ENDPOINT` | string | 없음 | endpoint |
| `MINIO_ACCESS_KEY` | string | 없음 | 비밀값 |
| `MINIO_SECRET_KEY` | string | 없음 | 비밀값 |
| `MINIO_BUCKET` | string | 없음 | 문서 bucket |
| `MINIO_SECURE` | bool | `true` | HTTPS 사용 |
| `MINIO_CERT_CHECK` | bool | `true` | 인증서 확인 |
| `MINIO_REGION` | string | 미설정 | region |
| `MINIO_REQUEST_TIMEOUT_SECONDS` | int >= 1 | `30` | operation timeout |
| `MINIO_MAX_RETRIES` | int >= 0 | `3` | 재시도 횟수 설정 |

production에서는 `MINIO_SECURE=true`와 `MINIO_CERT_CHECK=true`가 필요하다.

## Factory 옵션

### 공통 확장 옵션

| 옵션 | 기본값 | 적용 범위 |
| --- | --- | --- |
| `logger` | `dms.sdk` logger | 모든 factory |
| `metadata_validator` | `DefaultMetadataPolicy` | 모든 factory |
| `metadata_max_serialized_bytes` | `16_384` | 기본 policy를 만드는 factory |
| `metadata_max_depth` | `8` | 기본 policy를 만드는 factory |
| `recovery_audit_hook` | `None` | 모든 factory, best-effort 복구 감사 |
| `max_file_size` | `None` | client/component factory |
| `id_generator` | UUID 생성기 | client/component factory |
| `close_callbacks` | 빈 목록 | client/component factory |

custom `metadata_validator`를 제공하면 `metadata_max_serialized_bytes`와 `metadata_max_depth`는 해당 custom validator에 자동 적용되지 않는다.

### Component factory 전용

| 옵션 | 의미 |
| --- | --- |
| `metadata_store` | 문서 정보 저장 adapter |
| `object_store` | 문서 본문 저장 adapter |
| `service_checks` | `check_health()`에서 실행할 이름별 callback |
| `operation_store` | 멱등성 operation 저장소 |

### Client factory 전용

`engine`, `minio_client`, `bucket_name`이 필수다. 주입 client를 SDK가 자동 종료하지 않는다. `close_callbacks`에 명시적으로 등록한 작업만 SDK 종료 시 실행한다.

### ServiceConfigs factory 전용

`check_on_startup=False`가 기본이다. true이면 SDK 반환 전에 선택 서비스 상태를 확인하고 실패 시 조립 자원을 정리한다. 설정 묶음에 다른 서비스가 있어도 DMS는 선택한 문서 정보 저장소와 MinIO만 조립한다.

## Lifecycle과 동시성

- 환경·설정 기반 factory가 만든 서비스 client는 SDK가 소유한다.
- client·component 기반 factory에 주입한 자원은 기본적으로 호출자가 소유한다.
- `close_callbacks`는 SDK가 종료 책임을 위임받았을 때만 사용한다.
- SDK를 `with` 또는 `async with`로 사용하면 정상·예외 종료에서 정리된다.
- 환경 기반 조립 중 다른 thread가 `DMS_*`, `DOCMESH_*`, `POSTGRES_*`, `SQLITE_*`, `MINIO_*`를 변경하지 않아야 한다.

## 설정 오류 처리

설정 파싱·선택·보안 검증·조립 오류는 `ConfigurationError`로 변환된다. 환경 진단이 있으면 `diagnosis` 속성에 보존된다. 외부 HTTP 응답에는 원래 오류 문자열 대신 `recommended_http_error()`의 secret-safe 메시지를 사용한다.

## 설정 추적표

| 설정 영역 | API | `.env.example` | 예제 |
| --- | --- | --- | --- |
| 저장소 선택과 엄격 모드 | `diagnose_environment`, `create_sdk_from_environment` | DMS 선택 절 | [환경 진단](examples.md#4-환경-사전-진단) |
| PostgreSQL | 환경 factory, service-config factory | PostgreSQL 절 | [환경 기반 조립](examples.md#1-환경-기반-sdk) |
| SQLite | 환경 factory, service-config factory | SQLite 절 | [검증된-설정-묶음](examples.md#2-검증된-설정-묶음으로-조립) |
| MinIO | 모든 기본 조립 경로 | MinIO 절 | 1, 2, 3 |
| Component 옵션 | `create_sdk_from_components` | 해당 없음 | [명시적 component 조립](examples.md#3-명시적-component-조립) |
| Metadata policy | 모든 factory | 해당 없음 | [구조화 metadata 검증](examples.md#11-구조화-metadata-검증) |
| 상태 확인 | `check_health`, startup option | `DOCMESH_HEALTHCHECK_ENABLED` | [상태-확인과-종료](examples.md#13-상태-확인과-종료) |
