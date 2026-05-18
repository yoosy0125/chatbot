# RAG Notebooks

P2 corpus를 KoE5로 임베딩하고, Chroma/BM25/RRF/Reranker 조합의 retrieval 성능을 비교하는 단계입니다.

## Files

| 파일 | 용도 |
|---|---|
| `embedding_retrieval_eval_v2_p2.ipynb` | KoE5 embedding, Chroma indexing, R0~R6 retrieval 평가 |
| `rag_pipeline_road_map.ipynb` | RAG pipeline 학습/설계 참고 노트북 |

## Required Local Inputs

아래 파일은 용량이 커서 GitHub에 포함하지 않습니다. Google Drive 또는 로컬/VM 디스크에 별도로 배치합니다.

```text
outputs/parsing_p2_250/
├─ chunks_v2.jsonl   # 기본 corpus
└─ chunks_v1.jsonl   # R0 baseline

data/eval/
├─ eval_batch_01.csv
├─ ...
└─ eval_batch_25.csv
```

`eval_batch_26` 이후는 Q id가 다시 시작되므로 기본 공식 평가에서는 제외합니다.

## Experiments

| ID | 조건 | 목적 |
|---|---|---|
| R0 | v1 clean text dense top5 | clean text baseline |
| R1 | v2_p2 dense top5 | 기본 dense 검색 |
| R2 | v2_p2 dense top10 | 후보 수 증가 효과 |
| R3 | v2_p2 MMR top5, fetch_k=30 | 다양성 반영 |
| R4 | dense top30 -> reranker top5 | reranker 효과 |
| R5 | dense top30 + BM25 top30 -> RRF top5 | hybrid 효과 |
| R6 | dense + BM25 -> RRF top30 -> reranker top5 | hybrid + reranker 최종 후보 |

## Output Policy

아래 실행 결과는 GitHub에 포함하지 않습니다.

```text
outputs/retrieval_eval/
├─ chroma/
├─ embedding_cache/
├─ predictions/
└─ experiment_logs/retrieval_experiments.csv
```

`retrieval_experiments.csv`는 실행할 때마다 append됩니다. 100문항 smoke test와 500문항 공식 범위 결과가 함께 남을 수 있으므로, 최종 비교에는 `num_eval_questions=500`, `eval_scope=canonical_01_25`인 최신 row를 사용합니다.

## Evaluation Scope

- smoke test: `EVAL_SAMPLE_SIZE=30~100`
- 공식 범위 전체: `EVAL_SAMPLE_SIZE=0`
- 공식 범위 전체 문항 수: 500개 (`eval_batch_01~25`)

## Runtime Notes

Colab/GCP L4 기준으로 설계했습니다. 로컬 RTX4060에서도 가능하지만, reranker 포함 전체 500문항은 시간이 걸릴 수 있습니다.

이미 Chroma/embedding cache가 있으면 KoE5 임베딩 생성 셀을 다시 실행하지 않고, `User parameters -> eval load -> prediction -> evaluation`만 다시 실행하면 됩니다.
