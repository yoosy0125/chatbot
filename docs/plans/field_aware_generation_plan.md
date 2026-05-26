# Field-Aware RFP Generation 구현 계획

## Summary
- 1차 generation 모델은 `Qwen/Qwen2.5-3B-Instruct`를 사용한다.
- 입력 retrieval 결과는 `outputs/exp100_0525_exp1_recallguard_docfill_metadatafilter`의 `J5_hybrid_rrf_rerank` generation prediction JSONL을 기본으로 사용한다.
- 기본 공유 모드는 `USE_SOURCE_STORE=False`이다. `source_store`는 임베딩 대상이 아니며, 추후 고도화 시 ID 기반 원문 확장 lookup 용도로만 사용한다.
- 이번 수정의 핵심은 LLM이 긴 citation까지 직접 생성하게 하지 않고, 답변 생성과 근거 부착을 분리하는 것이다.

## Key Changes
- 모듈: `src/generation/rfp_generation.py`
  - 질문 유형 분류, field-aware context 조립, prompt 생성, JSON 후처리, deterministic citation 부착, 실패 태그 생성을 담당한다.
- 노트북: `notebooks/rag/rfp_generation_p4_hwpx_quickcheck.ipynb`
  - 상단 설정값만 바꿔 `125`, `250`, `690` corpus에 재사용한다.
  - `MAX_NEW_TOKENS=1024`를 기본값으로 사용한다.
  - 기본은 `GENERATION_DO_SAMPLE=False`이며, 이때 `temperature/top_p/top_k`는 전달하지 않는다.
  - Colab에서 hard error가 확인될 때만 `GENERATION_DO_SAMPLE=True`, `temperature=0.1`, `top_p=0.9`, `top_k=20` fallback을 사용한다.
- 입력 파일 탐색:
  - 1순위: `generation_predictions_J5_hybrid_rrf_rerank_*.jsonl`
  - 2순위: `generation_predictions_*.jsonl`
  - 파일이 없으면 후보 파일 목록을 출력하고 중단한다.

## Generation Design
- 질문 유형은 코드가 자동 분류한다.
  - `budget`, `duration`, `bid_deadline`, `submission_documents`, `submission_logistics`, `eligibility`, `business_type`, `requirements`, `evaluation`, `multi_doc`, `general`
- multi-doc 보강 신호:
  - `두 사업`, `두 문서`, `간의`, `차액`, `합계`, `각각`, `공통`, `모두`, `비교`
  - 예산 차액/합계 질문은 `answer_type=budget`이면서 `is_multi_doc=True`로 처리한다.
- context는 질문 유형별로 다르게 조립한다.
  - fact 질문: `fact_candidates`와 짧은 evidence 중심
  - 요약/요구사항/평가기준 질문: 섹션별 `fact/table/text` block을 제한적으로 추가
  - multi-doc 질문: `source_file`별로 근거가 분산되도록 구성
- 기간은 반드시 분리한다.
  - `project_duration`
  - `submission_deadline`
  - `submission_period`
  - `bid_deadline`
  - `maintenance_period`
  - `warranty_period`
  - `other_deadline`

## Output Schema And Post-processing
- LLM이 직접 생성하는 JSON은 짧게 유지한다.

```json
{
  "answer": "string",
  "answer_type": "budget|duration|bid_deadline|submission_documents|submission_logistics|eligibility|business_type|requirements|evaluation|summary|multi_doc_comparison|general|unknown",
  "confidence": "high|medium|low",
  "is_answerable": true,
  "final_values": {},
  "documents": [],
  "missing_info": [],
  "warnings": []
}
```

- LLM은 `citations.evidence_text`를 직접 생성하지 않는다.
- citation은 후처리 코드가 `context_package["evidence_blocks"]`에서 자동 부착한다.
- 자동 citation은 `evidence_id`, `source_file`, `chunk_id`, 짧은 `evidence_text`를 포함한다.
- `document_identity`, `answer_policy=route_only_not_final_answer`, `backfilled=True` 근거는 최종 citation 우선순위를 낮춘다.
- JSON이 잘렸더라도 raw text 안의 `answer` 필드가 있으면 복구한다.
  - `_valid_json=False`
  - `_recovered_answer=True`
  - `_parse_error_type=truncated_json`
  - `warnings`에 `answer_recovered_from_raw`를 남긴다.

## Answer Policy Guard
- 예산 질문에서는 다음 근거를 우선한다.
  - `project_budget`
  - `estimated_price`
  - `base_amount`
  - `budget_answer_enabled=True`
- `threshold_budget`, `payment_terms`는 사업예산 최종값으로 쓰지 않는다.
- 단, 입찰자격/지급조건 질문에서는 해당 fact를 사용할 수 있다.
- 예산 질문에서 금지된 fact 값을 최종 답변에 사용하면 `wrong_field_selection` 실패 태그를 남긴다.

## Outputs
- 기본 generation 산출물:
  - `generated_answers.jsonl`
  - `review_samples.csv`
  - `metrics_summary.json`
  - `failure_tags_summary.json`
  - `ragas_eval_input.jsonl`
  - `ragas_metrics_summary.json`
  - `ragas_per_question.csv`
  - `generation_contexts.jsonl`
  - `run_config.json`
- 답변 형성 과정 검토용 산출물:
  - `llm_answer_review.csv`
  - `llm_answer_review.html`
- `llm_answer_review`에는 다음을 포함한다.
  - `question_id`
  - `question`
  - `ground_truth`
  - `ground_truth_docs`
  - `raw_llm_text`
  - `parsed_answer`
  - `final_answer`
  - `valid_json`
  - `recovered_answer`
  - `parse_error_type`
  - `failure_tags`

## Metrics And Diagnostics
- 기본 요약 지표:
  - `valid_json_rate`
  - `answer_available_rate`
  - `empty_answer_rate`
  - `recovered_answer_rate`
  - `citation_valid_rate`
  - `numeric_grounded_rate`
  - `answerable_rate`
  - `generation_ms_avg`
- 실패 태그:
  - `retrieval_missing`
  - `context_building_error`
  - `wrong_field_selection`
  - `llm_invalid_json`
  - `llm_hallucination_risk`
  - `incomplete_multi_doc`
  - `insufficient_evidence`

## RAGAS Handling
- RAGAS는 이번 generation 수정의 핵심이 아니므로 선택 실행으로 유지한다.
- 답변이 있는 row만 평가하고, skipped row 수를 반드시 출력한다.
- `gpt-5-nano`는 현재 RAGAS/LangChain 조합에서 temperature 처리 충돌 가능성이 있으므로, RAGAS smoke 모델은 `gpt-4o-mini`를 권장한다.
- RAGAS 결과는 답변 보정에 사용하지 않고 품질 진단 보조 지표로만 사용한다.

## Memory Plan
- retrieval과 generation을 같은 Colab 런타임에서 이어서 실행할 경우:
  - retrieval 결과를 먼저 파일로 저장한다.
  - embedding model, reranker, Chroma client 참조를 삭제한다.
  - `gc.collect()`와 `torch.cuda.empty_cache()`를 실행한다.
  - 그 다음 LLM을 로드한다.
- 가장 안전한 기본값은 retrieval 노트북과 generation 노트북을 별도 런타임에서 실행하는 것이다.
- OOM fallback:
  - `GENERATION_SAMPLE_SIZE=10`
  - `MAX_CONTEXT_CHARS=6000`
  - `MAX_NEW_TOKENS=512`
  - 그래도 안 되면 `Qwen/Qwen2.5-1.5B-Instruct`로 smoke만 확인한다.

## Test Plan
- smoke 5문항:
  - empty answer 0개 목표
  - invalid JSON이어도 answer가 복구되는지 확인한다.
- review50:
  - 기존 기준선: empty answer 26/50
  - 수정 후 목표: empty answer 5개 이하
  - recovered answer 수를 별도 집계한다.
  - `llm_invalid_json`이 곧바로 빈 답변으로 이어지지 않아야 한다.
- 핵심 QID 확인:
  - `Q005`: 긴 요약 답변이 비어 있지 않아야 한다.
  - `Q008`: multi-doc budget 차액 질문으로 분류되어야 한다.
  - `Q039`: `threshold_budget=80억원`을 사업예산으로 오인하지 않아야 한다.
  - `Q167`, `Q290`: multi-doc 문서 누락 여부를 진단한다.
- 노트북 검증:
  - `.ipynb` JSON 파싱 성공
  - 주요 코드 셀 AST 파싱 성공
  - 한글 물음표 깨짐, mojibake, 긴 traceback 잔존 여부 확인

## Assumptions
- corpus는 `parsing_p4_hwpx_125_datafix_recallguard`를 유지한다.
- 팀원 공유 기본값은 계속 `USE_SOURCE_STORE=False`이다.
- source store 파일이 없어도 generation은 동작해야 한다.
- retrieval 성능 개선과 query rewrite는 별도 실험으로 분리한다.


## Failure-Driven Revision Scope (2026-05-25)
- review50 결과에서 실패 태그 20건과 `missing_info` 중심 케이스까지 포함해 총 24건을 분석 대상으로 삼는다.
- Q008, Q128, Q147, Q167, Q290, Q348처럼 정답 문서는 source에 있으나 다른 문서의 값/citation이 선택되는 문제를 막기 위해 `target_slots`와 target-aware citation ranking을 추가한다.
- Q166, Q186, Q326, Q386, Q486처럼 질문 안에 숫자와 계산 조건이 명시된 경우 LLM 계산에 맡기지 않고 deterministic numeric layer가 차액, 합계, 비율, 잔액, 월 단가를 계산한다.
- Q057, Q141, Q305, Q356, Q437처럼 "문서에 없음"이 답인 경우 `answer_status=not_found_in_context`로 관리하고, 확인한 근거를 `checked_citations` 성격의 deterministic citation으로 남긴다.
- Q100, Q214, Q453처럼 예산과 요약/비교/성격 설명이 섞인 질문은 `intent_slots`를 복수로 유지하여 예산만 답하는 일을 막는다.
- Q191, Q249, Q369, Q416, Q423처럼 multi-doc coverage가 불완전한 경우 `target_doc_coverage_missing`, `incomplete_multi_doc`, `citation_wrong_target`을 분리 진단한다.

## Target Slots And Intent Slots
- `target_slots`: 질문의 따옴표 사업명, 기관명+사업명 표현을 추출해 각 target별 `matched_source_file`, `match_score`, `missing_fields`를 기록한다.
- `intent_slots`: `budget_lookup`, `budget_difference`, `budget_sum`, `budget_ratio`, `purpose_summary`, `requirements_summary`, `negative_check`, `multi_doc_comparison`을 복수로 유지한다.
- `intent_plan`: `intent_slots`를 사람이 읽을 수 있는 실행 계획으로 확장한다. 각 intent마다 `answer_section`, `targets`, `target_policy`, `required_fact_types`, `preferred_chunk_types`, `requires_computation`, `requires_all_targets`, `classification_signals`를 기록한다.
- 예: Q100류 질문은 `budget_lookup`과 `purpose_summary`가 각각 `예산`, `핵심 요약` answer section으로 분리된다. Q005류 질문은 `requirements_summary`와 `requirements_list`가 분리되어 목록 누락을 점검할 수 있다.
- `intent_plan`은 LLM에게 그대로 전달되어 "한 문장 안의 하위 요청을 모두 답해야 한다"는 실행 지시로 사용하고, 후처리에서는 `_missing_intents`로 누락 intent를 기록한다.
- target에 맞지 않는 같은 기관의 다른 사업 예산은 최종 예산 후보에서 감점하고, target 문서에서 값을 못 찾으면 다른 문서 값으로 대체하지 않는다.
- retrieval 결과 chunk만 보지 않고, 검색된 `source_file`와 같은 문서의 `document_identity`, `document_summary`, `project_budget` 등 fact 후보를 `chunks_v2`에서 추가 로드한다. 단 `source_store`는 계속 사용하지 않는다.
- 예산 intent에서는 각 target 문서에 `project_budget` 계열 fact가 있는지 `missing_fields`로 표시한다. 없으면 같은 발주기관의 다른 사업 예산을 끌어오지 않고 `source_numeric_missing` 또는 `insufficient_context`로 진단한다.

## Deterministic Numeric Layer
- 질문 안에 명시된 금액, 억/억원/만원/천원/원 단위, %, N분의 M, 인원 수, 개월 수, 개수 정보를 코드가 파싱한다.
- 차액/합계/비율/잔액/월 단가 계산 결과는 `computed_values`로 context와 output에 저장한다.
- LLM은 `computed_values`를 변경하지 않고 문장화만 한다.
- 기존 `numeric_grounded_rate`는 유지하되, `source_numeric_grounded_rate`와 `derived_numeric_valid_rate`를 추가해 원문 숫자 근거와 파생 계산값을 분리 평가한다.

## Expanded Failure Tags
- 추가 태그: `wrong_target_field_selection`, `derived_numeric_mismatch`, `source_numeric_missing`, `negative_answer_no_checked_evidence`, `multi_intent_incomplete`, `target_doc_coverage_missing`, `citation_wrong_target`.
- 기존 `llm_hallucination_risk`, `incomplete_multi_doc`, `wrong_field_selection`은 유지하되 더 구체적인 태그와 함께 기록한다.

## Regression Checks
- Q008은 target 문서에 예산 fact가 없으면 같은 기관의 다른 예산을 쓰지 말고 `source_numeric_missing` 또는 `insufficient_context`로 멈춰야 한다. corpus에 정답 예산 fact가 들어오면 차액은 `1,145,940,000원`이어야 한다.
- Q057은 `answer_status=not_found_in_context`이고 hallucination risk로 집계되지 않아야 한다.
- Q100은 `budget_lookup + purpose_summary`로 처리되어 예산과 R&D/현장/팩토리 아웃풋 요약을 모두 답해야 한다.

## Failure-Driven Patch Round 2 (2026-05-25)
- 이번 수정은 review50 실제 실패 사례를 바탕으로 한 generation 방어 로직 보강이다.
- `QUESTION_KEYWORDS["budget"]`에서 `"원"` 단독 키워드를 제거한다. `한국수자원공사`처럼 기관명에 포함된 글자 때문에 예산 질문으로 오분류되는 위험을 줄이기 위함이다.
- 금액 정규식이 질문에 있고 `계산`, `합산`, `차액`, `비율`, `단가`, `월급`, `액수` 같은 연산 신호가 있을 때만 예산 intent를 추가한다.
- `budget_difference`, `budget_sum`, `budget_ratio` 질문에서 `computed_values`가 있으면 LLM이 생성한 숫자 답변을 보조하지 않고 deterministic 계산 결과로 대체한다.
- 단, `budget_lookup + purpose_summary`처럼 요약 의도가 함께 있는 질문은 계산값만으로 덮어쓰지 않고 `예산 / 핵심 요약 / 근거` 섹션을 유지한다.
- Q100 같은 복합 질문은 prompt에서 `예산:`, `핵심 요약:`, `근거:` 형식을 요구한다.
- Q008 같은 source numeric missing 케이스는 정답을 억지로 만들지 않는다. target 문서의 예산 fact가 없으면 같은 발주기관의 다른 사업 예산을 쓰지 않고 missing으로 남긴다.

## Round 2 Success Criteria
- `valid_json_rate == 1.0`
- `empty_answer_count == 0`
- `derived_numeric_valid_rate == 1.0`
- `numeric_grounded_rate >= 0.85`
- Q008: `495,000,000원`을 용인 사업 예산으로 사용하지 않아야 한다.
- Q057: 예산 intent가 붙지 않아야 하며, `not_found_in_context` 계열로 처리되어야 한다.
- Q100: 예산뿐 아니라 핵심 요약이 포함되어야 한다.
- Q326/Q386/Q486: LLM 계산값이 아니라 코드 계산값이 최종 답변에 반영되어야 한다.
