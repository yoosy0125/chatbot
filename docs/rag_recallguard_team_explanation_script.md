# RFP JSON Corpus 설명 대본

이 문서는 `rag_recallguard_one_page.html`을 팀원들에게 설명할 때 사용할 수 있는 발표/공유용 대본입니다.  
그대로 읽어도 되고, 말투만 조금 바꿔서 사용해도 됩니다.

---

## 0. 시작 멘트

여러분, 이제 retrieval 결과를 바탕으로 generation 단계로 넘어가도 될 것 같습니다.

그런데 generation을 할 때 단순히 검색된 chunk text만 LLM에게 던져주는 방식도 가능하지만, 저희가 만든 corpus에는 이미 문서 정보와 답변 후보 정보가 JSON key로 꽤 많이 구조화되어 있습니다.

그래서 이 key들을 잘 활용하면 LLM이 긴 문서 안에서 알아서 찾게 하는 것보다 더 안정적으로 context를 만들어 줄 수 있습니다.  
오늘 공유드리는 HTML 문서는 이 JSON 구조가 왜 필요한지, 어떤 key가 있고, generation에서 어떻게 쓸 수 있는지 설명하기 위한 자료입니다.

---

## 1. 이 데이터의 핵심 아이디어

가장 중요한 문장은 이겁니다.

> 검색은 넓게, 답변은 엄격하게.

RAG에서 가장 치명적인 문제는 두 가지입니다.

첫 번째는 정답 문서를 아예 못 가져오는 것입니다.  
두 번째는 문서는 가져왔는데, 그 안에서 잘못된 숫자나 잘못된 문장을 답변으로 쓰는 것입니다.

예를 들어 RFP 문서에는 `10억`이라는 숫자가 나와도 그게 실제 사업예산일 수도 있고, 입찰 참가 자격의 실적 기준일 수도 있고, 가격제안서 서식에 적는 예시 금액일 수도 있습니다.

그래서 저희 데이터는 검색할 때는 여러 후보를 넓게 잡되, 최종 답변에 사용할 수 있는 값인지는 `answer_policy`나 `budget_answer_enabled` 같은 key로 한 번 더 제한하는 구조입니다.

---

## 2. RFP 문서가 어려운 이유

RFP 문서는 일반 보고서처럼 한 문단에 정보가 깔끔하게 정리되어 있지 않습니다.

예산은 앞쪽 사업개요에 있을 수도 있고, 표 안에 있을 수도 있고, 별지나 가격제안서 서식 근처에도 비슷한 숫자가 나올 수 있습니다.

제출서류도 마찬가지입니다.  
본문에 한 번 나오고, 표에 한 번 나오고, 별지 서식 목록에 다시 나오는 경우가 많습니다.

기간도 하나가 아닙니다.

- 사업기간
- 입찰마감일
- 제안서 제출기한
- 무상유지보수기간
- 하자담보책임기간

이런 값들이 모두 “기간”처럼 보이지만, 질문에 따라 답해야 하는 값은 다릅니다.

그래서 단순히 문서를 1,000자씩 자르는 방식만으로는 부족하고, RFP에서 자주 묻는 항목들을 별도 key로 정리해 두는 방식이 필요했습니다.

---

## 3. 주목한 RFP 카테고리

저희가 특히 신경 쓴 카테고리는 이런 것들입니다.

- 예산 / 사업금액
- 사업기간 / 일정
- 입찰참가자격
- 제출서류
- 평가기준
- 과업범위
- 유지보수 / 하자담보
- 보안 / 산출물

이 항목들은 eval 질문에서도 자주 나오고, 실제 서비스에서도 사용자가 많이 물어볼 가능성이 높습니다.

예를 들어 사용자가 이렇게 물어볼 수 있습니다.

> 이 사업 예산 얼마야?

또는

> 입찰하려면 어떤 서류를 내야 해?

또는

> 참가 자격에 최근 실적 조건이 있어?

이런 질문에 안정적으로 답하려면, 관련 정보를 JSON에서 구분해 둘 필요가 있습니다.

---

## 4. JSON 구조를 쉽게 설명하면

JSON record 하나는 쉽게 말해서 “검색에 넣을 chunk 하나와 그 chunk의 설명서”입니다.

중요한 큰 덩어리는 세 가지입니다.

첫 번째는 `content`입니다.  
이건 실제로 임베딩에 들어가는 검색 본문입니다.

두 번째는 `metadata`입니다.  
이건 이 chunk가 어떤 문서에서 왔는지, 어떤 종류의 정보인지, 답변에 써도 되는지 알려주는 설명서입니다.

세 번째는 `source_ref`입니다.  
이건 나중에 더 긴 원문이나 표 원형을 찾아보고 싶을 때 사용하는 연결 key입니다.

정리하면:

| 영역 | 쉽게 말하면 | 쓰임 |
|---|---|---|
| `content` | 검색되는 본문 | 임베딩 / retrieval |
| `metadata` | chunk 설명서 | 필터링 / context 조립 / 답변 정책 |
| `source_ref` | 원문 연결 key | 추후 원문 확장 lookup |

---

## 5. 주요 key 설명

팀원분들이 가장 자주 보게 될 key는 이 정도입니다.

`chunk_id`는 chunk의 고유 ID입니다.  
검색 결과와 citation을 연결할 때 씁니다.

`doc_id`, `doc_key`는 문서 단위 ID입니다.  
여러 chunk가 같은 문서에서 나왔는지 묶을 때 씁니다.

`source_file`은 원본 파일명입니다.  
최종 답변에서 출처를 보여줄 때 유용합니다.

`chunk_type`은 chunk의 종류입니다.

대표적으로:

- `text`: 일반 본문
- `table`: 표에서 나온 내용
- `fact_candidates`: 예산, 기간, 제출서류 같은 핵심 후보값
- `toc`: 목차

`embed_enabled`는 임베딩 대상인지 여부입니다.  
`false`면 검색에는 직접 들어가지 않습니다.

다만 JSON에 남겨두는 이유는 검증, 디버깅, 원문 확장에 필요하기 때문입니다.

---

## 6. fact_type 설명

`fact_type`은 이 chunk가 어떤 정보를 담고 있는지 알려주는 라벨입니다.

예를 들어:

| fact_type | 뜻 |
|---|---|
| `project_budget` | 사업예산 |
| `project_duration` | 사업기간 |
| `submission_documents` | 제출서류 |
| `submission_logistics` | 제출 방법, 제출 장소, 제출 기한 |
| `eligibility` | 입찰참가자격 |
| `threshold_budget` | 실적 기준 금액 |
| `payment_terms` | 지급조건 |
| `document_identity` | 문서 식별용 정보 |

여기서 중요한 건 `project_budget`과 `threshold_budget`을 구분하는 것입니다.

둘 다 금액처럼 보이지만 의미가 다릅니다.

`project_budget`은 “이 사업 자체의 예산”입니다.  
반면 `threshold_budget`은 “입찰에 참여하려면 최근 몇 년간 얼마 이상의 실적이 있어야 한다” 같은 자격요건 금액입니다.

예산 질문에서 `threshold_budget`을 답으로 쓰면 오답이 됩니다.

그리고 `fact_candidates`라는 이름 때문에 금액, 서류, 기간이 한 줄에 전부 섞여 들어간다고 오해할 수 있는데, 실제로는 그렇게 이해하면 안 됩니다.

`fact_candidates`는 큰 바구니 이름이고, 그 안에서 다시 `fact_type`으로 나뉩니다.

트리 구조로 보면 이렇게 생각하면 됩니다.

```text
fact_candidates
 ├─ project_budget
 ├─ project_duration
 ├─ submission_documents
 ├─ submission_logistics
 ├─ eligibility
 ├─ payment_terms
 ├─ maintenance_period
 ├─ warranty_period
 └─ document_summary
```

예를 들어 같은 `fact_candidates` chunk라도 의미는 이렇게 달라집니다.

```json
{
  "chunk_type": "fact_candidates",
  "fact_type": "project_budget",
  "content": "사업예산 : 11,270,000,000원"
}
```

```json
{
  "chunk_type": "fact_candidates",
  "fact_type": "project_duration",
  "content": "사업기간 : 계약일로부터 24개월 이내"
}
```

```json
{
  "chunk_type": "fact_candidates",
  "fact_type": "submission_documents",
  "content": "제출서류 : 제안서, 가격제안서, 사업자등록증, 서약서..."
}
```

그래서 generation 단계에서는 질문 유형에 따라 필요한 `fact_type`을 우선 보면 됩니다.

| 질문 | 우선 볼 fact_type |
|---|---|
| “예산 얼마야?” | `project_budget` |
| “사업기간은?” | `project_duration` |
| “제출서류 뭐야?” | `submission_documents` |
| “어디에 언제까지 제출해?” | `submission_logistics` |
| “참가자격은?” | `eligibility` |
| “대금은 어떻게 지급돼?” | `payment_terms` |
| “무상유지보수 기간은?” | `maintenance_period` |
| “하자담보 책임기간은?” | `warranty_period` |

말로 설명할 때는 이렇게 말하면 됩니다.

> `fact_candidates`는 핵심 후보값을 모아둔 큰 묶음이고, 그 안에서 예산인지, 기간인지, 제출서류인지, 자격요건인지는 `fact_type`으로 다시 구분됩니다.

---

## 7. answer_policy가 필요한 이유

`answer_policy`는 이 chunk를 최종 답변 근거로 써도 되는지 알려주는 정책입니다.

예를 들어 사업예산으로 확실한 값은 이렇게 들어갑니다.

```json
{
  "fact_type": "project_budget",
  "answer_policy": "allow_as_project_budget",
  "budget_answer_enabled": true
}
```

이 뜻은:

> 예산 질문에 답할 때 이 값을 써도 된다.

반대로 입찰 자격의 실적 기준 금액은 이렇게 들어갑니다.

```json
{
  "fact_type": "threshold_budget",
  "answer_policy": "allow_for_eligibility_exclude_for_project_budget",
  "budget_answer_enabled": false,
  "eligibility_answer_enabled": true
}
```

이 뜻은:

> 자격요건 질문에는 써도 되지만, 사업예산 질문의 답으로 쓰면 안 된다.

이게 “검색은 넓게, 답변은 엄격하게”의 핵심입니다.

---

## 8. document_identity는 뭐냐

`document_identity`는 답변용 값이 아니라 문서 찾기용 표지판입니다.

예를 들어 이 안에는 이런 정보가 들어갑니다.

- 발주기관
- 사업명
- 파일명
- 공고번호
- 사업유형
- alias

사용자가 질문을 정확히 하지 않아도, 문서 이름이나 기관명과 비슷한 신호를 잡아서 정답 문서를 찾는 데 도움을 줍니다.

하지만 `document_identity` 안에 있는 숫자나 날짜를 최종 답변 근거로 쓰면 안 됩니다.

그래서 정책은 이렇게 되어 있습니다.

```json
{
  "fact_type": "document_identity",
  "answer_policy": "route_only_not_final_answer"
}
```

쉽게 말하면:

> 문서 찾는 데만 쓰고, 최종 답변 근거로는 쓰지 말자.

---

## 9. Generation에서 어떻게 활용하면 좋은가

generation 단계에서 가장 중요한 건 LLM에게 context를 어떻게 넘겨줄지입니다.

가장 단순한 방식은 retrieval된 chunk text를 그대로 이어 붙여서 LLM에게 주는 것입니다.

하지만 저희 데이터는 이미 key가 있으니, 질문 유형에 따라 context를 조금 더 정리해서 줄 수 있습니다.

예를 들어 사용자가 이렇게 물었다고 해보겠습니다.

> 고려대학교 차세대 포털 사업 예산은 얼마야?

그럼 context builder는 먼저 질문을 예산 질문으로 보고, `project_budget`과 `budget_answer_enabled=true`인 근거를 우선 찾아서 LLM에게 앞쪽에 넘겨줄 수 있습니다.

반대로 이런 질문이면:

> 이 사업에 참여하려면 10억 이상 실적이 필요해?

이건 예산 질문이 아니라 자격요건 질문입니다.  
이때는 `eligibility`, `threshold_budget`, `eligibility_answer_enabled=true`인 근거를 봐야 합니다.

즉, LLM에게 모든 걸 맡기는 게 아니라 코드가 먼저 JSON key를 보고 context를 정리해 주는 방식입니다.

---

## 10. 예시 context 설명

HTML 7번에 있는 예시는 이런 의도입니다.

LLM에게 그냥 이렇게 주는 것이 아닙니다.

> 고려대학교 문서 chunk 1  
> 고려대학교 문서 chunk 2  
> 고려대학교 표 chunk 1  
> 알아서 예산 찾아줘

대신 이런 식으로 정리해서 줄 수 있습니다.

```text
[질문]
고려대학교 차세대 포털·학사 정보시스템 구축사업의 예산은 얼마입니까?

[핵심 추출값 요약]
- fact_type: project_budget
- answer_policy: allow_as_project_budget
- budget_answer_enabled: true
- evidence: 사업예산 : 11,270,000,000원

[사용 금지 근거]
- fact_type: threshold_budget
- budget_answer_enabled: false
- 이유: 입찰 자격요건의 실적 기준 금액일 수 있음
```

이렇게 주면 LLM이 잘못된 금액을 답으로 쓸 가능성이 줄어듭니다.

---

## 11. 팀원분들이 기억하면 좋은 점

정리하면 이 데이터는 단순 chunk 파일이 아닙니다.

검색할 때는 `content`를 쓰고,  
검색 결과를 해석할 때는 `metadata`를 보고,  
generation에서 답변 근거를 고를 때는 `fact_type`, `answer_policy`, `*_answer_enabled`를 보면 됩니다.

특히 아래 세 가지는 꼭 기억해 주세요.

1. `document_identity`는 문서 찾기용이지 답변 근거용이 아닙니다.
2. `threshold_budget`은 예산처럼 보여도 사업예산이 아니라 자격요건 금액일 수 있습니다.
3. `submission_documents`와 `eligibility`는 서로 다릅니다. 제출서류와 참가자격을 섞으면 안 됩니다.

---

## 12. 마무리 멘트

이 방식이 유일한 정답은 아닙니다.  
retrieval이나 generation 담당자분들이 다른 방식으로 실험해보셔도 됩니다.

다만 데이터를 만들 때 이런 의도로 key를 설계했기 때문에, generation 단계에서 이 key들을 활용하면 더 안정적인 답변을 만들 수 있을 것 같습니다.

context 조립 방식은 제가 어느 정도 형태를 잡아서 공유드릴 예정이고, 우선 이 문서는 데이터 구조를 이해하기 위한 참고 자료로 봐주시면 됩니다.

---

## 짧은 공유 문구

시간이 없을 때는 아래처럼 짧게 말해도 됩니다.

> 이 corpus는 단순히 RFP 문서를 잘라놓은 파일이 아니라, 예산·기간·제출서류·자격요건 같은 RFP 핵심 정보를 JSON key로 구조화한 데이터입니다.  
> retrieval에서는 넓게 후보를 찾고, generation에서는 `fact_type`, `answer_policy`, `*_answer_enabled`를 보고 최종 답변에 써도 되는 근거만 사용하도록 설계했습니다.  
> 특히 `document_identity`는 문서 찾기용이고, `threshold_budget`은 자격요건 금액일 수 있으므로 사업예산 답변으로 쓰면 안 됩니다.
