#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production gate for online author-assignment comparison results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_MIN_LINKABLE_PRECISION = 0.995
DEFAULT_MAX_NEW_AUTHOR_FALSE_LINK = 0.01
DEFAULT_MIN_RECALL_GAIN = 0.0
DEFAULT_MIN_HYPERGRAPH_SUPPORT_THRESHOLD = 1.25
DEFAULT_MIN_LOW_UNKNOWN_LINKABLE_RECALL = 0.90
DEFAULT_MAX_LOW_UNKNOWN_RATE = 0.10


def load_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value: float) -> float:
    return round(value * 100, 3)


def method(result: dict[str, Any], section: str, name: str) -> dict[str, Any]:
    return result[section][name]


def dataset_summary(
    label: str,
    result: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    framework_link = method(result, "linkable_end_to_end_methods", "framework_v1_profile")
    hybrid_link = method(result, "linkable_end_to_end_methods", "risk_controlled_hybrid")
    hybrid_new = method(result, "new_author_methods", "risk_controlled_hybrid")
    recall_gain = hybrid_link["recall"] - framework_link["recall"]

    checks = {
        "hypergraph_support_threshold": (
            float(result["hypergraph_support_threshold"])
            >= thresholds["hypergraph_support_threshold"]
        ),
        "hybrid_linkable_precision": (
            hybrid_link["precision"] >= thresholds["hybrid_linkable_precision"]
        ),
        "hybrid_new_author_false_link_rate": (
            hybrid_new["false_link_rate"] <= thresholds["hybrid_new_author_false_link_rate"]
        ),
        "hybrid_recall_gain_vs_framework": (
            recall_gain >= thresholds["hybrid_recall_gain_vs_framework"]
        ),
    }
    low_unknown_checks = {
        "hybrid_linkable_recall": (
            hybrid_link["recall"] >= thresholds["low_unknown_linkable_recall"]
        ),
        "hybrid_linkable_unknown_rate": (
            hybrid_link["unknown_rate"] <= thresholds["low_unknown_rate"]
        ),
    }
    return {
        "label": label,
        "dataset": result["dataset"],
        "dataset_sha256": result.get("dataset_sha256"),
        "history_mentions": result["history_mentions"],
        "test_mentions": result["test_mentions"],
        "truth_in_history_mentions": result["truth_in_history_mentions"],
        "candidate_covered_mentions": result["candidate_covered_mentions"],
        "hypergraph_support_threshold": result["hypergraph_support_threshold"],
        "framework_linkable": {
            "precision": framework_link["precision"],
            "recall": framework_link["recall"],
            "f1": framework_link["f1"],
            "unknown_rate": framework_link["unknown_rate"],
        },
        "hybrid_linkable": {
            "precision": hybrid_link["precision"],
            "recall": hybrid_link["recall"],
            "f1": hybrid_link["f1"],
            "unknown_rate": hybrid_link["unknown_rate"],
        },
        "hybrid_new_author": {
            "false_link_rate": hybrid_new["false_link_rate"],
            "false_links": hybrid_new["false_links"],
            "evaluated_mentions": hybrid_new["evaluated_mentions"],
            "no_prediction_rate": hybrid_new["no_prediction_rate"],
        },
        "delta_vs_framework": {
            "linkable_recall": recall_gain,
            "linkable_unknown_rate": (
                hybrid_link["unknown_rate"] - framework_link["unknown_rate"]
            ),
        },
        "production_checks": checks,
        "production_ready": all(checks.values()),
        "low_unknown_checks": low_unknown_checks,
        "low_unknown_ready": all(checks.values()) and all(low_unknown_checks.values()),
    }


def build_summary(
    results: list[list[str]],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    datasets = [
        dataset_summary(label, load_result(Path(path)), thresholds)
        for label, path in results
    ]
    return {
        "thresholds": thresholds,
        "datasets": datasets,
        "production_ready": all(item["production_ready"] for item in datasets),
        "low_unknown_ready": all(item["low_unknown_ready"] for item in datasets),
        "scope": (
            "LINK/NEW/UNKNOWN online gate; UNKNOWN remains a manual-review output, "
            "not an automatic merge."
        ),
    }


def print_table(summary: dict[str, Any]) -> None:
    print(
        "| Dataset | Hybrid link P/R/F1 | UNKNOWN | Recall gain | New false-link | "
        "Threshold | Risk gate | Low-UNKNOWN |"
    )
    print("|---|---:|---:|---:|---:|---:|---|---|")
    for item in summary["datasets"]:
        link = item["hybrid_linkable"]
        new = item["hybrid_new_author"]
        delta = item["delta_vs_framework"]
        gate = "PASS" if item["production_ready"] else "FAIL"
        low_unknown = "PASS" if item["low_unknown_ready"] else "FAIL"
        print(
            "| {label} | {p:.3f}/{r:.3f}/{f:.3f} | {unknown:.3f} | {gain:+.3f} | "
            "{false:.3f} ({false_links}/{n}) | {threshold:.3f} | {gate} | "
            "{low_unknown} |".format(
                label=item["label"],
                p=pct(link["precision"]),
                r=pct(link["recall"]),
                f=pct(link["f1"]),
                unknown=pct(link["unknown_rate"]),
                gain=pct(delta["linkable_recall"]),
                false=pct(new["false_link_rate"]),
                false_links=new["false_links"],
                n=new["evaluated_mentions"],
                threshold=item["hypergraph_support_threshold"],
                gate=gate,
                low_unknown=low_unknown,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result",
        action="append",
        nargs=2,
        metavar=("LABEL", "JSON"),
        required=True,
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--min-hybrid-linkable-precision",
        type=float,
        default=DEFAULT_MIN_LINKABLE_PRECISION,
    )
    parser.add_argument(
        "--max-hybrid-new-author-false-link-rate",
        type=float,
        default=DEFAULT_MAX_NEW_AUTHOR_FALSE_LINK,
    )
    parser.add_argument(
        "--min-hybrid-recall-gain-vs-framework",
        type=float,
        default=DEFAULT_MIN_RECALL_GAIN,
    )
    parser.add_argument(
        "--min-hypergraph-support-threshold",
        type=float,
        default=DEFAULT_MIN_HYPERGRAPH_SUPPORT_THRESHOLD,
    )
    parser.add_argument(
        "--min-low-unknown-linkable-recall",
        type=float,
        default=DEFAULT_MIN_LOW_UNKNOWN_LINKABLE_RECALL,
    )
    parser.add_argument(
        "--max-low-unknown-rate",
        type=float,
        default=DEFAULT_MAX_LOW_UNKNOWN_RATE,
    )
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    thresholds = {
        "hybrid_linkable_precision": args.min_hybrid_linkable_precision,
        "hybrid_new_author_false_link_rate": (
            args.max_hybrid_new_author_false_link_rate
        ),
        "hybrid_recall_gain_vs_framework": (
            args.min_hybrid_recall_gain_vs_framework
        ),
        "hypergraph_support_threshold": args.min_hypergraph_support_threshold,
        "low_unknown_linkable_recall": args.min_low_unknown_linkable_recall,
        "low_unknown_rate": args.max_low_unknown_rate,
    }
    summary = build_summary(args.result, thresholds)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print_table(summary)

    if not summary["production_ready"] and not args.warn_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
