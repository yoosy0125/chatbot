from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import unicodedata


def sha1_short(text: str, n: int = 12) -> str:
    return hashlib.sha1(str(text or "").encode("utf-8")).hexdigest()[:n]


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def truncate(text: str, limit: int = 700) -> str:
    text = normalize_space(text)
    return text if len(text) <= limit else text[:limit].rstrip() + " ..."


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def as_scalar(value):
    if isinstance(value, bool):
        return str(value)
    if value is None:
        return ""
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, (list, tuple, set)):
        return "|".join(str(x) for x in value if str(x).strip())
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def metadata_update(row: dict, values: dict) -> None:
    metadata = row.setdefault("metadata", {})
    for key, value in values.items():
        row[key] = value
        metadata[key] = as_scalar(value)


def normalize_doc_text(text: str) -> str:
    return unicodedata.normalize("NFC", str(text or ""))


AMOUNT_PATTERNS = [
    (re.compile(r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*천\s*원"), 1_000, "천원"),
    (re.compile(r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*백\s*만\s*원"), 1_000_000, "백만원"),
    (re.compile(r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*억\s*원"), 100_000_000, "억원"),
    (re.compile(r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*원"), 1, "원"),
]


def parse_amount_krw(raw_num: str, multiplier: int) -> int | None:
    try:
        value = float(str(raw_num).replace(",", ""))
        return int(round(value * multiplier))
    except Exception:
        return None


def extract_amount_candidates(text: str) -> list[dict]:
    candidates = []
    seen = set()
    for pattern, multiplier, unit in AMOUNT_PATTERNS:
        for match in pattern.finditer(text or ""):
            amount_krw = parse_amount_krw(match.group("num"), multiplier)
            if amount_krw is None:
                continue
            raw = match.group(0)
            key = (match.start(), match.end(), amount_krw)
            if key in seen:
                continue
            seen.add(key)
            left = max(0, match.start() - 90)
            right = min(len(text), match.end() + 90)
            candidates.append({
                "amount_raw": raw,
                "amount_krw": amount_krw,
                "amount_unit": unit,
                "context": normalize_space(text[left:right]),
                "start": match.start(),
            })
    return sorted(candidates, key=lambda x: x["start"])


def classify_budget_type(context: str, current_fact_type: str = "") -> str:
    text = normalize_space(context)
    current = str(current_fact_type or "")
    if current in {
        "project_budget",
        "total_allocation",
        "estimated_price",
        "base_amount",
        "threshold_budget",
        "payment_terms",
        "price_proposal",
        "reference_amount",
    }:
        return current
    if any(k in text for k in ["대금", "지급", "선금", "중도금", "잔금", "분할", "청구"]):
        return "payment_terms"
    if any(k in text for k in ["입찰참가", "참가자격", "자격", "실적", "수행실적", "최근", "이상", "이하", "초과", "미만"]):
        if any(k in text for k in ["억원", "원", "천원", "백만원"]):
            return "threshold_budget"
    if any(k in text for k in ["추정가격", "추정 금액", "추정금액"]):
        return "estimated_price"
    if any(k in text for k in ["기초금액", "기준금액", "예정가격"]):
        return "base_amount"
    if any(k in text for k in ["전체 배정액", "총 배정액", "배정액", "총액"]):
        return "total_allocation"
    if any(k in text for k in ["사업예산", "사업 예산", "사업비", "사업 비", "사업금액", "소요예산", "총사업비", "용역비", "예산액", "예산"]):
        return "project_budget"
    if "budget_type:" in text:
        value = text.split("budget_type:", 1)[1].split("|", 1)[0].strip()
        return value or "reference_amount"
    return "reference_amount"


def policy_for_budget_type(budget_type: str) -> dict:
    if budget_type in {"project_budget", "total_allocation"}:
        return {
            "answer_policy": "allow_as_project_budget",
            "budget_answer_enabled": True,
            "answer_allowed_question_types": "budget,budget_comparison,budget_sum,budget_difference,total_allocation",
            "answer_blocked_question_types": "",
            "answer_risk_level": "low",
            "retrieval_role": "typed_budget_signal",
            "fact_status": "extracted",
            "fact_confidence": "high",
        }
    if budget_type in {"estimated_price", "base_amount"}:
        return {
            "answer_policy": "allow_as_secondary_budget_only",
            "budget_answer_enabled": False,
            "answer_allowed_question_types": "estimated_price,base_amount,general_reference",
            "answer_blocked_question_types": "project_budget,total_allocation",
            "answer_risk_level": "medium",
            "retrieval_role": "secondary_budget_signal",
            "fact_status": "reference_only",
            "fact_confidence": "medium",
        }
    if budget_type == "payment_terms":
        return {
            "answer_policy": "allow_for_payment_terms_exclude_for_project_budget",
            "budget_answer_enabled": False,
            "payment_answer_enabled": True,
            "answer_allowed_question_types": "payment_terms,contract_terms,general_reference",
            "answer_blocked_question_types": "budget,project_budget,total_allocation",
            "answer_risk_level": "medium",
            "retrieval_role": "payment_terms_signal",
            "fact_status": "reference_only",
            "fact_confidence": "medium",
        }
    if budget_type == "threshold_budget":
        return {
            "answer_policy": "allow_for_eligibility_exclude_for_project_budget",
            "budget_answer_enabled": False,
            "eligibility_answer_enabled": True,
            "answer_allowed_question_types": "eligibility,performance_requirement,general_reference",
            "answer_blocked_question_types": "budget,project_budget,total_allocation",
            "answer_risk_level": "high",
            "retrieval_role": "eligibility_threshold_signal",
            "fact_status": "reference_only",
            "fact_confidence": "medium",
        }
    return {
        "answer_policy": "route_only_not_final_answer",
        "budget_answer_enabled": False,
        "answer_allowed_question_types": "general_reference",
        "answer_blocked_question_types": "budget,project_budget,total_allocation",
        "answer_risk_level": "high",
        "retrieval_role": "reference_amount_signal",
        "fact_status": "reference_only",
        "fact_confidence": "medium",
    }


def enrich_existing_fact(row: dict) -> None:
    if row.get("chunk_type") != "fact_candidates":
        return
    content = row.get("content", "")
    fact_type = str(row.get("fact_type") or row.get("metadata", {}).get("fact_type") or "")
    amounts = extract_amount_candidates(content)
    if amounts and not row.get("amount_krw"):
        selected = amounts[0]
        budget_type = classify_budget_type(selected["context"] + " " + content[:200], fact_type)
        policy = policy_for_budget_type(budget_type)
        metadata_update(row, {
            "amount_raw": selected["amount_raw"],
            "amount_krw": selected["amount_krw"],
            "amount_unit": selected["amount_unit"],
            "amount_type": budget_type,
            "budget_type": budget_type,
            **policy,
        })
        if fact_type in {"budget", "project_budget", "estimated_price", "base_amount", "total_allocation", "payment_terms", "threshold_budget"}:
            metadata_update(row, {"fact_type": budget_type})
    if fact_type == "document_summary" and re.search(r"(사업금액|사업예산|사업비|소요예산|추정가격|기초금액)\s*[:：]", content):
        metadata_update(row, {
            "answer_policy": "route_only_not_final_answer",
            "budget_answer_enabled": False,
            "answer_blocked_question_types": "budget,project_budget,total_allocation",
            "answer_risk_level": "medium",
        })
        if "[주의:" not in content:
            row["content"] = content + "\n[주의: 이 document_summary의 금액 신호는 라우팅용입니다. 최종 예산 답변은 project_budget/total_allocation fact를 우선 사용합니다.]"


def make_derived_chunk(base_row: dict, fact_type: str, label: str, body: str, extra: dict | None = None) -> dict:
    extra = extra or {}
    doc_id = base_row["doc_id"]
    source_file = base_row.get("source_file", "")
    metadata_base = dict(base_row.get("metadata") or {})
    section_path = f"핵심 후보 정보 > {fact_type}"
    content = (
        f"[문서: {source_file} | 사업명: {metadata_base.get('project_name', '')} | "
        f"발주기관: {metadata_base.get('issuer', '')} | 섹션: {section_path} | 유형: fact_candidates]\n"
        f"{label}: {body}"
    )
    content_hash = sha1_short(content)
    chunk_id = f"{doc_id}_fact_candidates_fact_goalfix_{fact_type}_{content_hash}"
    source_ref = dict(base_row.get("source_ref") or {})
    metadata = {
        "doc_id": doc_id,
        "doc_key": base_row.get("doc_key", metadata_base.get("doc_key", "")),
        "canonical_doc_id": metadata_base.get("canonical_doc_id", ""),
        "canonical_doc_key": metadata_base.get("canonical_doc_key", ""),
        "source_file": source_file,
        "source_file_nfc": metadata_base.get("source_file_nfc", normalize_doc_text(source_file)),
        "evidence_id": f"EV_{sha1_short(chunk_id, 10)}",
        "source_format": base_row.get("source_format", metadata_base.get("source_format", "")),
        "file_type": metadata_base.get("file_type", ""),
        "chunk_type": "fact_candidates",
        "section_path": section_path,
        "section_type": "핵심 후보 정보",
        "issuer": metadata_base.get("issuer", ""),
        "project_name": metadata_base.get("project_name", ""),
        "fact_type": fact_type,
        "fact_status": extra.get("fact_status", "extracted"),
        "fact_confidence": extra.get("fact_confidence", "medium"),
        "retrieval_role": extra.get("retrieval_role", "goalfix_field_signal"),
        "answer_policy": extra.get("answer_policy", "question_type_dependent"),
        "answer_allowed_question_types": extra.get("answer_allowed_question_types", "matching_question_type,general_reference"),
        "answer_blocked_question_types": extra.get("answer_blocked_question_types", ""),
        "answer_risk_level": extra.get("answer_risk_level", "low"),
        "budget_answer_enabled": extra.get("budget_answer_enabled", False),
        "eligibility_answer_enabled": extra.get("eligibility_answer_enabled", False),
        "payment_answer_enabled": extra.get("payment_answer_enabled", False),
    }
    for key in ["amount_raw", "amount_krw", "amount_unit", "amount_type", "budget_type"]:
        if key in extra:
            metadata[key] = extra[key]
    return {
        "chunk_id": chunk_id,
        "doc_id": doc_id,
        "doc_key": metadata["doc_key"],
        "source_file": source_file,
        "source_format": base_row.get("source_format", metadata.get("source_format", "")),
        "chunk_type": "fact_candidates",
        "embed_enabled": True,
        "content": content,
        "metadata": {k: as_scalar(v) for k, v in metadata.items()},
        "source_ref": {
            "source_store_id": source_ref.get("source_store_id", ""),
            "block_id": source_ref.get("block_id", ""),
            "part_index": source_ref.get("part_index", 1),
            "content_hash": content_hash,
        },
        "fact_type": fact_type,
        "fact_status": metadata["fact_status"],
        "fact_confidence": metadata["fact_confidence"],
        "evidence_text_short": truncate(body, 500),
        **{k: v for k, v in extra.items() if k in {"amount_raw", "amount_krw", "amount_unit", "amount_type", "budget_type", "answer_policy", "budget_answer_enabled"}},
    }


FIELD_RULES = {
    "project_scope": {
        "label": "사업범위/과업범위/대상시스템",
        "keywords": ["사업범위", "과업범위", "업무범위", "구축 범위", "대상 시스템", "주요 과업", "세부 과업", "범위"],
    },
    "project_background": {
        "label": "추진배경/필요성/현황 문제",
        "keywords": ["추진배경", "추진 배경", "필요성", "현황 및 문제점", "사업 배경", "개선 필요", "문제점"],
    },
    "requirements": {
        "label": "요구사항/기능/산출물",
        "keywords": ["요구사항", "기능 요구", "성능 요구", "데이터 요구", "보안 요구", "산출물", "인증서", "수료", "발급", "대시보드", "조회"],
    },
    "project_purpose_effect": {
        "label": "사업목적/기대효과/개선목표",
        "keywords": ["사업목적", "사업 목적", "목표", "기대효과", "개선효과", "추진목적"],
    },
}


def score_for_keywords(text: str, keywords: list[str]) -> int:
    return sum(2 if keyword in text[:250] else 1 for keyword in keywords if keyword in text)


def derive_goalfix_chunks(rows: list[dict]) -> tuple[list[dict], Counter]:
    by_doc = defaultdict(list)
    for row in rows:
        by_doc[row.get("doc_id", "")].append(row)

    added = []
    added_counts = Counter()
    for doc_id, doc_rows in by_doc.items():
        if not doc_id:
            continue
        base_row = next((r for r in doc_rows if r.get("chunk_type") != "fact_candidates"), doc_rows[0])
        existing_fact_types = {str(r.get("fact_type") or r.get("metadata", {}).get("fact_type") or "") for r in doc_rows}

        amount_by_type = {}
        searchable_rows = [r for r in doc_rows if r.get("chunk_type") in {"text", "table", "fact_candidates"}]
        for row in searchable_rows:
            content = row.get("content", "")
            for cand in extract_amount_candidates(content):
                if cand["amount_krw"] < 1_000_000:
                    continue
                budget_type = classify_budget_type(cand["context"], row.get("fact_type", ""))
                if budget_type not in amount_by_type:
                    amount_by_type[budget_type] = (row, cand)
        for budget_type, (source_row, cand) in amount_by_type.items():
            if budget_type in existing_fact_types and any(str(r.get("fact_type") or "") == budget_type and r.get("amount_krw") for r in doc_rows):
                continue
            policy = policy_for_budget_type(budget_type)
            body = f"{budget_type}: {cand['amount_raw']} | KRW: {cand['amount_krw']} | 근거: {cand['context']}"
            chunk = make_derived_chunk(
                source_row,
                budget_type,
                "금액 의미 보정",
                body,
                {
                    **policy,
                    "amount_raw": cand["amount_raw"],
                    "amount_krw": cand["amount_krw"],
                    "amount_unit": cand["amount_unit"],
                    "amount_type": budget_type,
                    "budget_type": budget_type,
                },
            )
            added.append(chunk)
            added_counts[budget_type] += 1

        non_fact_rows = [r for r in doc_rows if r.get("chunk_type") in {"text", "table"}]
        for fact_type, rule in FIELD_RULES.items():
            if fact_type in existing_fact_types:
                continue
            scored = []
            for row in non_fact_rows:
                content = normalize_space(row.get("content", ""))
                if len(content) < 80:
                    continue
                score = score_for_keywords(content, rule["keywords"])
                if score:
                    scored.append((score, row, content))
            if not scored:
                continue
            scored.sort(key=lambda x: (-x[0], len(x[2])))
            _, source_row, content = scored[0]
            chunk = make_derived_chunk(source_row, fact_type, rule["label"], truncate(content, 900))
            added.append(chunk)
            added_counts[fact_type] += 1
    return added, added_counts


def validate(chunks: list[dict], source_store: list[dict], before_count: int, added_counts: Counter, output_dir: Path) -> dict:
    chunk_ids = [row.get("chunk_id", "") for row in chunks]
    source_ids = {row.get("source_store_id", "") for row in source_store}
    refs = [row.get("source_ref", {}).get("source_store_id", "") for row in chunks]
    missing_refs = [ref for ref in refs if ref and source_store and ref not in source_ids]
    fact_rows = [row for row in chunks if row.get("chunk_type") == "fact_candidates"]
    report = {
        "input_chunk_count": before_count,
        "output_chunk_count": len(chunks),
        "added_chunk_count": len(chunks) - before_count,
        "added_chunk_type_counts": dict(added_counts),
        "duplicate_chunk_id_count": len(chunk_ids) - len(set(chunk_ids)),
        "missing_source_store_ref": len(missing_refs),
        "chunk_type_counts": dict(Counter(row.get("chunk_type", "") for row in chunks)),
        "fact_type_counts": dict(Counter(str(row.get("fact_type") or row.get("metadata", {}).get("fact_type") or "") for row in fact_rows)),
        "amount_type_counts": dict(Counter(str(row.get("amount_type") or row.get("metadata", {}).get("amount_type") or "") for row in fact_rows if row.get("amount_krw") or row.get("metadata", {}).get("amount_krw"))),
        "budget_answer_enabled_count": sum(str(row.get("budget_answer_enabled") or row.get("metadata", {}).get("budget_answer_enabled")).lower() == "true" for row in fact_rows),
        "document_summary_budget_guard_count": sum(
            (str(row.get("fact_type") or row.get("metadata", {}).get("fact_type")) == "document_summary")
            and "최종 예산 답변" in row.get("content", "")
            for row in fact_rows
        ),
        "chunks_jsonl_size_mib": round((output_dir / "chunks_v2_125.jsonl").stat().st_size / 1024 / 1024, 2)
        if (output_dir / "chunks_v2_125.jsonl").exists() else 0,
    }
    return report


def run(input_dir: Path, output_dir: Path) -> dict:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = input_dir / "chunks_v2_125.jsonl"
    source_candidates = [input_dir / "source_store_v2_125.jsonl", input_dir / "source_store_125.jsonl"]
    source_path = next((candidate for candidate in source_candidates if candidate.exists()), source_candidates[0])
    metadata_path = input_dir / "metadata_light_125.xlsx"
    if not chunks_path.exists():
        raise FileNotFoundError(f"chunks file not found: {chunks_path}")

    chunks = read_jsonl(chunks_path)
    source_store = read_jsonl(source_path)
    before_count = len(chunks)

    for row in chunks:
        enrich_existing_fact(row)
    added, added_counts = derive_goalfix_chunks(chunks)
    chunks.extend(added)

    # deterministic order by document and chunk id keeps repeated runs comparable.
    chunks.sort(key=lambda row: (row.get("doc_key", ""), row.get("source_file", ""), row.get("chunk_type", ""), row.get("chunk_id", "")))

    write_jsonl(output_dir / "chunks_v2_125.jsonl", chunks)
    if source_path.exists():
        shutil.copy2(source_path, output_dir / source_path.name)
    if metadata_path.exists():
        shutil.copy2(metadata_path, output_dir / "metadata_light_125.xlsx")

    report = validate(chunks, source_store, before_count, added_counts, output_dir)
    (output_dir / "validation_report_goalfix.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    readme = f"""# P4 HWPX 125 Goalfix Corpus

## 목적

기존 `parsing_p4_hwpx_125_datafix_recallguard` 산출물을 덮어쓰지 않고, generation 검토에서 발견된 데이터 문제를 125개 샘플 기준으로 빠르게 보정한 corpus입니다.

## 핵심 보정

- 금액 표현에 `amount_krw`, `amount_type`, `budget_type`을 보강했습니다.
- `project_budget`, `total_allocation`, `estimated_price`, `base_amount`, `threshold_budget`, `payment_terms`를 분리했습니다.
- `document_summary`에 들어간 금액은 라우팅용으로 제한하고, 최종 예산 답변은 typed budget fact를 우선하도록 표시했습니다.
- 사업범위, 추진배경, 요구사항, 사업목적/기대효과 보조 fact chunk를 추가했습니다.

## 파일

```text
chunks_v2_125.jsonl              # Chroma 적재용
source_store_v2_125.jsonl        # 기존 상세 근거 파일 복사본
metadata_light_125.xlsx          # 기존 참고용 메타데이터 복사본
validation_report_goalfix.json   # 보정 검증 요약
README.md
```

## Validation 요약

```json
{json.dumps(report, ensure_ascii=False, indent=2)}
```
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.input_dir, args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
