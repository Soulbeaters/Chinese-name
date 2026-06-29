#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sweep risk-controlled hybrid support thresholds on the large Article 2 datasets."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.online_disambiguation_quality_gate import (  # noqa: E402
    DEFAULT_MAX_NEW_AUTHOR_FALSE_LINK,
    DEFAULT_MIN_LINKABLE_PRECISION,
    DEFAULT_MIN_RECALL_GAIN,
)
from src.istina_hypergraph_proxy import OnlineBenchmarkConfig, evaluate_file  # noqa: E402


DEFAULT_CROSSREF_DATASET = Path(r"C:\istina\materia 材料\测试表单\crossref_authors.json")
DEFAULT_ADVISOR_DATASET = Path(r"runs\advisor_doi_20260507\advisor_doi_crossref_api_authors.json")
DEFAULT_OUTPUT = Path("results/article2_hybrid_threshold_sweep_20260629.json")
DEFAULT_THRESHOLDS = (0.5, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0)
DEFAULT_MIN_PRECISION_MARGIN = 0.00025


def compact_result(label: str, result: dict[str, Any]) -> dict[str, Any]:
    framework_link = result["linkable_end_to_end_methods"]["framework_v1_profile"]
    hybrid_link = result["linkable_end_to_end_methods"]["risk_controlled_hybrid"]
    hybrid_new = result["new_author_methods"]["risk_controlled_hybrid"]
    recall_gain = hybrid_link["recall"] - framework_link["recall"]
    return {
        "label": label,
        "dataset": result["dataset"],
        "dataset_sha256": result["dataset_sha256"],
        "hypergraph_support_threshold": result["hypergraph_support_threshold"],
        "history_mentions": result["history_mentions"],
        "test_mentions": result["test_mentions"],
        "truth_in_history_mentions": result["truth_in_history_mentions"],
        "candidate_covered_mentions": result["candidate_covered_mentions"],
        "hybrid_linkable": {
            "precision": hybrid_link["precision"],
            "recall": hybrid_link["recall"],
            "f1": hybrid_link["f1"],
            "unknown_rate": hybrid_link["unknown_rate"],
            "wrong": hybrid_link["wrong"],
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
    }


def production_ready(
    row: dict[str, Any],
    min_precision: float,
    max_false_link: float,
    min_recall_gain: float,
) -> bool:
    return (
        row["hybrid_linkable"]["precision"] >= min_precision
        and row["hybrid_new_author"]["false_link_rate"] <= max_false_link
        and row["delta_vs_framework"]["linkable_recall"] >= min_recall_gain
    )


def select_recommended_threshold(
    rows: list[dict[str, Any]],
    min_precision: float = DEFAULT_MIN_LINKABLE_PRECISION,
    max_false_link: float = DEFAULT_MAX_NEW_AUTHOR_FALSE_LINK,
    min_recall_gain: float = DEFAULT_MIN_RECALL_GAIN,
    min_precision_margin: float = DEFAULT_MIN_PRECISION_MARGIN,
) -> dict[str, Any]:
    rows_by_threshold: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_threshold[float(row["hypergraph_support_threshold"])].append(row)

    candidates: list[dict[str, Any]] = []
    for threshold, threshold_rows in sorted(rows_by_threshold.items()):
        all_gate_ready = all(
            production_ready(row, min_precision, max_false_link, min_recall_gain)
            for row in threshold_rows
        )
        min_precision_margin_value = min(
            row["hybrid_linkable"]["precision"] - min_precision
            for row in threshold_rows
        )
        min_false_link_margin = min(
            max_false_link - row["hybrid_new_author"]["false_link_rate"]
            for row in threshold_rows
        )
        mean_f1 = sum(row["hybrid_linkable"]["f1"] for row in threshold_rows) / len(
            threshold_rows
        )
        candidates.append(
            {
                "threshold": threshold,
                "production_ready": all_gate_ready,
                "precision_margin_ready": (
                    min_precision_margin_value >= min_precision_margin
                ),
                "min_precision_margin": min_precision_margin_value,
                "min_false_link_margin": min_false_link_margin,
                "mean_hybrid_linkable_f1": mean_f1,
            }
        )

    eligible = [
        item
        for item in candidates
        if item["production_ready"] and item["precision_margin_ready"]
    ]
    if not eligible:
        return {
            "threshold": None,
            "reason": "No threshold satisfied production gates and precision safety margin.",
            "candidates": candidates,
        }

    selected = max(
        eligible,
        key=lambda item: (
            item["mean_hybrid_linkable_f1"],
            item["min_precision_margin"],
            -item["threshold"],
        ),
    )
    return {
        "threshold": selected["threshold"],
        "reason": (
            "Selected the production-ready threshold with at least "
            f"{min_precision_margin:.6f} precision safety margin and the highest "
            "mean linkable F1 across datasets."
        ),
        "selected": selected,
        "candidates": candidates,
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    datasets = [
        ("Crossref ORCID", args.crossref_dataset),
        ("Advisor DOI ORCID", args.advisor_dataset),
    ]
    rows: list[dict[str, Any]] = []
    for threshold in args.thresholds:
        for label, dataset in datasets:
            result = evaluate_file(
                dataset,
                OnlineBenchmarkConfig(
                    cutoff_year=args.cutoff_year,
                    max_profile_mentions=args.max_profile_mentions,
                    hypergraph_support_threshold=threshold,
                ),
            )
            rows.append(compact_result(label, result))

    selection = select_recommended_threshold(
        rows,
        min_precision=args.min_hybrid_linkable_precision,
        max_false_link=args.max_hybrid_new_author_false_link_rate,
        min_recall_gain=args.min_hybrid_recall_gain_vs_framework,
        min_precision_margin=args.min_precision_margin,
    )
    return {
        "thresholds": args.thresholds,
        "validation_config": {
            "crossref_dataset": str(args.crossref_dataset),
            "advisor_dataset": str(args.advisor_dataset),
            "cutoff_year": args.cutoff_year,
            "max_profile_mentions": args.max_profile_mentions,
            "min_hybrid_linkable_precision": args.min_hybrid_linkable_precision,
            "max_hybrid_new_author_false_link_rate": (
                args.max_hybrid_new_author_false_link_rate
            ),
            "min_hybrid_recall_gain_vs_framework": (
                args.min_hybrid_recall_gain_vs_framework
            ),
            "min_precision_margin": args.min_precision_margin,
        },
        "selection": selection,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crossref-dataset", type=Path, default=DEFAULT_CROSSREF_DATASET)
    parser.add_argument("--advisor-dataset", type=Path, default=DEFAULT_ADVISOR_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cutoff-year", type=int, default=2021)
    parser.add_argument("--max-profile-mentions", type=int, default=30)
    parser.add_argument("--thresholds", nargs="+", type=float, default=DEFAULT_THRESHOLDS)
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
        "--min-precision-margin",
        type=float,
        default=DEFAULT_MIN_PRECISION_MARGIN,
    )
    args = parser.parse_args()

    summary = build_summary(args)
    target = PROJECT_ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary["selection"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
