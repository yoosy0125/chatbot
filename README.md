# RAG Codeit Project - YSY 작업 브랜치 안내

이 fork는 팀 공용 repo에 바로 섞지 않고, 개인 작업 브랜치를 분리해서 공유하기 위한 저장소입니다.

제가 작업한 RFP RAG 관련 파일은 제 fork의 YSY 브랜치에 통합해두었습니다.
(확인하거나 테스트하실 분은 아래처럼 받아주세요! `main`이 아니라 `YSY` 브랜치입니다!)

```bash
git clone https://github.com/yoosy0125/chatbot.git
cd chatbot
git checkout YSY
```

이미 clone한 상태라면:

```bash
git fetch origin
git checkout YSY
git pull origin YSY
```

## 2026.05.18일 기준 포함된 내용은

HWP 텍스트 추출/아티팩트 제거, parsing phase1/phase2, v2_p2 JSONL 구조, 확장 평가 모듈, KoE5+Chroma R0~R6 retrieval 실험 노트북입니다.

원본 RFP 데이터, outputs, Chroma DB, embedding cache, prediction JSONL, API key는 GitHub에 올리지 않았습니다.
필요한 데이터/산출물은 별도 공유 드라이브에서 다운로드하시거나 제게 개별적으로 요청 부탁드립니다.

## 브랜치 요약

main       안내 README만 있는 브랜치
YSY        최종 통합 작업 브랜치
hwp        HWP 추출 작업 기록용
parsing    파싱 작업 기록용
evaluation 평가 작업 기록용
rag        리트리벌 작업 기록용

## Branch Structure

```text
yoosy0125/chatbot
├─ main
│  └─ 안내용 README만 유지
│
├─ YSY
│  └─ 최종 통합 작업 브랜치
│     ├─ 공통 README / requirements / .gitignore
│     ├─ HWP 텍스트 추출 및 아티팩트 제거 검증
│     ├─ RFP parsing phase1 / phase2
│     ├─ v2_p2 JSONL corpus 설계
│     ├─ 확장 retrieval 평가 모듈
│     └─ KoE5 + Chroma R0~R6 retrieval 실험 노트북
│
├─ hwp
│  └─ HWP 추출 작업 기록용 브랜치
│
├─ parsing
│  └─ 파싱/JSONL corpus 생성 작업 기록용 브랜치
│
├─ evaluation
│  └─ 평가 지표 확장 작업 기록용 브랜치
│
└─ rag
   └─ 임베딩/리트리벌 실험 작업 기록용 브랜치
```

## YSY Branch Tree

```text
chatbot/
├─ README.md
├─ requirements.txt
├─ .env.example
├─ .gitignore
├─ data/
│  └─ README.md
├─ docs/
│  ├─ plans/
│  │  ├─ plan.md
│  │  └─ context_engineering_plan.md
│  └─ notes/
│     └─ tagging_experiment_share_note.md
├─ notebooks/
│  ├─ parsing/
│  ├─ eval/
│  └─ rag/
└─ src/
   └─ parsing/
```

## Included

- HWP 텍스트 추출 및 아티팩트 제거 검증 노트북
- RFP 문서 parsing phase1/phase2 노트북
- JSONL key 설명 문서
- P2 250개 corpus sanity check 노트북
- 확장 retrieval 평가 스크립트
- KoE5 + Chroma R0~R6 retrieval 실행 노트북
- 재현용 README / requirements / `.env.example`

## Not Included

용량과 데이터 관리 문제로 아래 파일은 GitHub에 올리지 않았습니다.

```text
data 원본 RFP
outputs/
Chroma DB
embedding cache
prediction JSONL
retrieval_experiments.csv
.env / API key
zip 파일
```

필요한 데이터와 산출물은 별도 공유 드라이브에서 받아 로컬 또는 Colab/GCV 환경에 배치해야 합니다.
