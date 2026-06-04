# docmesh-rag-system-core

DocMesh 프로젝트의 RAG System core package

## 개요

이 패키지는 문서 적재, 검색, 답변 생성을 담당하는 RAG 코어입니다.

관련 문서:
- [PRD](docs/prd.md)
- [API 문서](docs/api.md)
- [테스트 문서](docs/test.md)

현재 코어는 다음 원칙으로 동작합니다.
- `token` 기반 사용자 스코프 분리
- 코어 내부에서 인증 상태를 저장하지 않는 stateless 구조
- `token`이 없으면 단일 사용자 모드로 동작
- `DocumentStorage`는 문서 본문 자체를 메타데이터에 넣지 않고 **문서 파일/오브젝트 자산**을 관리
- ingest는 **텍스트 입력**과 **파일 입력**을 분리해서 처리

## 현재 인터페이스

`RAGCore`는 `token`을 직접 받아 사용자 스코프를 결정합니다.

- `token`이 있으면: 해당 token 문자열을 사용자 스코프로 사용
- `token`이 없거나 공백이면: `single-user` 스코프로 처리

문서 적재는 세 경로로 분리됩니다.

- `ingest_text(...)`: 텍스트 본문을 직접 입력
- `ingest_file_stream(...)`: 파일 스트림을 입력
- `ingest_file_path(...)`: 파일 경로를 입력

## DocumentStorage 동작

`DocumentStorage`의 책임은 문서 내용을 인라인으로 들고 있는 것이 아니라, MinIO 같은 스토리지 계층처럼 **문서 파일 자산을 관리**하는 것입니다.

- `local` 모드: 관리 디렉터리 아래에 문서 파일을 저장하고 `storage_path`를 기록
- `memory` 모드: 메모리 상의 논리적 오브젝트(`memory://...`)로 관리하고 `storage_path`를 기록
- 문서 메타데이터에는 문서 본문을 직접 저장하지 않음

즉, `DocumentRecord`는 본문(text)을 들고 있지 않고, 저장된 문서 자산 위치를 가리키는 방식입니다.

## 사용 예시

```python
from io import BytesIO
from pathlib import Path

from rag_system_core import OllamaEmbeddingClient, RAGCore


class GenerationClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


# environment variables:
# - OLLAMA_BASE_URL=http://ollama:11434
# - OLLAMA_EMBED_MODEL=bge-m3
# - OLLAMA_TIMEOUT=30
core = RAGCore(
    embedding_client=OllamaEmbeddingClient(),
    generation_client=GenerationClient(),
    metadata_path=Path("./data/metadata.db"),
    document_storage_dir=Path("./data/documents"),
    storage_mode="local",
)

# 1) 텍스트 직접 적재
core.ingest_text(
    token="user-token-a",
    text="alpha beta gamma",
    source="note.txt",
)

# 2) 파일 스트림 적재
stream = BytesIO(b"document from stream")
core.ingest_file_stream(
    token="user-token-a",
    file_stream=stream,
    source="stream.txt",
)

# 3) 파일 경로 적재
core.ingest_file_path(
    token="user-token-a",
    file_path=Path("./sample.txt"),
)

response = core.query(
    token="user-token-a",
    question="alpha에 대해 요약해줘",
    top_k=3,
)

print(response.answer)

stored = core.list_documents(token="user-token-a")[0]
print(stored.storage_path)

# 단일 유저 모드: token 생략 가능
core.ingest_text(
    text="single user document",
    source="solo.txt",
)

single_user_response = core.query(
    question="문서를 요약해줘",
)

print(single_user_response.answer)
```

## 주요 기능

- 문자열 직접 입력 / 파일 스트림 / 파일 경로 입력 지원
- 고정 길이 청킹 + overlap 지원
- 배치 임베딩 호출 구조
- 사용자 스코프별 검색 분리
- 프롬프트 구성
  - `[System Prompt]`
  - `[Retrieved Context]`
  - `[User Query]`
- SQLAlchemy ORM + SQLite 기반 문서/청크 메타데이터 persistence 지원
- 재시작 시 저장된 청크/임베딩을 다시 로드해 retrieval 복원 가능
- 문서별 청크 조회 및 문서 삭제 시 메타데이터/청크/자산 정리 지원
- memory / local storage 모드 지원
- 문서 자산 경로(`storage_path`) 기반 문서 관리

## 테스트

```bash
pytest -q
```
