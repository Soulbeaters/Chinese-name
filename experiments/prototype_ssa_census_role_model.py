#!/usr/bin/env python3
"""Prototype a normalized given-name/surname role fallback.

Given-name counts come from the official SSA national baby-name archive and
surname counts from the official 2010 US Census surname file.  The script is
for candidate selection; production adoption requires separate holdout and
advisor-DOI confirmation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import zipfile
from collections import Counter, defaultdict
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
from src.surname_identifier_v8 import (
    NameDecision,
    local_decision,
    preprocess_name,
)  # noqa: E402


ELIGIBLE_REASONS = {
    "NO_MATCH_DEFAULT_GIVEN",
    "NO_CN_EVIDENCE_DEFAULT_GIVEN",
    "FORCED_GIVEN_ON_TIE",
    "DELTA_SMALL_MIXED",
}


def load_role_scores(ssa_zip: Path, census_csv: Path) -> dict[str, tuple[float, int]]:
    given_counts: dict[str, int] = defaultdict(int)
    with zipfile.ZipFile(ssa_zip) as archive:
        for filename in archive.namelist():
            if not (filename.startswith("yob") and filename.endswith(".txt")):
                continue
            for raw_line in archive.read(filename).decode("utf-8").splitlines():
                name, _sex, count = raw_line.split(",")
                given_counts[name.lower()] += int(count)

    surname_counts: dict[str, int] = {}
    with census_csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("name") and row.get("count"):
                surname_counts[row["name"].lower()] = int(row["count"])

    total_given = sum(given_counts.values())
    total_surname = sum(surname_counts.values())
    vocabulary = set(given_counts) | set(surname_counts)
    given_denominator = total_given + len(vocabulary)
    surname_denominator = total_surname + len(vocabulary)
    return {
        token: (
            math.log((surname_counts.get(token, 0) + 1) / surname_denominator)
            - math.log((given_counts.get(token, 0) + 1) / given_denominator),
            surname_counts.get(token, 0) + given_counts.get(token, 0),
        )
        for token in vocabulary
    }


def apply_role_model(
    record,
    decision: NameDecision,
    scores: dict[str, tuple[float, int]],
    margin: float,
    min_support: int,
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
        reason_codes=decision.reason_codes + [f"SSA_CENSUS_ROLE_LOG_ODDS({delta:.2f})"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--ssa-zip", type=Path, required=True)
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pair-hash-bucket", type=int, choices=range(5))
    parser.add_argument("--margins", type=float, nargs="+", default=[1, 2, 3, 4])
    parser.add_argument("--min-supports", type=int, nargs="+", default=[5, 100, 1000])
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
    scores = load_role_scores(args.ssa_zip, args.census)
    cfg = get_config("CROSSREF")
    output = {
        "dataset": str(args.dataset),
        "ssa_zip": str(args.ssa_zip),
        "census": str(args.census),
        "pair_hash_bucket": args.pair_hash_bucket,
        "candidate_records": len(rows),
        "role_vocabulary": len(scores),
        "results": {},
    }

    for expected_order in ("given_first", "family_first"):
        records, flags = build_records(rows, expected_order, "CROSSREF")
        baseline = {record.record_id: local_decision(record, cfg) for record in records}
        baseline_adjusted = adjust_by_publication(records, dict(baseline), cfg)
        baseline_adjusted = adjust_by_person(records, baseline_adjusted, cfg)
        baseline_metrics = summarize(records, baseline_adjusted, expected_order, flags)
        baseline_metrics["role_applied"] = 0
        order_results = {"baseline": baseline_metrics}
        for margin in args.margins:
            for min_support in args.min_supports:
                decisions = {
                    record.record_id: apply_role_model(
                        record,
                        baseline[record.record_id],
                        scores,
                        margin,
                        min_support,
                        0.72,
                        cfg.pub_conf_thresh,
                    )
                    for record in records
                }
                decisions = adjust_by_publication(records, decisions, cfg)
                decisions = adjust_by_person(records, decisions, cfg)
                key = f"margin={margin:g},min_support={min_support}"
                metrics = summarize(records, decisions, expected_order, flags)
                applied_ids = {
                    record_id
                    for record_id, item in decisions.items()
                    if any(
                        code.startswith("SSA_CENSUS_ROLE_LOG_ODDS")
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
                        f"{classify(baseline_adjusted[record_id])}->{classify(decisions[record_id])}"
                        for record_id in applied_ids
                    )
                )
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
            "applied": given["role_applied"] + family["role_applied"],
        }
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
