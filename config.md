# Configuration Guide

이 문서는 `.env.example` 기준으로 정리한 `docmesh-rag-system-core` 설정 안내서입니다.
즉, 아래 설정 예시와 항목 설명은 현재 체크인된 `.env.example`와 동일한 계약을 따릅니다.

---

## 1. canonical configuration example

```env
# docmesh-rag-system-core canonical configuration example
# Legacy envs are no longer supported:
# - OLLAMA_EMBED__*
# - OLLAMA_GENERATE__*
# - MILVUS__*

# Shared Ollama runtime
OLLAMA_HOST=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_GENERATION_MODEL=gpt-oss:20b
OLLAMA_REQUEST_TIMEOUT_SECONDS=30

# Milvus runtime
MILVUS_URI=./data/metadata.milvus.db
MILVUS_COLLECTION=rag_chunks
MILVUS_REQUEST_TIMEOUT_SECONDS=30
MILVUS_CONNECT_TIMEOUT_SECONDS=30

# Optional auth mode
# DOCMESH_AUTH_MODE=keycloak

# If using keycloak mode, configure the required docmesh-py-core auth settings too.
# Example names depend on your shared docmesh config contract.
# KEYCLOAK_URL=
# KEYCLOAK_REALM=
# KEYCLOAK_CLIENT_ID=
```

---

## 2. 항목 설명

| 변수 | 설명 | 예시 | 비고 |
|---|---|---|---|
| `OLLAMA_HOST` | Ollama 서버 주소 | `http://ollama:11434` | Shared Ollama runtime |
| `OLLAMA_EMBEDDING_MODEL` | 임베딩 모델명 | `bge-m3` | embedding client 생성에 필요 |
| `OLLAMA_GENERATION_MODEL` | 생성 모델명 | `gpt-oss:20b` | generation client 생성에 필요 |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | Ollama 요청 타임아웃(초) | `30` | 공통 Ollama timeout |
| `MILVUS_URI` | Milvus Lite 파일 경로 또는 URI | `./data/metadata.milvus.db` | vector store 저장 위치 |
| `MILVUS_COLLECTION` | 사용할 collection 이름 | `rag_chunks` | 미설정 시 기본값 `rag_chunks` |
| `MILVUS_REQUEST_TIMEOUT_SECONDS` | Milvus 요청 타임아웃(초) | `30` | 우선 timeout 소스 |
| `MILVUS_CONNECT_TIMEOUT_SECONDS` | Milvus 연결 타임아웃(초) | `30` | request timeout 없을 때 fallback 가능 |
| `DOCMESH_AUTH_MODE` | 인증 모드 | `keycloak` | 주석 해제 시 Keycloak 기반 user id 해석 사용 |
| `KEYCLOAK_URL` | Keycloak 서버 URL | 예: `https://auth.example.com` | `.env.example`에는 예시 이름만 주석으로 제시됨 |
| `KEYCLOAK_REALM` | Keycloak realm | 예: `docmesh` | 실제 이름/계약은 shared docmesh config에 따름 |
| `KEYCLOAK_CLIENT_ID` | Keycloak client id | 예: `rag-core` | 실제 이름/계약은 shared docmesh config에 따름 |

---

## 3. `.env.example`와 동기화된 규칙

### 3.1 지원되는 환경변수
현재 canonical 환경변수는 다음 그룹입니다.
- Ollama runtime
- Milvus runtime
- Optional auth mode (`DOCMESH_AUTH_MODE`)
- Keycloak 관련 추가 설정(주석 예시)

### 3.2 더 이상 지원하지 않는 legacy env
`.env.example` 기준으로 다음 환경변수 패턴은 더 이상 지원하지 않습니다.
- `OLLAMA_EMBED__*`
- `OLLAMA_GENERATE__*`
- `MILVUS__*`

### 3.3 Keycloak 사용 시
- `DOCMESH_AUTH_MODE=keycloak`를 활성화해야 합니다.
- 추가 Keycloak 설정이 필요합니다.
- 정확한 설정 이름/계약은 `docmesh-py-core`의 shared config contract를 따라야 합니다.

---

## 4. 빠른 사용 절차

1. `.env.example`를 복사해 `.env`를 만듭니다.
2. Ollama 주소와 모델명을 환경에 맞게 수정합니다.
3. Milvus 경로/collection을 환경에 맞게 수정합니다.
4. Keycloak을 쓰는 경우 관련 설정을 추가합니다.
5. 애플리케이션을 실행합니다.

예:

```bash
cp .env.example .env
```

---

## 5. 관련 파일

- `.env.example`
- `README.md`
- `docs/api.md`
- `docs/prd.md`
- `docs/test.md`
