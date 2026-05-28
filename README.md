# RAG Codeit Project

공공/기업 RFP 문서를 기반으로 parsing, retrieval, generation 실험을 진행하는 프로젝트입니다.

GitHub에는 코드, 노트북, 재현용 스크립트, 설명 문서만 관리합니다. 원본 문서, 생성 corpus, Chroma DB, embedding cache, API key는 용량과 보안 문제로 올리지 않습니다.

## 현재 기준 브랜치

```text
main       저장소 안내 README
parsing    RFP 원문 parsing, corpus 생성, 데이터 보정, validation/QC 스크립트
rag        retrieval 및 generation 실행 노트북, generation 로직, RAG 실험 문서
hwp        HWP 추출 검증 기록용 브랜치
evaluation 평가 모듈 기록용 브랜치
```

이전 통합용 `YSY` 브랜치와 `generation-handoff-ysy` 브랜치는 현재 기준으로는 사용하지 않습니다. 작업 확인은 목적에 따라 `parsing` 또는 `rag` 브랜치를 기준으로 해주세요.

## 추천 사용 기준

### Corpus 생성/보정/검증

```bash
git checkout parsing
```

주요 위치:

```text
src/parsing/
notebooks/parsing/
scripts/corpus/20260528/
scripts/g2b/
```

`parsing` 브랜치는 원본 RFP에서 corpus를 만들고, 금액 역할 분류, 나라장터 보강, slim corpus 생성, validation/manifest/hash 검증까지 재현하기 위한 코드가 중심입니다.

### Retrieval/Generation 실험

```bash
git checkout rag
```

주요 위치:

```text
notebooks/rag/
src/generation/
docs/plans/
docs/notes/
```

`rag` 브랜치는 Chroma/KoE5 기반 retrieval 실험, generation quickcheck, context builder 및 답변 생성 로직을 확인하는 기준 브랜치입니다.

## GitHub에 포함하지 않는 것

```text
data/original_data_list/
data/hwpx_664/
outputs/
Chroma DB
embedding cache
prediction JSONL
.env / API key
zip 파일
대용량 corpus JSONL / source_store JSONL
```

필요한 원본 데이터와 corpus 산출물은 별도 공유 드라이브에서 받아 로컬, Colab, GCP 런타임에 배치해서 사용합니다.

## 실행 시 주의

- 실험용 embedding에는 slim corpus의 `chunks_v2_*.jsonl` 사용을 권장합니다.
- `source_store_v2_*.jsonl`은 임베딩 대상이 아니라 generation 단계의 원문 확장/근거 확인용입니다.
- corpus 생성 로직은 `parsing`, retrieval/generation 실험은 `rag` 기준으로 관리합니다.
