# P4 Corpus Retrieval-Relaxed Policy Plan

## 목적

기존 `parsing_p4_hwpx_125_datafix`는 사업금액 오답을 줄이기 위해 `threshold_budget`, `payment_terms` 같은 위험 fact를 임베딩에서 제외했다. 이 방식은 generation의 오답 위험을 낮추지만, 자격요건/지급조건 질문이나 오타 질문에서는 retrieval recall을 낮출 수 있다.

이번 수정은 “검색은 넓게, 답변은 질문 유형별로 제한”하는 구조로 바꾼다.

## 핵심 정책

- 기존 `parsing_p4_hwpx_125_datafix` 폴더는 덮어쓰지 않는다.
- 새 산출물 폴더는 `outputs/parsing_p4_hwpx_125_datafix_relaxed`를 사용한다.
- `threshold_budget`은 retrieval에 포함하되, 사업금액 답변에는 사용하지 않는다.
- `threshold_budget`은 자격요건/실적 기준/대기업 참여 제한 질문에서 사용할 수 있다.
- `payment_terms`는 retrieval에 포함하되, 사업금액 답변에는 사용하지 않는다.
- `payment_terms`는 계약 대금 지급조건 질문에서 사용할 수 있다.
- `project_budget`, `estimated_price`, `base_amount`만 final 사업금액 후보로 유지한다.

## Metadata 추가

fact chunk에 아래 metadata를 추가한다.

- `retrieval_role`
- `answer_policy`
- `answer_allowed_question_types`
- `answer_blocked_question_types`
- `answer_risk_level`
- `budget_answer_enabled`
- `eligibility_answer_enabled`
- `payment_answer_enabled`

## 기대 효과

- 자격요건 질문에서 실적 금액 기준을 검색할 수 있다.
- 지급조건 질문에서 선금/잔금 조건을 검색할 수 있다.
- 사업금액 질문에서는 `budget_answer_enabled=false`인 fact를 context builder가 제외할 수 있다.
- retrieval hit/recall과 generation faithfulness를 동시에 관리할 수 있다.

## 검증 기준

- 125개 문서 파싱 성공
- eval physical source docs 40개 포함 유지
- `chunk_id`, `evidence_id`, `canonical_doc_id`, `source_file_nfc` 결측 0
- `threshold_budget`, `payment_terms` fact가 `embed_enabled=true`로 살아나는지 확인
- 해당 fact의 `budget_answer_enabled=false` 확인
- `low_confidence_fact_embedded_count=0` 유지
- 기존 `parsing_p4_hwpx_125_datafix` 산출물은 수정하지 않음
