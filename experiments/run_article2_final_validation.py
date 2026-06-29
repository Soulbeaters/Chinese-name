#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the full Article 2 validation pipeline on the two local large datasets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CROSSREF_DATASET = Path(r"C:\istina\materia 材料\测试表单\crossref_authors.json")
DEFAULT_ADVISOR_DATASET = Path(r"runs\advisor_doi_20260507\advisor_doi_crossref_api_authors.json")
DEFAULT_CLUSTER_GATE = Path("results/article2_quality_gate_summary_20260628.json")
DEFAULT_ONLINE_GATE = Path("results/article2_online_quality_gate_summary_20260629.json")
DEFAULT_FINAL_SUMMARY = Path("results/article2_final_validation_summary_20260629.json")
RESULT_PATHS = {
    "crossref_baseline": Path("results/article2_baseline_exact_context_crossref_orcid_20260628.json"),
    "advisor_baseline": Path("results/article2_baseline_exact_context_advisor_orcid_20260628.json"),
    "crossref_framework": Path(
        "results/article2_framework_v1_final_balanced_crossref_orcid_20260628.json"
    ),
    "advisor_framework": Path(
        "results/article2_framework_v1_final_balanced_advisor_orcid_20260628.json"
    ),
    "cluster_gate": DEFAULT_CLUSTER_GATE,
    "crossref_online": Path("results/article2_istina_proxy_online_crossref_orcid_20260628.json"),
    "advisor_online": Path("results/article2_istina_proxy_online_advisor_orcid_20260628.json"),
    "online_gate": DEFAULT_ONLINE_GATE,
    "final_summary": DEFAULT_FINAL_SUMMARY,
}


def script_command(script: str, *args: str | Path | int | float) -> list[str]:
    return [sys.executable, str(PROJECT_ROOT / script), *(str(arg) for arg in args)]


def build_steps(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    return [
        ("Unit tests", [sys.executable, "-m", "pytest", "-q"]),
        (
            "Compile Python sources",
            [sys.executable, "-m", "compileall", "-q", "src", "experiments", "tests"],
        ),
        ("Patch whitespace check", ["git", "diff", "--check"]),
        (
            "Crossref baseline",
            script_command(
                "experiments/evaluate_author_disambiguation_framework.py",
                "--dataset",
                args.crossref_dataset,
                "--output",
                RESULT_PATHS["crossref_baseline"],
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
                RESULT_PATHS["advisor_baseline"],
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
                RESULT_PATHS["crossref_framework"],
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
                RESULT_PATHS["advisor_framework"],
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
                RESULT_PATHS["cluster_gate"],
                "--pair",
                "Crossref ORCID",
                RESULT_PATHS["crossref_baseline"],
                RESULT_PATHS["crossref_framework"],
                "--pair",
                "Advisor DOI ORCID",
                RESULT_PATHS["advisor_baseline"],
                RESULT_PATHS["advisor_framework"],
            ),
        ),
        (
            "Crossref online comparison",
            script_command(
                "experiments/evaluate_istina_hypergraph_proxy.py",
                "--dataset",
                args.crossref_dataset,
                "--output",
                RESULT_PATHS["crossref_online"],
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
                RESULT_PATHS["advisor_online"],
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
                RESULT_PATHS["online_gate"],
                "--result",
                "Crossref ORCID",
                RESULT_PATHS["crossref_online"],
                "--result",
                "Advisor DOI ORCID",
                RESULT_PATHS["advisor_online"],
            ),
        ),
    ]


def run_step(label: str, command: list[str]) -> None:
    print(f"\n=== {label} ===", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def write_final_summary(
    cluster_gate_path: Path,
    online_gate_path: Path,
    output_path: Path,
    validation_steps: list[str] | None = None,
    validation_config: dict[str, object] | None = None,
) -> dict[str, object]:
    cluster_gate = json.loads((PROJECT_ROOT / cluster_gate_path).read_text(encoding="utf-8"))
    online_gate = json.loads((PROJECT_ROOT / online_gate_path).read_text(encoding="utf-8"))
    summary = {
        "cluster_gate_path": str(cluster_gate_path),
        "online_gate_path": str(online_gate_path),
        "result_paths": {
            name: str(path)
            for name, path in RESULT_PATHS.items()
        },
        "validation_steps": validation_steps or [],
        "validation_config": validation_config or {},
        "quality_gate_thresholds": {
            "cluster": cluster_gate["thresholds"],
            "online": online_gate["thresholds"],
        },
        "code_checks": {
            "unit_tests": True,
            "compileall": True,
            "patch_whitespace_check": True,
        },
        "cluster_production_ready": cluster_gate["production_ready"],
        "online_production_ready": online_gate["production_ready"],
        "production_ready": (
            cluster_gate["production_ready"] and online_gate["production_ready"]
        ),
        "cluster_datasets": [
            {
                "label": item["label"],
                "dataset_sha256": item.get("dataset_sha256"),
                "cluster_pairwise_precision": item["candidate"]["cluster_pairwise_precision"],
                "b_cubed_f1": item["candidate"]["b_cubed_f1"],
            }
            for item in cluster_gate["datasets"]
        ],
        "online_datasets": [
            {
                "label": item["label"],
                "dataset_sha256": item.get("dataset_sha256"),
                "hybrid_linkable_precision": item["hybrid_linkable"]["precision"],
                "hybrid_linkable_recall": item["hybrid_linkable"]["recall"],
                "hybrid_new_author_false_link_rate": (
                    item["hybrid_new_author"]["false_link_rate"]
                ),
            }
            for item in online_gate["datasets"]
        ],
    }
    target = PROJECT_ROOT / output_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crossref-dataset", type=Path, default=DEFAULT_CROSSREF_DATASET)
    parser.add_argument("--advisor-dataset", type=Path, default=DEFAULT_ADVISOR_DATASET)
    parser.add_argument("--max-block-size", type=int, default=200)
    parser.add_argument("--cutoff-year", type=int, default=2021)
    parser.add_argument("--max-profile-mentions", type=int, default=30)
    parser.add_argument("--hypergraph-support-threshold", type=float, default=3.0)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_FINAL_SUMMARY)
    args = parser.parse_args()

    steps = build_steps(args)
    for label, command in steps:
        run_step(label, command)
    summary = write_final_summary(
        DEFAULT_CLUSTER_GATE,
        DEFAULT_ONLINE_GATE,
        args.summary_output,
        [label for label, _ in steps],
        {
            "crossref_dataset": str(args.crossref_dataset),
            "advisor_dataset": str(args.advisor_dataset),
            "max_block_size": args.max_block_size,
            "cutoff_year": args.cutoff_year,
            "max_profile_mentions": args.max_profile_mentions,
            "hypergraph_support_threshold": args.hypergraph_support_threshold,
        },
    )
    print(
        "\n=== Final validation summary ===\n"
        + json.dumps(summary, ensure_ascii=False, indent=2),
        flush=True,
    )


if __name__ == "__main__":
    main()
