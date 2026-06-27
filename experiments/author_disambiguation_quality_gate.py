#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize and gate author-disambiguation evaluation results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_MIN_CANDIDATE_PRECISION = 0.99
DEFAULT_MIN_CLUSTER_PRECISION = 0.99
DEFAULT_MIN_B_CUBED_F1 = 0.95


def load_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def metric(result: dict[str, Any], section: str, name: str) -> float:
    return float(result[section][name])


def pct(value: float) -> float:
    return round(value * 100, 3)


def dataset_summary(
    label: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    checks = {
        "candidate_pairwise_precision": (
            metric(candidate, "candidate_pairwise", "precision")
            >= thresholds["candidate_pairwise_precision"]
        ),
        "cluster_pairwise_precision": (
            metric(candidate, "cluster_pairwise", "precision")
            >= thresholds["cluster_pairwise_precision"]
        ),
        "b_cubed_f1": metric(candidate, "b_cubed", "f1") >= thresholds["b_cubed_f1"],
    }
    return {
        "label": label,
        "dataset": candidate["dataset"],
        "dataset_sha256": candidate.get("dataset_sha256"),
        "labeled_mentions": candidate["labeled_mentions"],
        "unique_orcid": candidate["unique_orcid"],
        "baseline_algorithm": baseline["algorithm"],
        "candidate_algorithm": candidate["algorithm"],
        "candidate_profile": candidate["profile"],
        "baseline": {
            "candidate_pairwise_f1": baseline["candidate_pairwise"]["f1"],
            "cluster_pairwise_f1": baseline["cluster_pairwise"]["f1"],
            "b_cubed_f1": baseline["b_cubed"]["f1"],
        },
        "candidate": {
            "candidate_pairwise_precision": candidate["candidate_pairwise"]["precision"],
            "candidate_pairwise_recall": candidate["candidate_pairwise"]["recall"],
            "candidate_pairwise_f1": candidate["candidate_pairwise"]["f1"],
            "cluster_pairwise_precision": candidate["cluster_pairwise"]["precision"],
            "cluster_pairwise_recall": candidate["cluster_pairwise"]["recall"],
            "cluster_pairwise_f1": candidate["cluster_pairwise"]["f1"],
            "b_cubed_precision": candidate["b_cubed"]["precision"],
            "b_cubed_recall": candidate["b_cubed"]["recall"],
            "b_cubed_f1": candidate["b_cubed"]["f1"],
        },
        "delta_vs_baseline": {
            "candidate_pairwise_f1": (
                candidate["candidate_pairwise"]["f1"] - baseline["candidate_pairwise"]["f1"]
            ),
            "cluster_pairwise_f1": (
                candidate["cluster_pairwise"]["f1"] - baseline["cluster_pairwise"]["f1"]
            ),
            "b_cubed_f1": candidate["b_cubed"]["f1"] - baseline["b_cubed"]["f1"],
        },
        "production_checks": checks,
        "production_ready": all(checks.values()),
    }


def build_summary(
    pairs: list[list[str]],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    datasets = []
    for label, baseline_path, candidate_path in pairs:
        datasets.append(
            dataset_summary(
                label,
                load_result(Path(baseline_path)),
                load_result(Path(candidate_path)),
                thresholds,
            )
        )
    return {
        "thresholds": thresholds,
        "datasets": datasets,
        "production_ready": all(item["production_ready"] for item in datasets),
    }


def print_table(summary: dict[str, Any]) -> None:
    print("| Dataset | Candidate P/R/F1 | Cluster P/R/F1 | B3 F1 | Delta Cluster F1 | Delta B3 F1 | Gate |")
    print("|---|---:|---:|---:|---:|---:|---|")
    for item in summary["datasets"]:
        candidate = item["candidate"]
        delta = item["delta_vs_baseline"]
        gate = "PASS" if item["production_ready"] else "FAIL"
        print(
            "| {label} | {cp:.3f}/{cr:.3f}/{cf:.3f} | {kp:.3f}/{kr:.3f}/{kf:.3f} | "
            "{b3:.3f} | {dkf:+.3f} | {db3:+.3f} | {gate} |".format(
                label=item["label"],
                cp=pct(candidate["candidate_pairwise_precision"]),
                cr=pct(candidate["candidate_pairwise_recall"]),
                cf=pct(candidate["candidate_pairwise_f1"]),
                kp=pct(candidate["cluster_pairwise_precision"]),
                kr=pct(candidate["cluster_pairwise_recall"]),
                kf=pct(candidate["cluster_pairwise_f1"]),
                b3=pct(candidate["b_cubed_f1"]),
                dkf=pct(delta["cluster_pairwise_f1"]),
                db3=pct(delta["b_cubed_f1"]),
                gate=gate,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pair",
        action="append",
        nargs=3,
        metavar=("LABEL", "BASELINE_JSON", "CANDIDATE_JSON"),
        required=True,
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--min-candidate-pairwise-precision",
        type=float,
        default=DEFAULT_MIN_CANDIDATE_PRECISION,
    )
    parser.add_argument(
        "--min-cluster-pairwise-precision",
        type=float,
        default=DEFAULT_MIN_CLUSTER_PRECISION,
    )
    parser.add_argument("--min-b-cubed-f1", type=float, default=DEFAULT_MIN_B_CUBED_F1)
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    thresholds = {
        "candidate_pairwise_precision": args.min_candidate_pairwise_precision,
        "cluster_pairwise_precision": args.min_cluster_pairwise_precision,
        "b_cubed_f1": args.min_b_cubed_f1,
    }
    summary = build_summary(args.pair, thresholds)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print_table(summary)

    if not summary["production_ready"] and not args.warn_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
