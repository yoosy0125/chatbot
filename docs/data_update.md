# P4 목표 보정(goalfix) 데이터 업데이트 안내

핵심은 데이터가 단순히 더 많아진 것이 아니라, 질문에 맞게 더 정확히 해석되도록 바뀌었다는 점입니다.

기존 데이터에서도 검색은 어느 정도 됐지만, 생성(generation) 단계에서 숫자나 표 정보를 잘못 해석하는 문제가 있었습니다. 특히 RFP 문서에는 금액이 정말 많이 나오는데, 모든 금액이 같은 의미는 아닙니다.

예를 들어 아래 세 문장은 모두 금액을 포함합니다.

```text
1. 사업예산: 1,515,000천원
2. 최근 3년 이내 단일 실적 2억원 이상 보유
3. 선금은 계약금액의 70% 이내 지급 가능
```

사람이 보면 1번은 실제 사업예산, 2번은 입찰참가자격 기준금액, 3번은 지급조건이라는 걸 구분할 수 있습니다. 그런데 LLM에게 검색된 문장만 그냥 넣으면, 2억원이나 70% 같은 숫자를 실제 사업예산처럼 잘못 답할 수 있습니다.

그래서 이번 목표 보정(goalfix) 버전에서는 금액을 그냥 숫자로만 저장하지 않고, 금액의 의미를 나눠서 저장했습니다.

```text
project_budget   : 실제 사업예산으로 답변에 써도 되는 금액
total_allocation : 전체 배정액 또는 총액 성격의 금액
threshold_budget : 입찰참가자격, 실적 기준 등에 쓰이는 기준금액
payment_terms    : 선금, 중도금, 잔금 같은 지급조건 금액
estimated_price  : 추정가격
base_amount      : 기초금액
```

그리고 최종 예산 답변에 써도 되는 값에는 `budget_answer_enabled=true`를 붙였습니다. 반대로 자격요건 기준금액이나 지급조건 금액은 검색에는 도움이 될 수 있지만, 사업예산 최종 답변에는 쓰면 안 되기 때문에 `budget_answer_enabled=false`로 둡니다.

예를 들면 데이터 한 줄이 이런 식으로 생겼다고 보시면 됩니다.

```json
{
  "content": "사업예산 : 1,515,000천원 | KRW: 1515000000 | budget_type: project_budget",
  "metadata": {
    "source_file": "그랜드코리아레저(주)_2024년도 GKL 그룹웨어 시스템 구축 용역.hwp",
    "chunk_type": "fact_candidates",
    "fact_type": "project_budget",
    "amount_krw": 1515000000,
    "amount_type": "project_budget",
    "answer_policy": "allow_as_project_budget",
    "budget_answer_enabled": true
  }
}
```

이 경우는 사업예산 질문에 최종 답변 근거로 써도 됩니다.

반대로 이런 데이터도 있을 수 있습니다.

```json
{
  "content": "입찰참가자격 : 최근 3년 이내 단일 실적 2억원 이상",
  "metadata": {
    "fact_type": "threshold_budget",
    "amount_krw": 200000000,
    "amount_type": "threshold_budget",
    "answer_policy": "allow_for_eligibility_exclude_for_project_budget",
    "budget_answer_enabled": false,
    "eligibility_answer_enabled": true
  }
}
```

이 경우 2억원은 중요한 값이지만, 사업예산이 아닙니다. 따라서 “이 사업의 예산은 얼마인가요?”라는 질문에는 쓰면 안 되고, “입찰참가자격 기준은 무엇인가요?” 같은 질문에 써야 합니다.

지급조건도 마찬가지입니다.

```json
{
  "content": "지급조건 : 선금은 계약금액의 70% 이내 지급 가능",
  "metadata": {
    "fact_type": "payment_terms",
    "amount_type": "payment_terms",
    "answer_policy": "allow_for_payment_terms_exclude_for_project_budget",
    "budget_answer_enabled": false,
    "payment_answer_enabled": true
  }
}
```

이건 계약 조건 설명에는 필요하지만, 사업예산 답변에는 쓰면 안 됩니다.

중요한 점은 이 key들이 데이터에 들어 있다고 해서 LLM이 자동으로 이해하는 것은 아니라는 점입니다. 크로마(Chroma)는 검색 결과로 `content`와 `metadata`를 돌려줄 뿐입니다. 그 다음에는 우리 코드가 metadata를 읽어서 질문 유형에 맞는 근거만 골라야 합니다.

흐름은 이렇게 보시면 됩니다.

```text
사용자 질문
-> Chroma 검색
-> content와 metadata 반환
-> context builder가 metadata를 보고 근거 선별
-> 선별된 근거와 규칙을 prompt에 넣음
-> LLM이 답변 생성
```

즉, `answer_policy`는 자동 실행되는 마법 같은 key가 아닙니다. “이 근거를 어떤 질문에서 답변에 써도 되는지 알려주는 신호”입니다.

예를 들어 예산 질문이면 context builder는 이런 식으로 동작해야 합니다.

```python
if question_type == "budget":
    if metadata["budget_answer_enabled"] == True:
        use_as_final_budget_evidence()
    elif metadata["fact_type"] in ["threshold_budget", "payment_terms"]:
        do_not_use_as_project_budget()
```

프롬프트에도 이런 규칙을 같이 넣어주는 게 안전합니다.

```text
[답변 규칙]
- 예산 질문에서는 budget_answer_enabled=true인 근거를 우선 사용한다.
- threshold_budget은 입찰참가자격 기준금액이므로 사업예산으로 답하지 않는다.
- payment_terms는 지급조건이므로 사업예산으로 답하지 않는다.
- amount_krw가 있으면 금액 계산에는 이 정규화 값을 사용한다.
- 근거가 부족하면 확인되지 않는다고 답한다.
```

이렇게 해야 LLM이 “검색된 숫자 아무거나”로 답하지 않고, 우리가 데이터에 넣어둔 의미 구분을 따라가게 됩니다.

이번 보정은 금액만을 위한 것은 아닙니다. 사업범위, 추진배경, 요구사항, 기대효과처럼 고차원 질문에 필요한 정보도 별도 `fact_candidates` 청크로 보강했습니다.

예를 들어 이런 질문이 있다고 해보겠습니다.

```text
이 사업은 어떤 문제를 해결하기 위해 추진되었나요?
```

이 질문은 단순히 사업명이나 기관명만 찾아서는 답하기 어렵습니다. 그래서 `project_background`, `project_scope`, `requirements`, `project_purpose_effect` 같은 fact type을 추가했습니다.

```json
{
  "content": "추진배경: 기존 그룹웨어 노후화로 업무 처리 속도와 협업 효율이 저하되어 신규 시스템 구축이 필요함",
  "metadata": {
    "chunk_type": "fact_candidates",
    "fact_type": "project_background",
    "source_file": "그랜드코리아레저(주)_2024년도 GKL 그룹웨어 시스템 구축 용역.hwp"
  }
}
```

이런 데이터는 예산 계산에는 직접 쓰지 않지만, 사업 배경이나 목적을 묻는 질문에서는 더 좋은 근거가 됩니다.

정리하면 이번 goalfix 데이터의 의도는 세 가지입니다.

```text
1. 금액을 숫자가 아니라 의미 단위로 구분한다.
2. 답변에 써도 되는 금액과 쓰면 안 되는 금액을 metadata로 표시한다.
3. 고차원 질문에 필요한 사업범위, 배경, 요구사항 정보를 검색 가능한 청크로 끌어올린다.
```

검증 결과 125개 기준으로 청크는 22,994개이고, 새로 610개가 보강됐습니다. `chunk_id` 중복은 0건이고, 근거 연결 누락도 0건입니다.

다음 단계는 이 goalfix 데이터를 같은 검색 조건으로 돌려서 기존 recallguard 버전보다 Hit@5, MRR@5, nDCG@5, Doc Recall@5가 어떻게 바뀌는지 확인하는 것입니다.

팀에서 generation prompt를 만들 때는 아래 한 문장만 기억하시면 됩니다.

```text
metadata는 LLM이 자동으로 이해하는 값이 아니라, context builder와 prompt가 반드시 읽고 반영해야 하는 제어 신호입니다.
```
