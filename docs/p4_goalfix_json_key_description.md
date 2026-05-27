# P4 goalfix JSON Key 설명서

`parsing_p4_hwpx_125_datafix_goalfix` 산출물의 JSONL key를 정리한 문서입니다.

이번 버전은 기존 P4/recallguard corpus에 **생성 단계 오류를 줄이기 위한 목표 보정(goalfix)** 을 추가한 버전입니다. 핵심은 검색 결과에 포함된 숫자와 요약 정보를 LLM이 잘못 해석하지 않도록, 금액의 의미와 답변 사용 가능 여부를 metadata에 명시한 것입니다.

## 0. 산출물 개요

| 항목 | 값 |
|---|---|
| corpus_name | `p4_hwpx_125_goalfix` |
| corpus_version | `v2_goalfix_amount_policy` |
| target_output_name | `parsing_p4_hwpx_125_datafix_goalfix` |
| source_output_name | `parsing_p4_hwpx_125_datafix_recallguard` |
| parser/postprocess | `p4_hwpx_goalfix_postprocess_v2026_05_27` |
| 문서 수 | 125개 |
| 기본 retrieval 파일 | `chunks_v2_125.jsonl` |
| 상세 근거 조회 파일 | `source_store_v2_125.jsonl` |
| 검증 리포트 | `validation_report_goalfix.json` |

`jsonl`은 한 줄에 JSON 객체 하나가 들어가는 형식입니다. 파일 전체가 하나의 JSON 배열이 아니라, 각 줄이 독립적인 record입니다.

## 1. 이번 goalfix에서 달라진 점

| 구분 | 변경 내용 |
|---|---|
| 금액 의미 분리 | 모든 금액을 같은 값으로 취급하지 않고 `project_budget`, `threshold_budget`, `payment_terms` 등으로 나눴습니다. |
| 답변 사용 가능 여부 | 사업예산 답변에 써도 되는 금액에는 `budget_answer_enabled=true`를 표시했습니다. |
| 정책 key 추가 | `answer_policy`, `answer_allowed_question_types`, `answer_blocked_question_types`, `answer_risk_level`을 추가했습니다. |
| 고차원 질문 보강 | `project_scope`, `project_background`, `requirements`, `project_purpose_effect` fact chunk를 추가했습니다. |
| document_summary 보호 | 문서 요약 안의 숫자를 최종 예산처럼 쓰지 않도록 `route_only_not_final_answer` 정책을 부여했습니다. |
| Chroma 적재 유지 | Chroma에는 여전히 `ids=chunk_id`, `documents=content`, `metadatas=metadata`로 넣습니다. |

검증 결과:

| 항목 | 값 |
|---|---:|
| input_chunk_count | 22,384 |
| output_chunk_count | 22,994 |
| added_chunk_count | 610 |
| duplicate_chunk_id_count | 0 |
| missing_source_store_ref | 0 |
| chunks_v2 size | 64.11 MiB |

## 2. chunks_v2_125.jsonl 최상위 key

`chunks_v2_125.jsonl`은 Chroma 적재의 기본 입력입니다. 기본적으로 `embed_enabled=true`인 row를 임베딩 대상으로 사용합니다.

| key | 설명 |
|---|---|
| `chunk_id` | chunk 고유 ID입니다. Chroma의 `ids`로 사용합니다. |
| `doc_id` | 파일명 기반 내부 문서 ID입니다. |
| `doc_key` | 확장자와 일부 표기 차이를 줄인 문서 식별명입니다. eval 정답 문서명 매칭에도 중요합니다. |
| `canonical_doc_id` | 재공고/표기 차이가 있는 문서를 묶기 위한 canonical 문서 ID입니다. |
| `canonical_doc_key` | canonical 문서 식별명입니다. |
| `source_file` | 원본 파일명입니다. |
| `source_file_nfc` | 유니코드 정규화된 원본 파일명입니다. |
| `source_format` | 파싱에 사용된 형식입니다. 예: `hwpx`, `pdf` |
| `chunk_type` | chunk 종류입니다. 예: `text`, `table`, `fact_candidates`, `toc` |
| `embed_enabled` | 기본 임베딩 대상 여부입니다. `false`면 Chroma 기본 적재에서 제외하는 것이 안전합니다. |
| `content` | 실제 임베딩/검색에 사용할 텍스트입니다. Chroma의 `documents`로 사용합니다. |
| `metadata` | Chroma metadata로 넣는 짧은 dict입니다. 출처, chunk_type, fact_type, 정책 key가 들어갑니다. |
| `source_ref` | `source_store_v2_125.jsonl`의 상세 근거와 연결하는 참조 key입니다. |
| `fact_type` | `chunk_type='fact_candidates'`일 때 정보 목적을 나타냅니다. |
| `fact_status` | fact 추출 상태입니다. 예: `extracted`, `reference_only` |
| `fact_confidence` | fact 신뢰도입니다. 예: `high`, `medium` |
| `evidence_id` | generation 또는 정성평가에서 근거를 식별하기 위한 짧은 ID입니다. |
| `evidence_text_short` | fact 판단의 짧은 근거 문장입니다. 긴 원문은 `source_store`에서 확인합니다. |

## 3. Chroma 적재 매핑

Chroma 적재 시 key 매핑은 아래처럼 보면 됩니다.

```python
ids = [row["chunk_id"] for row in rows]
documents = [row["content"] for row in rows]
metadatas = [row["metadata"] for row in rows]

collection.add(
    ids=ids,
    documents=documents,
    metadatas=metadatas,
)
```

주의할 점:

- `content`는 검색용 텍스트입니다.
- `metadata`는 필터링과 generation context 선택을 위한 짧은 값입니다.
- 긴 원문, 긴 표 구조, nested dict/list는 Chroma metadata에 넣지 않습니다.
- `metadata` 안의 boolean 값은 실행 환경에 따라 문자열 `"True"`, `"False"`로 들어올 수 있습니다. 코드에서는 `True`와 `"True"`를 모두 처리하는 것이 안전합니다.

예:

```python
def is_true(value):
    return value is True or str(value).lower() == "true"

if is_true(metadata.get("budget_answer_enabled")):
    # 사업예산 답변 근거로 사용 가능
    ...
```

## 4. chunk_type 값

| 값 | 설명 | 기본 사용 |
|---|---|---|
| `text` | 표가 아닌 일반 본문 문단 기반 chunk입니다. | 일반 검색 근거 |
| `table` | HWPX/PDF에서 추출한 표 기반 chunk입니다. | 표 안의 요구사항, 평가기준, 제출서류, 예산 정보 검색 |
| `fact_candidates` | 문서에서 추출한 핵심 후보 정보 chunk입니다. | 금액/기간/제출/자격/사업범위 등 목적별 검색 |
| `toc` | 목차 chunk입니다. | 구조 보존용, 기본 임베딩 제외 권장 |

현재 goalfix 검증 기준:

| chunk_type | row 수 |
|---|---:|
| `fact_candidates` | 1,705 |
| `table` | 15,481 |
| `text` | 5,754 |
| `toc` | 54 |

## 5. fact_type 값

`fact_candidates`는 검색 목적별로 나뉜 핵심 청크입니다.

| fact_type | 설명 | 질문 예시 |
|---|---|---|
| `document_identity` | 원본문서명, 정규화 문서명, 사업명, 발주기관, alias를 묶은 식별용 chunk입니다. | “이 문서 찾아줘”, “어느 기관 사업이야?” |
| `document_summary` | 문서 전체 핵심 신호를 요약한 chunk입니다. 라우팅에는 좋지만 최종 답변 근거로는 조심해야 합니다. | “이 사업 대략 뭐야?” |
| `project_budget` | 실제 사업예산으로 답변에 쓸 수 있는 금액 chunk입니다. | “예산이 얼마야?” |
| `total_allocation` | 전체 배정액 또는 총액 성격의 금액입니다. | “총 배정액은?” |
| `estimated_price` | 추정가격입니다. 실제 사업예산과 다를 수 있습니다. | “추정가격은?” |
| `base_amount` | 기초금액입니다. 사업예산과 구분해야 합니다. | “기초금액은?” |
| `threshold_budget` | 입찰참가자격, 실적 기준 등에 쓰이는 기준금액입니다. | “최근 3년 실적 기준은?” |
| `payment_terms` | 선금, 중도금, 잔금 등 지급조건 관련 금액입니다. | “지급조건은?” |
| `project_duration` | 사업기간/수행기간입니다. | “사업기간은?” |
| `maintenance_period` | 무상유지보수기간입니다. | “유지보수기간은?” |
| `warranty_period` | 하자담보책임기간입니다. | “하자보증기간은?” |
| `deadline_term` | 계약 후 N일 이내, 제출 후 N일 이내 같은 기간 조건입니다. | “착수계 제출 기한은?” |
| `bid_deadline` | 입찰마감일 또는 제출마감일입니다. | “입찰 마감일은?” |
| `submission_documents` | 제출서류명 목록입니다. | “제출서류는?” |
| `submission_logistics` | 제출방법, 제출장소, 제출처 관련 정보입니다. | “어디로 어떻게 제출해?” |
| `eligibility` | 입찰참가자격, 공동수급, 실적, 인증 등입니다. | “참가자격은?” |
| `business_type` | 구축/운영/유지관리/고도화/보안/클라우드 등 사업유형입니다. | “사업유형은?” |
| `project_background` | 사업 추진 배경입니다. | “왜 이 사업을 하나?” |
| `project_scope` | 사업범위/과업범위입니다. | “어디까지 구축해?” |
| `requirements` | 기능/성능/보안/데이터 등 요구사항입니다. | “요구사항은?” |
| `project_purpose_effect` | 목적, 기대효과, 개선효과입니다. | “기대효과는?” |
| `reference_amount` | 의미가 확정되지 않은 참고 금액입니다. 최종 예산 답변에는 주의가 필요합니다. | 일반 참고 |

## 6. 금액 관련 key

이번 goalfix에서 가장 중요한 영역입니다.

| key | 설명 |
|---|---|
| `amount_raw` | 원문에서 발견된 금액 표현입니다. 예: `1,515,000천원` |
| `amount_krw` | 원화 기준 숫자형 정규화 금액입니다. 예: `1515000000` |
| `amount_unit` | 원문 단위입니다. 예: `원`, `천원`, `백만원` |
| `amount_type` | 금액의 의미입니다. 예: `project_budget`, `threshold_budget`, `payment_terms` |
| `budget_type` | `amount_type`과 같은 용도로 쓰는 예산 분류값입니다. |
| `budget_answer_enabled` | 사업예산 질문의 최종 답변 근거로 써도 되는지 여부입니다. |

예를 들어 아래 세 문장은 모두 금액을 포함하지만 의미가 다릅니다.

```text
1. 사업예산: 1,515,000천원
2. 최근 3년 이내 단일 실적 2억원 이상 보유
3. 선금은 계약금액의 70% 이내 지급 가능
```

해석:

| 문장 | amount_type | 사업예산 답변 사용 |
|---|---|---|
| 사업예산: 1,515,000천원 | `project_budget` | 가능 |
| 단일 실적 2억원 이상 | `threshold_budget` | 불가. 자격요건 답변에 사용 |
| 선금 70% 이내 | `payment_terms` | 불가. 지급조건 답변에 사용 |

## 7. answer_policy 계열 key

`answer_policy`는 LLM이 자동으로 지키는 값이 아닙니다. 검색 결과를 prompt에 넣기 전에 context builder가 읽고 반영해야 하는 제어 신호입니다.

| key | 설명 |
|---|---|
| `answer_policy` | 이 근거를 어떤 답변에 사용할 수 있는지 나타내는 정책 이름입니다. |
| `answer_allowed_question_types` | 사용 가능한 질문 유형입니다. 문자열로 저장됩니다. |
| `answer_blocked_question_types` | 사용하면 안 되는 질문 유형입니다. 문자열로 저장됩니다. |
| `answer_risk_level` | 답변 근거로 사용할 때의 위험도입니다. 예: `low`, `medium`, `high` |
| `budget_answer_enabled` | 예산 질문에서 최종 사업예산 근거로 사용할 수 있는지 여부입니다. |
| `eligibility_answer_enabled` | 입찰참가자격 질문에 사용할 수 있는지 여부입니다. |
| `payment_answer_enabled` | 지급조건 질문에 사용할 수 있는지 여부입니다. |
| `retrieval_role` | 검색에서 맡는 역할입니다. 예: `typed_budget_signal`, `document_identity_anchor` |

대표 policy:

| answer_policy | 의미 |
|---|---|
| `allow_as_project_budget` | 사업예산 답변의 최종 근거로 사용 가능 |
| `allow_as_secondary_budget_only` | 추정가격/기초금액 등 보조 예산 정보로만 사용 |
| `allow_for_eligibility_exclude_for_project_budget` | 입찰참가자격에는 사용 가능, 사업예산 답변에는 사용 금지 |
| `allow_for_payment_terms_exclude_for_project_budget` | 지급조건에는 사용 가능, 사업예산 답변에는 사용 금지 |
| `route_only_not_final_answer` | 검색 라우팅/문서 식별에는 도움되지만 최종 답변 근거로는 사용 주의 |

예산 질문용 context 선택 예:

```python
def is_true(value):
    return value is True or str(value).lower() == "true"

def pick_budget_context(retrieved_rows):
    selected = []
    for row in retrieved_rows:
        meta = row["metadata"]

        if is_true(meta.get("budget_answer_enabled")):
            selected.append(row)
            continue

        if meta.get("fact_type") in ["threshold_budget", "payment_terms"]:
            # 입찰자격 기준금액/지급조건 금액은 사업예산 최종 답변에서 제외
            continue

    return selected
```

prompt에 같이 넣을 규칙 예:

```text
- 예산 질문에서는 budget_answer_enabled=true인 근거를 우선 사용한다.
- threshold_budget은 입찰참가자격 기준금액이므로 사업예산으로 답하지 않는다.
- payment_terms는 지급조건이므로 사업예산으로 답하지 않는다.
- amount_krw가 있으면 금액 계산에는 이 정규화 값을 사용한다.
- 근거가 부족하면 확인되지 않는다고 답한다.
```

## 8. metadata 내부 key

`metadata`는 Chroma metadata로 들어가는 짧은 값입니다.

| key | 설명 |
|---|---|
| `doc_id`, `doc_key` | 문서 식별 정보입니다. |
| `canonical_doc_id`, `canonical_doc_key` | 재공고/표기 차이를 묶기 위한 canonical 문서 정보입니다. |
| `source_file`, `source_file_nfc` | 원본 파일명과 정규화 파일명입니다. |
| `source_format`, `file_type` | 파싱 형식과 파일 타입입니다. |
| `evidence_id` | generation 근거 식별용 ID입니다. |
| `chunk_type` | chunk 종류입니다. |
| `section_path` | 문서 내 섹션 경로입니다. |
| `section_type` | RFP 도메인 기준 섹션 분류입니다. |
| `issuer` | 발주기관명입니다. |
| `project_name` | 사업명입니다. |
| `fact_type`, `fact_status`, `fact_confidence` | fact chunk의 목적, 상태, 신뢰도입니다. |
| `amount_*`, `budget_*` | 금액 정규화 및 예산 정책 key입니다. |
| `answer_*` | generation 답변 사용 정책 key입니다. |
| `table_role`, `table_signal_score`, `table_embed_reason` | table chunk의 검색 가치와 embed 판단 근거입니다. |

주의:

- `metadata`는 Chroma filtering과 context 선택을 위한 값입니다.
- 긴 원문, 표 전체 구조, OCR 전문, nested dict/list는 metadata에 넣지 않는 것이 안전합니다.
- 상세 원문 확인은 `source_ref.source_store_id`로 `source_store_v2_125.jsonl`을 조회합니다.

## 9. source_ref 내부 key

| key | 설명 |
|---|---|
| `source_store_id` | `source_store_v2_125.jsonl`의 `source_store_id`와 연결되는 key입니다. |
| `block_id` | chunk가 만들어진 원본 block ID입니다. |
| `part_index` | 하나의 block이 여러 chunk로 쪼개졌을 때 몇 번째 조각인지 나타냅니다. |
| `content_hash` | content 기반 hash입니다. |
| `evidence_id` | 근거 식별용 ID입니다. |

검색 결과의 원문 근거를 더 길게 보고 싶으면 `source_store_id`를 기준으로 `source_store_v2_125.jsonl`에서 찾아보면 됩니다.

## 10. source_store_v2_125.jsonl key

`source_store_v2_125.jsonl`은 Chroma에 직접 넣기 위한 파일이 아니라, 검색 결과의 상세 원문/표 구조를 확인하기 위한 참조 파일입니다.

| key | 설명 |
|---|---|
| `source_store_id` | source block 고유 ID입니다. |
| `doc_id`, `doc_key`, `source_file`, `source_format` | 문서 식별 정보입니다. |
| `source_type` | 원본 block 종류입니다. 예: `text`, `table`, `fact_candidates`, `toc` |
| `full_text` | chunk보다 긴 원문 또는 fact/table 원문입니다. |
| `section_path` | 원문 block의 섹션 경로입니다. |
| `block_id` | 원본 block ID입니다. |
| `content_hash` | 원문 content hash입니다. |
| `table_structure` | table block일 때 행/열, 병합 셀, row type 등 표 구조 정보입니다. |

`source_store`를 모든 generation에서 무조건 조회할 필요는 없습니다. 기본 답변은 Chroma가 반환한 `content + metadata`로 구성하고, 표 원형 확인이나 정성평가가 필요할 때만 `source_store`를 조회하는 방식이 가볍습니다.

## 11. generation prompt에서 사용하는 방법

검색 결과를 LLM에 그대로 넣기보다, 질문 유형별로 context를 선별한 뒤 넣는 것이 안전합니다.

| 질문 유형 | 우선 근거 | 제외/주의 근거 |
|---|---|---|
| 사업예산 | `budget_answer_enabled=true`, `fact_type=project_budget`, `amount_krw` | `threshold_budget`, `payment_terms`, `document_summary` 숫자 |
| 예산 합산/차액 | `amount_krw`, `source_file`, `fact_type` | LLM 자체 계산 |
| 입찰참가자격 | `fact_type=eligibility`, `threshold_budget`, `eligibility_answer_enabled=true` | `project_budget`만 단독 사용 |
| 지급조건 | `payment_terms`, `payment_answer_enabled=true` | 사업예산으로 오해 |
| 사업범위/요구사항 | `project_scope`, `requirements`, `table` | 문서 식별용 `document_identity`만 사용 |
| 추진배경/기대효과 | `project_background`, `project_purpose_effect` | 사업명/기관명만 사용 |

## 12. 예시 record

### 12-1. 사업예산으로 사용 가능한 금액

```json
{
  "content": "사업예산 : 1,515,000천원 | KRW: 1515000000 | budget_type: project_budget",
  "metadata": {
    "chunk_type": "fact_candidates",
    "fact_type": "project_budget",
    "amount_krw": 1515000000,
    "amount_type": "project_budget",
    "answer_policy": "allow_as_project_budget",
    "budget_answer_enabled": true
  }
}
```

### 12-2. 사업예산으로 쓰면 안 되는 입찰자격 기준금액

```json
{
  "content": "입찰참가자격 : 최근 3년 이내 단일 실적 2억원 이상",
  "metadata": {
    "chunk_type": "fact_candidates",
    "fact_type": "threshold_budget",
    "amount_krw": 200000000,
    "amount_type": "threshold_budget",
    "answer_policy": "allow_for_eligibility_exclude_for_project_budget",
    "budget_answer_enabled": false,
    "eligibility_answer_enabled": true
  }
}
```

### 12-3. 사업예산으로 쓰면 안 되는 지급조건 금액

```json
{
  "content": "지급조건 : 선금은 계약금액의 70% 이내 지급 가능",
  "metadata": {
    "chunk_type": "fact_candidates",
    "fact_type": "payment_terms",
    "amount_type": "payment_terms",
    "answer_policy": "allow_for_payment_terms_exclude_for_project_budget",
    "budget_answer_enabled": false,
    "payment_answer_enabled": true
  }
}
```

## 13. 해석 시 주의사항

1. `answer_policy`는 자동 실행되는 값이 아닙니다. context builder와 prompt에서 명시적으로 읽고 반영해야 합니다.
2. `budget_answer_enabled=false`인 금액도 검색에는 도움이 될 수 있습니다. 다만 사업예산 최종 답변에는 사용하면 안 됩니다.
3. `document_summary`는 검색 라우팅에는 유용하지만, 그 안의 숫자를 최종 답변으로 바로 쓰면 위험합니다.
4. 다중문서 질문에서는 같은 문서의 table/text/fact가 top5를 독점하지 않도록 final selection에서 문서 다양성을 확인해야 합니다.
5. `amount_krw`는 계산용 정규화 값입니다. 답변 문장에서는 원문 표현과 함께 확인하는 것이 안전합니다.
6. `source_store`는 Chroma DB가 아닙니다. Chroma metadata의 `source_store_id`로 연결되는 상세 근거 조회 파일입니다.
