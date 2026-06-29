# -*- coding: utf-8 -*-
"""Tests for the Article 2 final validation runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.run_article2_final_validation import build_steps, write_final_summary  # noqa: E402


def test_final_validation_runner_builds_all_pipeline_steps():
    args = argparse.Namespace(
        crossref_dataset=Path("crossref.json"),
        advisor_dataset=Path("advisor.json"),
        max_block_size=200,
        cutoff_year=2021,
        max_profile_mentions=30,
        hypergraph_support_threshold=3.0,
    )

    steps = build_steps(args)
    labels = [label for label, _ in steps]

    assert labels == [
        "Unit tests",
        "Compile Python sources",
        "Patch whitespace check",
        "Crossref baseline",
        "Advisor baseline",
        "Crossref framework_v1",
        "Advisor framework_v1",
        "Cluster quality gate",
        "Crossref online comparison",
        "Advisor online comparison",
        "Online quality gate",
    ]
    assert any("author_disambiguation_quality_gate.py" in part for part in steps[7][1])
    assert any("online_disambiguation_quality_gate.py" in part for part in steps[-1][1])
    assert "3.0" in steps[8][1]


def test_final_validation_summary_combines_gate_outputs(tmp_path):
    cluster_path = tmp_path / "cluster.json"
    online_path = tmp_path / "online.json"
    output_path = tmp_path / "summary.json"
    cluster_path.write_text(
        json.dumps(
            {
                "production_ready": True,
                "datasets": [
                    {
                        "label": "Crossref ORCID",
                        "dataset_sha256": "sha-crossref",
                        "candidate": {
                            "cluster_pairwise_precision": 0.993,
                            "b_cubed_f1": 0.951,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    online_path.write_text(
        json.dumps(
            {
                "production_ready": True,
                "datasets": [
                    {
                        "label": "Crossref ORCID",
                        "dataset_sha256": "sha-crossref",
                        "hybrid_linkable": {
                            "precision": 0.996,
                            "recall": 0.86,
                        },
                        "hybrid_new_author": {
                            "false_link_rate": 0.006,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = write_final_summary(
        cluster_path,
        online_path,
        output_path,
        ["Unit tests", "Online quality gate"],
    )

    assert summary["production_ready"] is True
    assert summary["validation_steps"] == ["Unit tests", "Online quality gate"]
    assert summary["result_paths"]["final_summary"].endswith(
        "article2_final_validation_summary_20260629.json"
    )
    assert summary["code_checks"]["unit_tests"] is True
    assert summary["cluster_datasets"][0]["dataset_sha256"] == "sha-crossref"
    assert summary["online_datasets"][0]["hybrid_new_author_false_link_rate"] == 0.006
    assert json.loads(output_path.read_text(encoding="utf-8")) == summary
