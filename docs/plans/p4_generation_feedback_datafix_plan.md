# P4 Generation Feedback Datafix Plan

## Summary

Generation review50 결과에서 확인된 문제를 파싱 단계에서 줄이기 위한 수정 계획이다. 목표는 텍스트를 더 많이 넣는 것이 아니라, RAG가 질문 유형에 맞는 fact를 더 정확히 고르게 만드는 것이다.

이번 수정은 기존 `parsing_p4_hwpx_125` 산출물을 덮어쓰지 않고 새 산출물로 생성한다.

- 새 출력 폴더: `outputs/parsing_p4_hwpx_125_datafix`
- 기준 입력: 기존 P4 HWPX 원문과 동일
- 기존 청킹 크기: `1000 / 150` 유지
- V3가 아니라 P4 125 corpus의 generation feedback 수정버전

## Problems Observed

1. Citation 평가가 실제보다 낮게 측정됨
   - LLM은 완성형 한글 파일명을 출력하고, context의 `source_file`은 조합형 한글로 들어와 exact match가 실패했다.
   - `chunk_id`는 맞는데 `source_file` 문자열만 달라지는 케이스가 많았다.

2. Budget 후보가 오염됨
   - `사업금액의 하한`, `대기업 참여 가능 금액`, `평가/배점 표의 금액`이 실제 사업예산처럼 올라왔다.
   - GKL 예산 질문에서 실제 `사업예산 1,515,000천원` 대신 `80억원/40억원` 하한 금액을 답한 사례가 있었다.

3. 기간 fact가 넓게 묶임
   - 사업기간, 제출기한, 입찰마감일, 유지보수기간, 하자담보기간은 generation에서 다른 의미로 써야 한다.
   - 하나의 `duration` fact로만 묶으면 질문 유형별 context 조립이 둔해진다.

4. Multi-doc/축약명 대응 metadata가 부족함
   - 질문에는 `GKL`, `고대 차세대 포털`, `수공 사고분석`처럼 축약 표현이 들어간다.
   - 문서명/기관명 alias를 더 명확히 metadata에 넣어야 한다.

## Key Changes

### 1. Canonical Identifiers

모든 block/chunk/source record에 다음 필드를 추가한다.

- `source_file_nfc`: Unicode NFC 정규화 파일명
- `canonical_doc_id`: NFC 정규화 문서명 기준 stable id
- `canonical_doc_key`: NFC 정규화 문서 key
- `evidence_id`: LLM citation용 짧은 근거 id

향후 generation prompt는 긴 `source_file` 대신 `evidence_id`를 citation하게 하는 방향으로 바꾼다.

### 2. Budget Type Split

예산 후보를 하나의 `budget`으로 두지 않고 아래 타입으로 분리한다.

- `project_budget`: 실제 사업예산/사업금액/사업비/소요예산/총사업비
- `estimated_price`: 추정가격
- `base_amount`: 기초금액
- `threshold_budget`: 대기업 참여 하한/사업금액의 하한/매출액 구간 금액
- `payment_terms`: 선금/중도금/잔금/지급조건
- `price_proposal`: 가격제안서/산출내역서 작성 양식의 금액
- `reference_amount`: 평가표/배점표/서식/참고용 금액

`final_budget`은 `project_budget`, `estimated_price`, `base_amount`에서만 선발한다. `threshold_budget`, `payment_terms`, `price_proposal`, `reference_amount`는 candidate로 보존하되 최종 사업예산으로 승격하지 않는다.

### 3. Fact Block Split

기존 `budget`, `duration` fact를 더 구체적인 fact로 분리한다.

- `project_budget`
- `estimated_price`
- `base_amount`
- `threshold_budget`
- `payment_terms`
- `project_duration`
- `maintenance_period`
- `warranty_period`
- `deadline_term`

검색/생성 단계에서는 질문 유형에 맞는 fact_type만 우선 조립한다.

### 4. Generation Directness Checks

새 산출물 생성 후 다음을 확인한다.

- `source_file_nfc`, `canonical_doc_id`, `evidence_id` 누락 0건
- `threshold_budget`이 `final_budget`으로 올라간 문서 0건
- GKL 그룹웨어 문서의 최종 예산이 `1,515,000천원` 계열로 잡히는지 확인
- `사업금액의 하한` 후보는 `threshold_budget`으로 분류되는지 확인
- 기간 fact가 `project_duration`, `maintenance_period`, `warranty_period`, `deadline_term`으로 분리되는지 확인

## Expected Impact

- Citation 평가: Unicode mismatch로 인한 허위 실패 감소
- Budget 질문: 하한 금액/평가표 금액 오답 감소
- Duration 질문: 사업기간과 제출/행정 기한 혼동 감소
- Context builder: 질문 유형별로 더 작은 fact 집합을 선택할 수 있어 lost-in-the-middle 위험 감소

## Non-goals

- 250/690 전체 재생성은 이번 단계의 필수 목표가 아니다.
- retrieval 알고리즘 자체는 바꾸지 않는다.
- Judge LLM 평가는 아직 붙이지 않는다.
- 원문 source_store 공개 전략은 바꾸지 않는다.
