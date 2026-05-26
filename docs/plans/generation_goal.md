

## Background
현재 RAG 시스템은 retrieval 단계 이후 generation 단계를 구축하는 중이다.
1차 generation 입력은 `125 exp100` retrieval 결과 중 `J5_hybrid_rrf_rerank` 결과를 사용한다.

이번 작업의 핵심은 단순히 검색된 context를 LLM에 넣는 것이 아니라, 입력 JSON의 실제 key 구조를 먼저 분석한 뒤 질문 유형별로 필요한 field를 선별하여 context를 구성하는 것이다.

또한 generation 결과를 사람이 검수할 수 있게 저장하고, RAGAS 프레임워크를 활용해 생성 품질을 정량적으로 확인할 수 있어야 한다.

generation 단계는 다음 목표를 가진다.

- 질문 유형을 자동 분류한다.
- 입력 JSON의 사용 가능한 key를 분석한다.
- 질문 유형별로 fact, table, text, source_file, fact_candidates 등 활용 가능한 field를 우선순위에 따라 context로 조립한다.
- LLM 답변은 반드시 정해진 JSON 스키마로 후처리한다.
- citation, answerable 여부, missing_info, warnings를 포함해 hallucination 위험을 줄인다.
- 먼저 `review50` 모드로 30~50문항을 생성하고 사람이 수동 검수할 수 있게 한다.
- RAGAS로 Faithfulness, Answer Relevance, Context Precision, Context Recall 지표를 확인할 수 있게 한다.
- 동일 실험을 반복 실행해도 기존 결과를 덮어쓰지 않고 새 output 폴더에 저장한다.
- 이후 같은 구조로 `exp100`, `250`, `690` corpus까지 확장 가능해야 한다.

[가정]
- Judge LLM은 generation 답변 생성 또는 답변 보정에는 사용하지 않는다.
- 단, RAGAS 평가 단계에서 필요한 evaluator LLM/embedding은 생성 품질 평가 용도로만 사용할 수 있다.
- `source_store`는 기본적으로 사용하지 않는다.
- `source_store`는 임베딩 대상이 아니며, 추후 내부 고도화 실험에서만 ID 기반 원문 확장 lookup 용도로 사용한다.
- 입력 JSON 구조가 계획과 다를 수 있으므로, 구현 초기에 실제 JSONL 샘플을 분석하고 그 결과를 기반으로 field mapping을 결정해야 한다.

## Objective
다음 4가지를 완성한다.

1. `src/generation/rfp_generation.py` 신규 모듈 구현
   - 입력 JSONL 샘플 구조 분석
   - 질문 유형 자동 분류
   - JSON key 기반 field-aware context 구성
   - prompt 생성
   - LLM 출력 JSON 후처리
   - 실패 태그 생성
   - citation / numeric grounding / answerable 관련 deterministic 검증 보조 함수 구현
   - RAGAS 평가용 dataframe 또는 dataset 생성 함수 구현

2. `notebooks/rag/rfp_generation_p4_hwpx_quickcheck.ipynb` 신규 노트북 구현
   - 상단 설정값만 바꾸면 `125`, `250`, `690` corpus에 재사용 가능해야 한다.
   - `review50` 모드에서 30~50문항을 먼저 생성할 수 있어야 한다.
   - 다른 팀원이 노트북을 통째로 실행해도 흐름을 이해할 수 있도록 프로젝트 경로, 입력 파일, output 경로 설정 부분에 친절한 한국어 주석을 작성한다.
   - retrieval 이후 Colab/GPU 메모리를 비우고 generation 모델을 로드하는 흐름을 포함해야 한다.
   - OOM fallback 설정을 포함해야 한다.
   - RAGAS 평가 실행 셀을 포함한다.

3. generation 실행 결과 저장 구조 구현
   - 생성 답변 JSONL 저장
   - 검증 요약 metrics 저장
   - 실패 태그 요약 저장
   - 사람이 검수하기 쉬운 review용 CSV 또는 JSONL 저장
   - RAGAS 평가 입력 파일 저장
   - RAGAS 평가 결과 파일 저장
   - 수정한 파일, 실행 설정, 검증 결과를 재현 가능하게 남긴다.

4. 실험별 output 폴더 자동 생성
   - output 폴더 이름은 사용자가 지정한 실험 이름과 실행 시간을 함께 사용한다.
   - 예: `generation_review50_20260523_153012`
   - 동일 실험을 반복 실행해도 기존 결과를 덮어쓰지 않는다.
   - 숫자 suffix 방식보다 실행 시간 timestamp 방식으로 정리한다.
   - output directory는 `mkdir(parents=True, exist_ok=False)`처럼 새 폴더 생성을 기본으로 한다.
   - 결과 저장 경로는 노트북 상단 설정 셀에서 한눈에 확인할 수 있어야 한다.

## Scope

Allowed:
- `src/generation/rfp_generation.py` 신규 생성
- `notebooks/rag/rfp_generation_p4_hwpx_quickcheck.ipynb` 신규 생성
- generation 결과 저장용 output 경로 생성
- RAGAS 평가 결과 저장용 output 경로 생성
- generation 전용 helper 함수, config, schema 정의 추가
- generation 단계에 필요한 최소한의 README 또는 실행 메모 추가
- 입력 JSONL 샘플을 읽어 실제 key 구조를 분석하는 코드 추가
- deterministic validation 함수 추가
- RAGAS 평가용 변환 함수 추가
- Colab/GPU 메모리 정리 코드 추가
- OOM fallback 설정 추가

Expected input patterns:
- `outputs/parsing_p4_hwpx_{N}/chunks_v2_{N}.jsonl`
- `outputs/retrieval_quickcheck_p4_hwpx_{N}/{RUN_NAME}/all_experiment_contexts_*.jsonl`
- 기본 corpus는 `N=125`
- 기본 retrieval run은 `J5_hybrid_rrf_rerank`
- 기본 실행 모드는 `review50`

Expected output pattern:
- `outputs/generation_p4_hwpx_{N}/{EXPERIMENT_NAME}_{RUN_TIMESTAMP}/generated_answers.jsonl`
- `outputs/generation_p4_hwpx_{N}/{EXPERIMENT_NAME}_{RUN_TIMESTAMP}/review_samples.csv`
- `outputs/generation_p4_hwpx_{N}/{EXPERIMENT_NAME}_{RUN_TIMESTAMP}/metrics_summary.json`
- `outputs/generation_p4_hwpx_{N}/{EXPERIMENT_NAME}_{RUN_TIMESTAMP}/failure_tags_summary.json`
- `outputs/generation_p4_hwpx_{N}/{EXPERIMENT_NAME}_{RUN_TIMESTAMP}/ragas_eval_input.jsonl`
- `outputs/generation_p4_hwpx_{N}/{EXPERIMENT_NAME}_{RUN_TIMESTAMP}/ragas_metrics_summary.json`
- `outputs/generation_p4_hwpx_{N}/{EXPERIMENT_NAME}_{RUN_TIMESTAMP}/ragas_per_question.csv`
- `outputs/generation_p4_hwpx_{N}/{EXPERIMENT_NAME}_{RUN_TIMESTAMP}/run_config.json`

Not Allowed:
- retrieval 로직 수정 금지
- parsing/chunking 결과 파일 직접 수정 금지
- 기존 `chunks_v2_{N}.jsonl` 원본 수정 금지
- 기존 retrieval 결과 JSONL 원본 수정 금지
- `source_store`를 기본 입력으로 강제 사용하지 말 것
- `source_store`를 임베딩 대상으로 사용하지 말 것
- RAGAS 평가 결과를 generation 답변 보정에 사용하지 말 것
- 불확실한 JSON key를 존재한다고 가정하고 하드코딩하지 말 것
- 기존 API, 폴더 규칙, 파일명 규칙을 불필요하게 깨지 말 것
- 대규모 리팩터링 금지
- generation과 무관한 retrieval, parsing, chunking 성능 개선 작업 금지
- 불필요한 방어 코드, 과도한 try-except, silent pass, 의미 없는 fallback 코드를 넣지 말 것

## Requirements

### 1. Input JSON structure inspection
- generation을 시작하기 전에 입력 JSONL 샘플을 읽어 실제 key 구조를 분석해야 한다.
- 최소 3~10개 sample record의 top-level key, nested key, value type, missing ratio를 요약해야 한다.
- 분석 결과를 바탕으로 사용 가능한 field를 canonical field로 mapping해야 한다.
- 예상 key가 없으면 즉시 실패하지 말고 fallback 가능한 key를 탐색해야 한다.
- 단, 근거 없는 추측으로 없는 값을 만들어내면 안 된다.

### 2. Canonical field mapping
입력 JSON의 실제 key를 분석한 후, 가능한 경우 아래 canonical field로 mapping한다.

- `question`
- `question_id`
- `retrieved_contexts`
- `source_file`
- `chunk_id`
- `section_title`
- `text`
- `table`
- `fact`
- `fact_candidates`
- `score`
- `rank`
- `metadata`
- `source_store_id`

존재하지 않는 field는 `missing_fields` 또는 `warnings`에 기록한다.

### 3. Question type classification
질문 유형은 코드가 자동 분류해야 한다.

지원할 answer_type 후보:
- `budget`
- `duration`
- `bid_deadline`
- `submission_documents`
- `submission_logistics`
- `eligibility`
- `business_type`
- `requirements`
- `evaluation`
- `summary`
- `multi_doc_comparison`
- `general`
- `unknown`

질문 유형 분류는 keyword rule 기반 MVP로 시작해도 된다.
단, 추후 확장 가능하도록 함수 단위로 분리해야 한다.

### 4. Field-aware context building
질문 유형별로 context 구성 방식이 달라야 한다.

Fact 중심 질문:
- 예: 예산, 사업기간, 입찰마감, 제출기간, 유지보수기간, 보증기간
- `fact_candidates`가 있으면 우선 사용한다.
- 그다음 `fact`, `table`, `text` 순으로 보조 근거를 추가한다.
- evidence는 짧고 명확해야 한다.
- 숫자, 날짜, 금액, 기간은 원문 근거와 함께 유지해야 한다.

긴 요약 / 요구사항 / 평가기준 질문:
- `section_title`, `fact`, `table`, `text` block을 제한적으로 추가한다.
- 너무 긴 context를 그대로 넣지 말고 section 단위로 압축한다.
- 핵심 근거가 되는 chunk와 source_file을 보존한다.

Multi-doc 질문:
- 단순 score 순 나열만 하지 말고 `source_file`별로 묶어 context를 구성한다.
- 문서별 차이, 공통점, 누락 정보를 분리할 수 있어야 한다.
- 특정 문서의 근거가 부족하면 `missing_info`에 기록한다.

### 5. Deadline and duration separation
기간 관련 값은 반드시 분리해서 다뤄야 한다.
다음 항목을 하나로 뭉뚱그리지 말 것.

- `project_duration`
- `submission_deadline`
- `submission_period`
- `bid_deadline`
- `maintenance_period`
- `warranty_period`
- `other_deadline`

예를 들어 사업기간과 입찰마감일을 혼동하면 안 된다.

### 6. Prompt generation
LLM prompt는 다음을 명확히 포함해야 한다.

- 답변은 제공된 context에 근거해야 한다.
- 모르면 추측하지 말고 `is_answerable=false`로 둔다.
- 최종 출력은 반드시 JSON만 반환한다.
- citation은 context에 포함된 source_file, chunk_id, section 정보에서만 생성한다.
- 숫자, 날짜, 금액은 context에 있는 값만 사용한다.
- context에 없는 값은 만들지 않는다.
- 서로 충돌하는 근거가 있으면 confidence를 낮추고 warnings에 기록한다.

### 7. Output JSON schema
LLM의 최종 출력은 반드시 아래 스키마를 따르도록 후처리해야 한다.

{
  "answer": "string",
  "answer_type": "budget|duration|bid_deadline|submission_documents|submission_logistics|eligibility|business_type|requirements|evaluation|summary|multi_doc_comparison|general|unknown",
  "confidence": "high|medium|low",
  "is_answerable": true,
  "final_values": {},
  "documents": [],
  "citations": [],
  "missing_info": [],
  "warnings": []
}

후처리 요구사항:
- JSON 파싱 실패 시 repair를 시도한다.
- repair 실패 시 실패 태그 `llm_invalid_json`을 기록한다.
- 필수 key가 없으면 기본값을 채운다.
- `answer_type`, `confidence`, `is_answerable` 값은 허용 범위 밖이면 보정하거나 warning을 남긴다.
- citation이 context에 없는 source를 참조하면 warning을 남긴다.
- 숫자/날짜/금액이 context 근거 없이 등장하면 hallucination risk warning을 남긴다.

### 8. Failure tags
다음 실패 태그를 지원해야 한다.

- `retrieval_missing`
- `context_building_error`
- `wrong_field_selection`
- `llm_invalid_json`
- `llm_hallucination_risk`
- `incomplete_multi_doc`
- `insufficient_evidence`

각 결과 record에는 필요한 경우 failure tag를 남겨야 한다.

### 9. Memory plan
Colab/GPU 환경을 고려해 다음을 구현 또는 노트북에 포함한다.

- retrieval 결과를 먼저 파일로 저장한 뒤 generation을 실행한다.
- generation 실행 전 embedding model, reranker, Chroma client 참조를 삭제할 수 있는 정리 코드를 둔다.
- `gc.collect()` 실행
- `torch.cuda.empty_cache()` 실행
- 그 다음 generation LLM 로드
- 가장 안전한 흐름은 retrieval 노트북과 generation 노트북을 별도 런타임에서 실행하는 것이다.

OOM fallback 기본값:
- `GENERATION_SAMPLE_SIZE=10`
- `MAX_CONTEXT_CHARS=6000`
- `max_new_tokens=512`
- 그래도 안 되면 `Qwen/Qwen2.5-1.5B-Instruct`로 smoke test만 확인

1차 generation 모델:
- `Qwen/Qwen2.5-3B-Instruct`

### 10. Review50 execution
- 1차 완료 기준은 `review50`에서 30~50문항 생성 가능 상태이다.
- 사람이 검수할 수 있도록 다음 정보를 결과에 포함해야 한다.
  - question_id
  - question
  - predicted answer_type
  - used source_file
  - used chunk_id
  - selected context 요약
  - answer
  - confidence
  - is_answerable
  - final_values
  - citations
  - missing_info
  - warnings
  - failure_tags

### 11. Metrics summary
`review50` 실행 후 최소 다음 지표를 계산하거나 저장해야 한다.

- `total_questions`
- `valid_json_count`
- `valid_json_rate`
- `citation_checked_count`
- `citation_valid_rate`
- `numeric_grounded_checked_count`
- `numeric_grounded_rate`
- `answerable_count`
- `answerable_rate`
- `generation_ms_avg`
- failure tag별 count

`exp100`에서는 위 지표를 100문항 기준으로 저장할 수 있는 구조여야 한다.

### 12. RAGAS generation quality evaluation
RAGAS를 활용해 생성 품질 지표를 확인할 수 있어야 한다.

평가 대상 지표:
- `Faithfulness`
  - 필수 데이터 조합: `answer + contexts`
  - 의미: 답변이 검색된 문서 내용 안에만 존재하는지 확인한다.
  - 목적: hallucination 여부를 정량적으로 확인한다.

- `Answer Relevance`
  - 필수 데이터 조합: `question + answer`
  - 의미: 답변이 원래 질문의 의도에 얼마나 부합하는지 확인한다.
  - 목적: 답변이 질문과 엇나가지 않았는지 확인한다.

- `Context Precision`
  - 필수 데이터 조합: `question + contexts`
  - 의미: 질문과 관련된 문서가 검색 결과 상단에 잘 배치되었는지 확인한다.
  - 목적: generation 품질과 함께 retrieval ranking 품질도 확인한다.

- `Context Recall`
  - 필수 데이터 조합: `ground_truth + contexts`
  - 의미: 실제 정답 문장이 검색된 문서들 안에 포함되어 있는지 확인한다.
  - 목적: retrieval 결과가 정답 근거를 충분히 포함하는지 확인한다.

RAGAS 평가 입력 데이터는 최소 다음 컬럼을 가져야 한다.
- `question`
- `answer`
- `contexts`
- `ground_truth`
- `question_id`
- `answer_type`
- `source_files`
- `chunk_ids`

단, `ground_truth`가 없는 경우:
- `Faithfulness`
- `Answer Relevance`
- `Context Precision`

위 3개 지표를 우선 계산한다.

`Context Recall`은 `ground_truth`가 있는 데이터에서만 계산한다.
`ground_truth`가 없어서 계산하지 못한 경우에는 복잡한 예외 처리를 만들지 말고, `ragas_metrics_summary.json`에 다음처럼 명확히 기록한다.

{
  "context_recall_status": "not_run_missing_ground_truth"
}

RAGAS 평가 결과 저장 파일:
- `ragas_eval_input.jsonl`
- `ragas_metrics_summary.json`
- `ragas_per_question.csv`

RAGAS 평가 결과에는 다음을 포함한다.
- 전체 평균 점수
- 문항별 점수
- answer_type별 평균 점수
- Faithfulness가 낮은 문항 목록
- Answer Relevance가 낮은 문항 목록
- Context Precision이 낮은 문항 목록
- Context Recall이 낮은 문항 목록, 단 ground_truth가 있을 때만

RAGAS 관련 코드는 노트북에서 한 섹션으로 분리한다.
RAGAS import와 metric 설정은 한 셀에 모아 둔다.
설치된 RAGAS 버전에 따라 import path가 달라질 수 있으므로, Codex는 현재 환경의 ragas 버전을 확인하고 그 버전에 맞는 정석적인 API를 사용한다.
단, 여러 버전을 동시에 지원하기 위한 과도한 호환성 방어 코드는 작성하지 않는다.

### 13. Notebook usability for teammates
노트북 상단 설정 영역은 다른 팀원이 바로 이해할 수 있도록 친절한 한국어 주석을 포함해야 한다.

반드시 포함할 설정값:
- `PROJECT_ROOT`
- `CORPUS_N`
- `RUN_NAME`
- `EXPERIMENT_NAME`
- `RUN_TIMESTAMP`
- `OUTPUT_BASE_DIR`
- `OUTPUT_DIR`
- `INPUT_CONTEXTS_PATH`
- `CHUNKS_PATH`
- `USE_SOURCE_STORE`
- `GENERATION_SAMPLE_SIZE`
- `MAX_CONTEXT_CHARS`
- `GENERATION_MODEL_NAME`
- `MAX_NEW_TOKENS`
- `RUN_RAGAS_EVAL`

주석 예시 방향:
- `PROJECT_ROOT`: 노트북이 어느 위치에서 실행되든 프로젝트 루트를 명확히 잡기 위한 경로
- `CORPUS_N`: 125, 250, 690 corpus 중 어떤 데이터를 사용할지 선택
- `RUN_NAME`: retrieval 단계에서 저장한 실험 폴더 이름
- `EXPERIMENT_NAME`: 이번 generation 실험을 구분하기 위한 사람이 읽기 쉬운 이름
- `RUN_TIMESTAMP`: 같은 실험을 반복해도 output이 덮어써지지 않도록 붙이는 실행 시간
- `OUTPUT_DIR`: 이번 실행 결과가 저장되는 최종 폴더

경로 설정은 `pathlib.Path`를 사용한다.
문자열 경로 조합을 남발하지 않는다.

권장 형태:
- `RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")`
- `OUTPUT_DIR = OUTPUT_BASE_DIR / f"{EXPERIMENT_NAME}_{RUN_TIMESTAMP}"`
- `OUTPUT_DIR.mkdir(parents=True, exist_ok=False)`

### 14. Code style
쥬니어 개발자가 봐도 읽기 쉬운 정석적인 코드로 작성한다.

코드 스타일 원칙:
- 함수명과 변수명은 역할이 드러나게 작성한다.
- 지나치게 짧은 축약어를 피한다.
- 한 함수가 너무 많은 일을 하지 않도록 분리한다.
- 복잡한 one-liner보다 읽기 쉬운 여러 줄 코드를 우선한다.
- 불필요한 class 구조를 만들지 않는다.
- MVP 단계에서는 함수 중심 구조를 우선한다.
- type hint를 적절히 사용한다.
- 한국어 주석은 노트북의 설정/실행 흐름 설명에 집중한다.
- 코드 내부에는 당연한 내용을 반복 설명하는 주석을 달지 않는다.
- 넓은 범위의 `try-except Exception`을 남발하지 않는다.
- `pass`, 빈 except, 원인을 숨기는 fallback을 사용하지 않는다.
- 불필요한 방어 코드보다 명확한 입력, 명확한 실패, 명확한 로그를 우선한다.
- 에러 메시지는 팀원이 다음 행동을 알 수 있게 작성한다.

## Success Criteria
The task is complete only when:

- `src/generation/rfp_generation.py`가 생성되어 있고, generation 핵심 로직이 함수 단위로 분리되어 있다.
- `notebooks/rag/rfp_generation_p4_hwpx_quickcheck.ipynb`가 생성되어 있고, 상단 설정값만 바꿔 `125`, `250`, `690` corpus에 재사용 가능하다.
- 노트북 상단 설정 영역에 다른 팀원이 이해할 수 있는 친절한 한국어 주석이 있다.
- 입력 JSONL 샘플 구조를 분석하고, 실제 사용 가능한 key를 요약하는 단계가 있다.
- JSON key 기반 context builder가 구현되어 있다.
- 질문 유형별 context 구성 방식이 최소한 MVP 수준으로 다르게 동작한다.
- `review50` 모드에서 30~50문항을 생성할 수 있다.
- LLM 출력은 지정된 JSON 스키마로 저장된다.
- JSON 파싱 실패, citation 불일치, 근거 부족, hallucination risk를 warning 또는 failure tag로 남긴다.
- generation 결과 파일과 metrics 요약 파일이 저장된다.
- RAGAS 평가 입력 파일이 저장된다.
- RAGAS 평가 결과 파일이 저장된다.
- RAGAS로 Faithfulness, Answer Relevance, Context Precision을 확인할 수 있다.
- ground_truth가 있는 경우 Context Recall도 확인할 수 있다.
- 동일 실험을 반복 실행해도 기존 output을 덮어쓰지 않고 timestamp가 포함된 새 폴더에 저장된다.
- retrieval 코드와 parsing/chunking 결과 원본은 수정하지 않았다.
- `USE_SOURCE_STORE=False`가 기본값이다.
- Colab/GPU OOM을 줄이기 위한 fallback 설정이 포함되어 있다.
- 250/690 corpus로 확장하기 쉬운 설정 구조를 갖춘다.
- 불필요한 방어 코드 없이 정석적이고 읽기 쉬운 코드로 작성되어 있다.

## Verification Evidence
Before finishing, provide:

- 생성 또는 수정한 파일 목록
- 주요 함수 목록과 역할 요약
- 입력 JSON 구조 분석 결과 요약
  - top-level keys
  - 주요 nested keys
  - 사용 가능한 context 관련 keys
  - 누락되었거나 fallback 처리한 keys
- 노트북 상단 설정값 요약
- 생성된 `OUTPUT_DIR` 경로
- output 폴더가 timestamp 기반으로 생성되어 기존 결과를 덮어쓰지 않는다는 증거
- `review50` 실행 여부
- 실행한 명령어 또는 노트북 실행 순서
- 저장된 generation 결과 파일 경로
- 저장된 metrics 파일 경로
- 저장된 RAGAS input 파일 경로
- 저장된 RAGAS metrics 파일 경로
- `valid_json_rate`
- `citation_valid_rate`
- `numeric_grounded_rate`
- `answerable_rate`
- `generation_ms_avg`
- failure tag별 count
- RAGAS `Faithfulness` 평균 점수
- RAGAS `Answer Relevance` 평균 점수
- RAGAS `Context Precision` 평균 점수
- RAGAS `Context Recall` 평균 점수 또는 미실행 사유
- OOM fallback 사용 여부
- 남아 있는 리스크
- 사람이 추가 검수해야 할 항목

검증을 실제로 실행하지 못했다면, 실행하지 못한 이유를 명확히 적고 어떤 명령 또는 노트북 셀을 실행하면 되는지 제시한다.

## Constraints

Technical constraints:
- Python 기반으로 구현한다.
- 기존 retrieval 코드는 수정하지 않는다.
- 기존 parsing/chunking 결과 원본은 수정하지 않는다.
- 기본 LLM은 `Qwen/Qwen2.5-3B-Instruct`로 둔다.
- OOM fallback으로 `Qwen/Qwen2.5-1.5B-Instruct`를 사용할 수 있게 한다.
- 기본 `USE_SOURCE_STORE=False`로 둔다.
- `source_store` 파일이 없으면 자동으로 `USE_SOURCE_STORE=False`로 동작해야 한다.
- `MAX_CONTEXT_CHARS`, `GENERATION_SAMPLE_SIZE`, `max_new_tokens`를 설정값으로 분리한다.
- JSONL 입출력은 streaming 또는 line-by-line 처리로 메모리 사용량을 줄인다.
- 대규모 데이터를 한 번에 모두 메모리에 올리지 않는다.
- RAGAS 평가는 generation 이후 별도 단계로 실행한다.
- RAGAS 평가 결과는 generation 답변을 수정하거나 보정하는 데 사용하지 않는다.

Output constraints:
- 모든 실행 결과는 timestamp가 포함된 새 output 폴더에 저장한다.
- 동일 실험 반복 시 기존 output을 덮어쓰지 않는다.
- `run_config.json`에 주요 설정값을 저장한다.
- 사람이 나중에 결과를 추적할 수 있도록 파일명과 폴더명은 명확하게 작성한다.

Quality constraints:
- JSON 출력 형식의 일관성을 최우선으로 한다.
- hallucination 방지를 최우선으로 한다.
- context에 없는 숫자, 날짜, 금액, 기관명, 문서명을 생성하지 않는다.
- 근거가 부족하면 답을 꾸며내지 말고 `is_answerable=false` 또는 `confidence=low`로 처리한다.
- citation은 반드시 입력 context에서 확인 가능한 값만 사용한다.
- 동일한 기간 관련 질문에서 사업기간, 접수기간, 입찰마감, 유지보수기간, 보증기간을 혼동하지 않는다.
- RAGAS 점수는 generation 품질을 판단하는 보조 지표로 사용한다.
- RAGAS 점수가 낮은 문항은 사람이 우선 검수할 수 있도록 별도 목록으로 저장한다.

Memory constraints:
- Colab/GPU 메모리 안정성을 고려한다.
- generation 전에 불필요한 retrieval 객체 참조를 제거하는 코드를 제공한다.
- context 길이를 제한한다.
- review 단계에서는 30~50문항만 먼저 실행한다.
- OOM 발생 시 sample size, context length, max_new_tokens, model size 순으로 낮춘다.
- RAGAS 평가도 처음에는 review50 결과를 대상으로 실행한다.

Maintainability constraints:
- 125 corpus에만 종속된 하드코딩을 피한다.
- `{N}` 설정값 변경만으로 250/690 corpus에 확장 가능해야 한다.
- 질문 유형 분류, context 구성, prompt 생성, JSON 후처리, metrics 계산, RAGAS 평가 데이터 변환을 함수 단위로 분리한다.
- key mapping 로직은 추후 입력 JSON 구조가 바뀌어도 수정하기 쉽게 분리한다.
- 쥬니어 개발자가 읽을 수 있도록 정석적이고 명확한 코드 구조를 유지한다.

## Decision Rules
During each iteration:

- 먼저 실제 입력 JSONL 구조를 분석한다.
- 예상과 다른 key 구조가 발견되면, 임의로 추측하지 말고 mapping 후보와 누락 field를 보고한다.
- field가 여러 개 있을 경우 우선순위는 다음과 같다.
  1. 질문 유형과 직접 관련된 fact_candidates 또는 structured field
  2. table 또는 semi-structured evidence
  3. section_title이 포함된 text block
  4. 일반 text
- fact 질문에서는 짧고 정확한 evidence를 우선한다.
- 요약/요구사항/평가기준 질문에서는 section 단위 context를 우선한다.
- multi-doc 질문에서는 source_file별 grouping을 우선한다.
- JSON 형식 안정성이 답변의 자연스러움보다 중요하다.
- hallucination 방지가 답변 완성도보다 중요하다.
- Colab/GPU 안정성이 대용량 일괄 실행보다 중요하다.
- RAGAS 평가는 review50 generation 완료 후 실행한다.
- RAGAS 평가를 위해 필요한 `question`, `answer`, `contexts`를 generation 결과에서 명확히 추출한다.
- `ground_truth`가 없는 경우 Context Recall만 계산하지 않고, 나머지 RAGAS 지표는 계산한다.
- 불확실하면 confidence를 낮추고 warnings 또는 missing_info에 기록한다.
- 근거가 없으면 답변을 생성하지 말고 `is_answerable=false`로 처리한다.
- 최소 변경 원칙을 지키되, generation 모듈의 유지보수성과 확장성은 확보한다.
- 불필요한 방어 코드보다 명확한 데이터 흐름과 읽기 쉬운 구현을 우선한다.

## Stop Conditions
Stop and report instead of guessing if:

- 입력 JSONL 파일을 찾을 수 없다.
- retrieval 결과 파일 경로를 확정할 수 없다.
- 입력 JSON 구조가 계획과 크게 다르고, 어떤 field를 context로 써야 할지 판단할 수 없다.
- 질문 본문을 찾을 수 있는 key가 없다.
- context로 사용할 수 있는 text, fact, table, chunk 계열 field가 없다.
- source_file 또는 chunk_id 등 citation 근거를 만들 최소 metadata가 없다.
- GPU 메모리 부족으로 fallback 후에도 smoke test가 불가능하다.
- `Qwen/Qwen2.5-3B-Instruct` 로드가 불가능하고 대체 모델 사용도 불가능하다.
- RAGAS 설치 또는 import가 불가능하다.
- 현재 환경의 RAGAS 버전에서 필요한 평가 API를 확인할 수 없다.
- retrieval 코드 수정 없이는 진행할 수 없는 문제가 발견된다.
- parsing/chunking 결과 원본을 수정해야만 해결 가능한 문제가 발견된다.
- `source_store=True`를 강제해야만 답변 가능한 구조로 확인된다.
- 요구사항끼리 충돌한다.
- 안전하지 않거나 범위를 벗어난 변경이 필요하다.

When stopped, report:

- What was attempted
- What evidence was found
- Where the blocker is
- Which file/path/key caused the blocker
- What information or permission is needed next
- Whether a safe partial implementation was completed
- Suggested next action