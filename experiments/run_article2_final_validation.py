#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the full Article 2 validation pipeline on the two local large datasets."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CROSSREF_DATASET = Path(r"C:\istina\materia 材料\测试表单\crossref_authors.json")
DEFAULT_ADVISOR_DATASET = Path(r"runs\advisor_doi_20260507\advisor_doi_crossref_api_authors.json")


def script_command(script: str, *args: str | Path | int | float) -> list[str]:
    return [sys.executable, str(PROJECT_ROOT / script), *(str(arg) for arg in args)]


def build_steps(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    crossref_baseline = Path("results/article2_baseline_exact_context_crossref_orcid_20260628.json")
    advisor_baseline = Path("results/article2_baseline_exact_context_advisor_orcid_20260628.json")
    crossref_framework = Path(
        "results/article2_framework_v1_final_balanced_crossref_orcid_20260628.json"
    )
    advisor_framework = Path(
        "results/article2_framework_v1_final_balanced_advisor_orcid_20260628.json"
    )
    cluster_gate = Path("results/article2_quality_gate_summary_20260628.json")
    crossref_online = Path("results/article2_istina_proxy_online_crossref_orcid_20260628.json")
    advisor_online = Path("results/article2_istina_proxy_online_advisor_orcid_20260628.json")
    online_gate = Path("results/article2_online_quality_gate_summary_20260629.json")

    return [
        (
            "Crossref baseline",
            script_command(
                "experiments/evaluate_author_disambiguation_framework.py",
                "--dataset",
                args.crossref_dataset,
                "--output",
                crossref_baseline,
                "--algorithm",
                "baseline_exact_context",
                "--profile",
                "conservative",
                "--max-block-size",
                args.max_block_size,
            ),
        ),
        (
            "Advisor baseline",
            script_command(
                "experiments/evaluate_author_disambiguation_framework.py",
                "--dataset",
                args.advisor_dataset,
                "--output",
                advisor_baseline,
                "--algorithm",
                "baseline_exact_context",
                "--profile",
                "conservative",
                "--max-block-size",
                args.max_block_size,
            ),
        ),
        (
            "Crossref framework_v1",
            script_command(
                "experiments/evaluate_author_disambiguation_framework.py",
                "--dataset",
                args.crossref_dataset,
                "--output",
                crossref_framework,
                "--algorithm",
                "framework_v1",
                "--profile",
                "balanced",
                "--max-block-size",
                args.max_block_size,
            ),
        ),
        (
            "Advisor framework_v1",
            script_command(
                "experiments/evaluate_author_disambiguation_framework.py",
                "--dataset",
                args.advisor_dataset,
                "--output",
                advisor_framework,
                "--algorithm",
                "framework_v1",
                "--profile",
                "balanced",
                "--max-block-size",
                args.max_block_size,
            ),
        ),
        (
            "Cluster quality gate",
            script_command(
                "experiments/author_disambiguation_quality_gate.py",
                "--output",
                cluster_gate,
                "--pair",
                "Crossref ORCID",
                crossref_baseline,
                crossref_framework,
                "--pair",
                "Advisor DOI ORCID",
                advisor_baseline,
                advisor_framework,
            ),
        ),
        (
            "Crossref online comparison",
            script_command(
                "experiments/evaluate_istina_hypergraph_proxy.py",
                "--dataset",
                args.crossref_dataset,
                "--output",
                crossref_online,
                "--cutoff-year",
                args.cutoff_year,
                "--max-profile-mentions",
                args.max_profile_mentions,
                "--hypergraph-support-threshold",
                args.hypergraph_support_threshold,
            ),
        ),
        (
            "Advisor online comparison",
            script_command(
                "experiments/evaluate_istina_hypergraph_proxy.py",
                "--dataset",
                args.advisor_dataset,
                "--output",
                advisor_online,
                "--cutoff-year",
                args.cutoff_year,
                "--max-profile-mentions",
                args.max_profile_mentions,
                "--hypergraph-support-threshold",
                args.hypergraph_support_threshold,
            ),
        ),
        (
            "Online quality gate",
            script_command(
                "experiments/online_disambiguation_quality_gate.py",
                "--output",
                online_gate,
                "--result",
                "Crossref ORCID",
                crossref_online,
                "--result",
                "Advisor DOI ORCID",
                advisor_online,
            ),
        ),
    ]


def run_step(label: str, command: list[str]) -> None:
    print(f"\n=== {label} ===", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crossref-dataset", type=Path, default=DEFAULT_CROSSREF_DATASET)
    parser.add_argument("--advisor-dataset", type=Path, default=DEFAULT_ADVISOR_DATASET)
    parser.add_argument("--max-block-size", type=int, default=200)
    parser.add_argument("--cutoff-year", type=int, default=2021)
    parser.add_argument("--max-profile-mentions", type=int, default=30)
    parser.add_argument("--hypergraph-support-threshold", type=float, default=3.0)
    args = parser.parse_args()

    for label, command in build_steps(args):
        run_step(label, command)


if __name__ == "__main__":
    main()
