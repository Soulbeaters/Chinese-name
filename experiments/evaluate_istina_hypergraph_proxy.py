#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare the current framework with an ISTINA hypergraph-style proxy.

The archived ISTINA C++ code is source-analyzed but not directly runnable on the
local ORCID JSON datasets.  This experiment uses the same high-level inputs as
the old algorithm -- name-generated candidates plus historical coauthor graph --
and evaluates it against the current framework on a common candidate set.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.istina_hypergraph_proxy import (  # noqa: E402
    OnlineBenchmarkConfig,
    evaluate_file,
)


def pct(value: float) -> str:
    return f"{value * 100:.3f}"


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": result["dataset"],
        "cutoff_year": result["cutoff_year"],
        "history_mentions": result["history_mentions"],
        "history_authors": result["history_authors"],
        "test_mentions": result["test_mentions"],
        "truth_in_history_mentions": result["truth_in_history_mentions"],
        "candidate_covered_mentions": result["candidate_covered_mentions"],
        "candidate_coverage_vs_truth_in_history": result[
            "candidate_coverage_vs_truth_in_history"
        ],
        "methods": result["methods"],
        "linkable_end_to_end_methods": result["linkable_end_to_end_methods"],
        "new_author_methods": result["new_author_methods"],
    }


def print_candidate_table(result: dict[str, Any]) -> None:
    print("\nCandidate-covered scoring set:")
    print(
        "| Method | Precision | Recall | F1 | Unknown rate | Paper exact | "
        "Predicted/Correct/Wrong |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|")
    for method, metrics in result["methods"].items():
        print(
            f"| {method} | {pct(metrics['precision'])} | {pct(metrics['recall'])} | "
            f"{pct(metrics['f1'])} | {pct(metrics['unknown_rate'])} | "
            f"{pct(metrics['paper_exact_rate'])} | "
            f"{metrics['predicted_mentions']}/{metrics['correct']}/{metrics['wrong']} |"
        )


def print_linkable_table(result: dict[str, Any]) -> None:
    print("\nLinkable end-to-end set:")
    print("| Method | Precision | Recall | F1 | Unknown rate | Predicted/Correct/Wrong |")
    print("|---|---:|---:|---:|---:|---:|")
    for method, metrics in result["linkable_end_to_end_methods"].items():
        print(
            f"| {method} | {pct(metrics['precision'])} | {pct(metrics['recall'])} | "
            f"{pct(metrics['f1'])} | {pct(metrics['unknown_rate'])} | "
            f"{metrics['predicted_mentions']}/{metrics['correct']}/{metrics['wrong']} |"
        )


def print_new_author_table(result: dict[str, Any]) -> None:
    print("\nNew-author / truth-not-in-history set:")
    print("| Method | False-link rate | No-prediction rate | False links / N |")
    print("|---|---:|---:|---:|")
    for method, metrics in result["new_author_methods"].items():
        print(
            f"| {method} | {pct(metrics['false_link_rate'])} | "
            f"{pct(metrics['no_prediction_rate'])} | "
            f"{metrics['false_links']}/{metrics['evaluated_mentions']} |"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cutoff-year", type=int, default=2021)
    parser.add_argument("--max-profile-mentions", type=int, default=30)
    args = parser.parse_args()

    config = OnlineBenchmarkConfig(
        cutoff_year=args.cutoff_year,
        max_profile_mentions=args.max_profile_mentions,
    )
    result = evaluate_file(args.dataset, config)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(compact_result(result), ensure_ascii=False, indent=2))
    print_candidate_table(result)
    print_linkable_table(result)
    print_new_author_table(result)


if __name__ == "__main__":
    main()
