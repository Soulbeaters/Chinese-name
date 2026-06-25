#!/usr/bin/env python3
"""Production-quality diagnostics for name-order decisions."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluate_mentor_large_scale import (  # noqa: E402
    CONTEXT_MODES,
    apply_confidence_gate,
    build_records,
    get_config,
    load_all_split_names,
    load_candidates,
    name_pair_bucket,
    normalized_tokens,
    sha256_file,
)
from src.config_v8 import AblationConfig, set_ablation_config  # noqa: E402
from src.surname_identifier_v8 import (  # noqa: E402
    NameDecision,
    adjust_by_person,
    adjust_by_publication,
    local_decision,
)


def confidence_bin(value: float) -> str:
    if value < 0.5:
        return "<0.50"
    if value < 0.7:
        return "0.50-0.70"
    if value < 0.72:
        return "0.70-0.72"
    if value < 0.8:
        return "0.72-0.80"
    if value < 0.9:
        return "0.80-0.90"
    return ">=0.90"


def component_pattern(row: dict[str, Any]) -> str:
    first_tokens = normalized_tokens(str(row.get("firstname", "")))
    last_tokens = normalized_tokens(str(row.get("lastname", "")))
    return f"first_tokens={len(first_tokens)},last_tokens={len(last_tokens)}"


def classify(decision: NameDecision, expected_order: str) -> str:
    if decision.order == "unknown":
        return "unknown"
    if decision.order == expected_order:
        return "correct"
    return "error"


def collect_metrics(
    rows: list[dict[str, Any]],
    records_by_order: dict[str, list[Any]],
    decisions_by_order: dict[str, dict[str, NameDecision]],
    non_chinese_by_order: dict[str, dict[str, bool]],
    threshold: float,
    sample_limit: int,
) -> dict[str, Any]:
    counts = Counter()
    strata: dict[str, Counter] = defaultdict(Counter)
    error_samples: list[dict[str, Any]] = []
    unknown_samples: list[dict[str, Any]] = []

    for expected_order, records in records_by_order.items():
        decisions = apply_confidence_gate(decisions_by_order[expected_order], threshold)
        flags = non_chinese_by_order[expected_order]
        for record in records:
            row = rows[int(record.record_id)]
            decision = decisions[record.record_id]
            status = classify(decision, expected_order)
            counts[status] += 1
            counts["total"] += 1

            strata["status_by_expected_order"][f"{status}|{expected_order}"] += 1
            strata["status_by_mode"][f"{status}|{decision.mode}"] += 1
            strata["status_by_confidence"][f"{status}|{confidence_bin(decision.confidence)}"] += 1
            strata["status_by_known_non_chinese"][f"{status}|{flags[record.record_id]}"] += 1
            strata["status_by_component_pattern"][f"{status}|{component_pattern(row)}"] += 1
            for reason in decision.reason_codes:
                strata["status_by_reason"][f"{status}|{reason}"] += 1

            if status in {"error", "unknown"}:
                sample = {
                    "expected_order": expected_order,
                    "status": status,
                    "name_raw": record.name_raw,
                    "firstname": row.get("firstname"),
                    "lastname": row.get("lastname"),
                    "doi": row.get("doi") or row.get("article_id"),
                    "orcid": row.get("orcid"),
                    "affiliation": row.get("affiliation"),
                    "predicted": decision.order,
                    "mode": decision.mode,
                    "confidence": decision.confidence,
                    "reason_codes": decision.reason_codes,
                    "known_non_chinese": flags[record.record_id],
                    "component_pattern": component_pattern(row),
                }
                if status == "error" and len(error_samples) < sample_limit:
                    error_samples.append(sample)
                if status == "unknown" and len(unknown_samples) < sample_limit:
                    unknown_samples.append(sample)

    total = counts["total"]
    errors = counts["error"]
    unknown = counts["unknown"]
    return {
        "threshold": threshold,
        "total_decisions": total,
        "errors": errors,
        "unknown": unknown,
        "combined": errors + unknown,
        "error_rate": errors / total if total else 0.0,
        "unknown_rate": unknown / total if total else 0.0,
        "combined_rate": (errors + unknown) / total if total else 0.0,
        "strata": {
            name: dict(counter.most_common(50))
            for name, counter in strata.items()
        },
        "error_samples": error_samples,
        "unknown_samples": unknown_samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", default="CROSSREF")
    parser.add_argument("--candidate-filter", choices=("pinyin", "all"), default="pinyin")
    parser.add_argument("--pair-hash-bucket", type=int, choices=range(5))
    parser.add_argument(
        "--context-mode",
        choices=tuple(CONTEXT_MODES),
        default="person_publication",
    )
    parser.add_argument("--confidence-thresholds", type=float, nargs="+", default=[0.0, 0.70, 0.72, 0.80])
    parser.add_argument("--sample-limit", type=int, default=100)
    args = parser.parse_args()

    set_ablation_config(AblationConfig(surname_freq_strategy="freq_disabled"))
    rows = load_candidates(args.dataset) if args.candidate_filter == "pinyin" else load_all_split_names(args.dataset)
    if args.pair_hash_bucket is not None:
        rows = [row for row in rows if name_pair_bucket(row) == args.pair_hash_bucket]

    person_enabled, publication_enabled = CONTEXT_MODES[args.context_mode]
    cfg = get_config(args.source)
    records_by_order = {}
    decisions_by_order = {}
    non_chinese_by_order = {}

    for expected_order in ("given_first", "family_first"):
        records, flags = build_records(rows, expected_order, args.source)
        decisions = {
            record.record_id: local_decision(record, cfg)
            for record in records
        }
        if publication_enabled:
            decisions = adjust_by_publication(records, decisions, cfg)
        if person_enabled:
            decisions = adjust_by_person(records, decisions, cfg)
        records_by_order[expected_order] = records
        decisions_by_order[expected_order] = decisions
        non_chinese_by_order[expected_order] = flags

    threshold_results = [
        collect_metrics(
            rows,
            records_by_order,
            decisions_by_order,
            non_chinese_by_order,
            threshold,
            args.sample_limit,
        )
        for threshold in args.confidence_thresholds
    ]
    payload = {
        "dataset": str(args.dataset),
        "dataset_sha256": sha256_file(args.dataset),
        "candidate_records": len(rows),
        "candidate_filter": args.candidate_filter,
        "pair_hash_bucket": args.pair_hash_bucket,
        "context_mode": args.context_mode,
        "threshold_results": threshold_results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps([
        {
            "threshold": item["threshold"],
            "errors": item["errors"],
            "unknown": item["unknown"],
            "combined": item["combined"],
            "error_rate": item["error_rate"],
            "unknown_rate": item["unknown_rate"],
            "combined_rate": item["combined_rate"],
        }
        for item in threshold_results
    ], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
