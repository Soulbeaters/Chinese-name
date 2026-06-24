#!/usr/bin/env python3
"""Prototype a US Census surname-frequency fallback without changing production code.

The script computes local decisions once, then evaluates a grid of conservative
count-ratio thresholds.  It is intended for candidate selection only; a candidate
must still pass the separate holdout and advisor-DOI evaluations.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluate_mentor_large_scale import (  # noqa: E402
    adjust_by_person,
    adjust_by_publication,
    build_records,
    get_config,
    load_candidates,
    name_pair_bucket,
    summarize,
)
from src.config_v8 import AblationConfig, set_ablation_config  # noqa: E402
from src.surname_identifier_v8 import (  # noqa: E402
    NameDecision,
    local_decision,
    preprocess_name,
)


ELIGIBLE_REASONS = {
    "NO_MATCH_DEFAULT_GIVEN",
    "NO_CN_EVIDENCE_DEFAULT_GIVEN",
    "FORCED_GIVEN_ON_TIE",
    "DELTA_SMALL_MIXED",
}


def load_census_counts(path: Path) -> dict[str, tuple[int, float]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["name"]
            .strip()
            .lower(): (
                int(row["count"]),
                (
                    float(row["pctapi"])
                    if row.get("pctapi", "").replace(".", "", 1).isdigit()
                    else 0.0
                ),
            )
            for row in csv.DictReader(handle)
            if row.get("name") and row.get("count")
        }


def apply_census(
    record,
    decision: NameDecision,
    census: dict[str, tuple[int, float]],
    ratio_threshold: float,
    min_count: int,
    min_selected_pctapi: float,
    confidence: float,
    pub_conf_thresh: float,
) -> NameDecision:
    if decision.confidence >= pub_conf_thresh:
        return decision
    if not any(code in ELIGIBLE_REASONS for code in decision.reason_codes):
        return decision

    parsed = preprocess_name(record.name_raw)
    if parsed.first_idx < 0 or parsed.last_idx < 0:
        return decision
    first = parsed.tokens[parsed.first_idx].ascii.lower()
    last = parsed.tokens[parsed.last_idx].ascii.lower()
    first_values = census.get(first)
    last_values = census.get(last)
    if first_values is None or last_values is None:
        return decision
    first_count, first_pctapi = first_values
    last_count, last_pctapi = last_values
    if max(first_count, last_count) < min_count:
        return decision

    ratio = max(first_count, last_count) / max(1, min(first_count, last_count))
    if ratio < ratio_threshold:
        return decision
    delta = math.log(first_count / last_count)
    selected_pctapi = first_pctapi if delta > 0 else last_pctapi
    if selected_pctapi < min_selected_pctapi:
        return decision
    return NameDecision(
        order="family_first" if delta > 0 else "given_first",
        confidence=confidence,
        mode=decision.mode,
        reason_codes=decision.reason_codes
        + [f"CENSUS_SURNAME_COUNT_LOG_RATIO({delta:.2f})"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pair-hash-bucket", type=int, choices=range(5))
    parser.add_argument("--ratios", type=float, nargs="+", default=[4, 10, 25, 50, 100])
    parser.add_argument(
        "--min-counts", type=int, nargs="+", default=[100, 500, 1000, 5000]
    )
    parser.add_argument(
        "--min-selected-pctapis", type=float, nargs="+", default=[0, 25, 50, 75]
    )
    args = parser.parse_args()

    set_ablation_config(
        AblationConfig(
            surname_freq_strategy="freq_disabled",
            enable_corpus_role_model=True,
            enable_jmnedict_role_model=True,
        )
    )
    rows = load_candidates(args.dataset)
    if args.pair_hash_bucket is not None:
        rows = [row for row in rows if name_pair_bucket(row) == args.pair_hash_bucket]
    census = load_census_counts(args.census)
    cfg = get_config("CROSSREF")
    output = {
        "dataset": str(args.dataset),
        "census": str(args.census),
        "pair_hash_bucket": args.pair_hash_bucket,
        "candidate_records": len(rows),
        "results": {},
    }

    for expected_order in ("given_first", "family_first"):
        records, flags = build_records(rows, expected_order, "CROSSREF")
        baseline = {record.record_id: local_decision(record, cfg) for record in records}
        baseline_adjusted = adjust_by_publication(records, dict(baseline), cfg)
        baseline_adjusted = adjust_by_person(records, baseline_adjusted, cfg)
        baseline_metrics = summarize(records, baseline_adjusted, expected_order, flags)
        baseline_metrics["census_applied"] = 0
        order_results = {"baseline": baseline_metrics}
        for ratio in args.ratios:
            for min_count in args.min_counts:
                for min_selected_pctapi in args.min_selected_pctapis:
                    decisions = {
                        record.record_id: apply_census(
                            record,
                            baseline[record.record_id],
                            census,
                            ratio,
                            min_count,
                            min_selected_pctapi,
                            0.72,
                            cfg.pub_conf_thresh,
                        )
                        for record in records
                    }
                    decisions = adjust_by_publication(records, decisions, cfg)
                    decisions = adjust_by_person(records, decisions, cfg)
                    key = (
                        f"ratio={ratio:g},min_count={min_count},"
                        f"min_selected_pctapi={min_selected_pctapi:g}"
                    )
                    metrics = summarize(records, decisions, expected_order, flags)
                    applied_ids = {
                        record_id
                        for record_id, item in decisions.items()
                        if any(
                            code.startswith("CENSUS_SURNAME_COUNT_LOG_RATIO")
                            for code in item.reason_codes
                        )
                    }
                    metrics["census_applied"] = len(applied_ids)
                    classify = lambda item: (
                        "unknown"
                        if item.order == "unknown"
                        else "correct" if item.order == expected_order else "error"
                    )
                    metrics["census_transitions"] = dict(
                        Counter(
                            f"{classify(baseline_adjusted[record_id])}->{classify(decisions[record_id])}"
                            for record_id in applied_ids
                        )
                    )
                    metrics["census_applied_modes"] = dict(
                        Counter(decisions[record_id].mode for record_id in applied_ids)
                    )
                    record_by_id = {record.record_id: record for record in records}
                    metrics["census_change_samples"] = [
                        {
                            "name_raw": record_by_id[record_id].name_raw,
                            "transition": f"{classify(baseline_adjusted[record_id])}->{classify(decisions[record_id])}",
                            "before": baseline_adjusted[record_id].order,
                            "after": decisions[record_id].order,
                            "mode": decisions[record_id].mode,
                            "reason_codes": decisions[record_id].reason_codes,
                        }
                        for record_id in sorted(applied_ids, key=int)
                        if classify(baseline_adjusted[record_id])
                        != classify(decisions[record_id])
                    ][:50]
                    order_results[key] = metrics
        output["results"][expected_order] = order_results

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    compact = {}
    for key in output["results"]["given_first"]:
        given = output["results"]["given_first"][key]
        family = output["results"]["family_first"][key]
        compact[key] = {
            "errors": given["errors"] + family["errors"],
            "unknown": given["unknown"] + family["unknown"],
            "combined": given["errors"]
            + family["errors"]
            + given["unknown"]
            + family["unknown"],
            "applied": given["census_applied"] + family["census_applied"],
        }
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
