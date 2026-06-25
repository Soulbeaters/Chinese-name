#!/usr/bin/env python3
"""Prototype an official national-statistics role fallback."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluate_mentor_large_scale import (  # noqa: E402
    CONTEXT_MODES,
    adjust_by_person,
    adjust_by_publication,
    build_records,
    get_config,
    load_all_split_names,
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


def load_scores(path: Path) -> dict[str, tuple[float, int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    totals = payload["totals"]
    vocabulary = totals["vocabulary"]
    surname_denominator = totals["surname"] + vocabulary
    given_denominator = totals["given"] + vocabulary
    return {
        token: (
            math.log((surname_count + 1.0) / surname_denominator)
            - math.log((given_count + 1.0) / given_denominator),
            surname_count + given_count,
        )
        for token, (surname_count, given_count) in payload["counts"].items()
    }


def is_morphology_only_western(decision: NameDecision) -> bool:
    return (
        decision.mode == "WESTERN"
        and any(code in {"WEST_SURNAME_FIRST", "WEST_SURNAME_LAST"} for code in decision.reason_codes)
        and not any(code.startswith("KNOWN_NON_CHINESE_SURNAME") for code in decision.reason_codes)
    )


def apply_role_model(
    record: Any,
    decision: NameDecision,
    scores: dict[str, tuple[float, int]],
    margin: float,
    min_support: int,
    confidence: float,
    pub_conf_thresh: float,
    include_morphology_override: bool,
) -> NameDecision:
    morphology_override = include_morphology_override and is_morphology_only_western(decision)
    if decision.confidence >= pub_conf_thresh and not morphology_override:
        return decision
    if (
        not morphology_override
        and not any(code in ELIGIBLE_REASONS for code in decision.reason_codes)
    ):
        return decision

    parsed = preprocess_name(record.name_raw)
    if parsed.first_idx < 0 or parsed.last_idx < 0:
        return decision
    first = scores.get(parsed.tokens[parsed.first_idx].ascii.lower())
    last = scores.get(parsed.tokens[parsed.last_idx].ascii.lower())
    if not first or not last or first[1] < min_support or last[1] < min_support:
        return decision
    delta = first[0] - last[0]
    if abs(delta) < margin:
        return decision
    return NameDecision(
        order="family_first" if delta > 0 else "given_first",
        confidence=confidence,
        mode=decision.mode,
        reason_codes=decision.reason_codes
        + [f"OFFICIAL_STATS_ROLE_LOG_ODDS({delta:.2f})"],
    )


def compact_result(result: dict[str, Any]) -> dict[str, dict[str, int]]:
    compact = {}
    for mode_name in next(iter(result["results"].values())):
        given = result["results"]["given_first"][mode_name]
        family = result["results"]["family_first"][mode_name]
        compact[mode_name] = {
            "errors": given["errors"] + family["errors"],
            "unknown": given["unknown"] + family["unknown"],
            "combined": given["errors"] + family["errors"] + given["unknown"] + family["unknown"],
            "applied": given["role_applied"] + family["role_applied"],
        }
    return compact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pair-hash-bucket", type=int, choices=range(5))
    parser.add_argument("--candidate-filter", choices=("pinyin", "all"), default="pinyin")
    parser.add_argument("--margins", type=float, nargs="+", default=[3, 4, 5, 6, 7])
    parser.add_argument("--min-supports", type=int, nargs="+", default=[5, 10, 25, 50])
    parser.add_argument("--include-morphology-override", action="store_true")
    args = parser.parse_args()

    set_ablation_config(
        AblationConfig(
            surname_freq_strategy="freq_disabled",
            enable_corpus_role_model=True,
            enable_jmnedict_role_model=True,
            enable_ssa_census_role_model=True,
        )
    )
    rows = load_candidates(args.dataset) if args.candidate_filter == "pinyin" else load_all_split_names(args.dataset)
    if args.pair_hash_bucket is not None:
        rows = [row for row in rows if name_pair_bucket(row) == args.pair_hash_bucket]

    scores = load_scores(args.model)
    cfg = get_config("CROSSREF")
    output: dict[str, Any] = {
        "dataset": str(args.dataset),
        "model": str(args.model),
        "pair_hash_bucket": args.pair_hash_bucket,
        "candidate_filter": args.candidate_filter,
        "include_morphology_override": args.include_morphology_override,
        "candidate_records": len(rows),
        "role_vocabulary": len(scores),
        "results": {},
    }

    for expected_order in ("given_first", "family_first"):
        records, flags = build_records(rows, expected_order, "CROSSREF")
        baseline_local = {record.record_id: local_decision(record, cfg) for record in records}
        order_results: dict[str, Any] = {}
        for mode_name, (person_enabled, publication_enabled) in CONTEXT_MODES.items():
            baseline_context = dict(baseline_local)
            if publication_enabled:
                baseline_context = adjust_by_publication(records, baseline_context, cfg)
            if person_enabled:
                baseline_context = adjust_by_person(records, baseline_context, cfg)
            baseline_metrics = summarize(records, baseline_context, expected_order, flags)
            baseline_metrics["role_applied"] = 0
            order_results[f"{mode_name}:baseline"] = baseline_metrics

            for margin in args.margins:
                for min_support in args.min_supports:
                    decisions = {
                        record.record_id: apply_role_model(
                            record,
                            baseline_local[record.record_id],
                            scores,
                            margin,
                            min_support,
                            0.72,
                            cfg.pub_conf_thresh,
                            args.include_morphology_override,
                        )
                        for record in records
                    }
                    if publication_enabled:
                        decisions = adjust_by_publication(records, decisions, cfg)
                    if person_enabled:
                        decisions = adjust_by_person(records, decisions, cfg)
                    key = f"{mode_name}:margin={margin:g},min_support={min_support}"
                    metrics = summarize(records, decisions, expected_order, flags)
                    applied_ids = {
                        record_id
                        for record_id, item in decisions.items()
                        if any(
                            code.startswith("OFFICIAL_STATS_ROLE_LOG_ODDS")
                            for code in item.reason_codes
                        )
                    }
                    metrics["role_applied"] = len(applied_ids)
                    classify = lambda item: (
                        "unknown"
                        if item.order == "unknown"
                        else "correct" if item.order == expected_order else "error"
                    )
                    metrics["role_transitions"] = dict(
                        Counter(
                            f"{classify(baseline_context[record_id])}->{classify(decisions[record_id])}"
                            for record_id in applied_ids
                        )
                    )
                    order_results[key] = metrics
        output["results"][expected_order] = order_results

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(compact_result(output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
