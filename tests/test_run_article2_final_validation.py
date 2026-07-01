# -*- coding: utf-8 -*-
"""Tests for the Article 2 final validation runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.run_article2_final_validation import build_steps, write_final_summary  # noqa: E402


def public_cluster_gate(production_ready: bool) -> dict[str, object]:
    return {
        "production_ready": production_ready,
        "thresholds": {
            "candidate_pairwise_precision": 0.99,
            "cluster_pairwise_precision": 0.99,
            "b_cubed_f1": 0.95,
        },
        "datasets": [
            {
                "label": "DBLP public balanced",
                "dataset_sha256": "sha-dblp",
                "candidate_profile": "balanced",
                "production_ready": production_ready,
                "candidate": {
                    "cluster_pairwise_precision": 0.949,
                    "b_cubed_f1": 0.972,
                },
            }
        ],
    }


def public_online_gate(production_ready: bool) -> dict[str, object]:
    return {
        "production_ready": production_ready,
        "scope": "LINK/NEW/UNKNOWN online gate",
        "thresholds": {
            "hybrid_linkable_precision": 0.995,
            "hybrid_new_author_false_link_rate": 0.01,
            "hybrid_recall_gain_vs_framework": 0.0,
            "hypergraph_support_threshold": 1.25,
        },
        "datasets": [
            {
                "label": "DBLP public balanced",
                "dataset_sha256": "sha-dblp",
                "history_mentions": 100,
                "test_mentions": 50,
                "production_ready": production_ready,
                "hybrid_linkable": {
                    "precision": 0.996,
                    "recall": 0.82,
                    "f1": 0.90,
                },
                "hybrid_new_author": {
                    "false_link_rate": 0.004,
                },
            }
        ],
    }


def test_final_validation_runner_builds_all_pipeline_steps():
    args = argparse.Namespace(
        crossref_dataset=Path("crossref.json"),
        advisor_dataset=Path("advisor.json"),
        max_block_size=200,
        cutoff_year=2021,
        max_profile_mentions=30,
        hypergraph_support_threshold=1.25,
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
    assert "1.25" in steps[8][1]


def test_final_validation_summary_combines_gate_outputs(tmp_path):
    cluster_path = tmp_path / "cluster.json"
    online_path = tmp_path / "online.json"
    threshold_sweep_path = tmp_path / "threshold_sweep.json"
    public_cluster_path = tmp_path / "public_cluster.json"
    public_strict_cluster_path = tmp_path / "public_strict_cluster.json"
    public_online_path = tmp_path / "public_online.json"
    output_path = tmp_path / "summary.json"
    cluster_path.write_text(
        json.dumps(
            {
                "production_ready": True,
                "thresholds": {
                    "b_cubed_f1": 0.95,
                },
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
                "thresholds": {
                    "hybrid_linkable_precision": 0.995,
                    "hybrid_new_author_false_link_rate": 0.01,
                    "hybrid_recall_gain_vs_framework": 0.0,
                    "hypergraph_support_threshold": 1.25,
                },
                "datasets": [
                    {
                        "label": "Crossref ORCID",
                        "dataset_sha256": "sha-crossref",
                        "hybrid_linkable": {
                            "precision": 0.996,
                            "recall": 0.86,
                            "f1": 0.923,
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
    threshold_sweep_path.write_text(
        json.dumps(
            {
                "thresholds": [1.0, 1.25],
                "validation_config": {
                    "cutoff_year": 2021,
                    "max_profile_mentions": 30,
                    "min_hybrid_linkable_precision": 0.995,
                    "max_hybrid_new_author_false_link_rate": 0.01,
                    "min_hybrid_recall_gain_vs_framework": 0.0,
                },
                "selection": {
                    "threshold": 1.25,
                    "reason": "test selection",
                },
                "rows": [
                    {
                        "label": "Crossref ORCID",
                        "dataset_sha256": "sha-crossref",
                        "hypergraph_support_threshold": 1.0,
                        "hybrid_linkable": {
                            "precision": 0.996,
                            "recall": 0.85,
                            "f1": 0.92,
                        },
                        "hybrid_new_author": {
                            "false_link_rate": 0.006,
                        },
                    },
                    {
                        "label": "Crossref ORCID",
                        "dataset_sha256": "sha-crossref",
                        "hypergraph_support_threshold": 1.25,
                        "hybrid_linkable": {
                            "precision": 0.996,
                            "recall": 0.86,
                            "f1": 0.923,
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
    public_cluster_path.write_text(
        json.dumps(public_cluster_gate(False)),
        encoding="utf-8",
    )
    public_strict_cluster_path.write_text(
        json.dumps(public_cluster_gate(False)),
        encoding="utf-8",
    )
    public_online_path.write_text(
        json.dumps(public_online_gate(True)),
        encoding="utf-8",
    )

    summary = write_final_summary(
        cluster_path,
        online_path,
        output_path,
        ["Unit tests", "Online quality gate"],
        {
            "hypergraph_support_threshold": 1.25,
            "cutoff_year": 2021,
            "max_profile_mentions": 30,
        },
        threshold_sweep_path,
        1.25,
        public_cluster_path,
        public_strict_cluster_path,
        public_online_path,
    )

    assert summary["production_ready"] is True
    assert summary["public_risk_control_ready"] is True
    assert summary["validation_steps"] == ["Unit tests", "Online quality gate"]
    assert summary["validation_config"]["hypergraph_support_threshold"] == 1.25
    assert summary["quality_gate_thresholds"]["cluster"]["b_cubed_f1"] == 0.95
    assert summary["quality_gate_thresholds"]["online"]["hybrid_linkable_precision"] == 0.995
    assert summary["result_paths"]["final_summary"].endswith(
        "article2_final_validation_summary_20260701.json"
    )
    assert summary["code_checks"]["unit_tests"] is True
    assert summary["cluster_datasets"][0]["dataset_sha256"] == "sha-crossref"
    assert summary["online_datasets"][0]["hybrid_new_author_false_link_rate"] == 0.006
    assert summary["threshold_sweep_ready"] is True
    assert summary["threshold_sweep"]["selected_threshold"] == 1.25
    assert summary["threshold_sweep"]["expected_row_count"] == 2
    assert summary["threshold_sweep"]["selected_dataset_count"] == 1
    assert summary["public_validation"]["balanced_cluster_ready"] is False
    assert summary["public_validation"]["online_risk_control_ready"] is True
    assert summary["public_validation"]["online_datasets"][0]["dataset_sha256"] == "sha-dblp"
    assert json.loads(output_path.read_text(encoding="utf-8")) == summary


def test_final_validation_summary_fails_when_public_online_gate_fails(tmp_path):
    cluster_path = tmp_path / "cluster.json"
    online_path = tmp_path / "online.json"
    public_cluster_path = tmp_path / "public_cluster.json"
    public_strict_cluster_path = tmp_path / "public_strict_cluster.json"
    public_online_path = tmp_path / "public_online.json"
    output_path = tmp_path / "summary.json"

    cluster_path.write_text(
        json.dumps(
            {
                "production_ready": True,
                "thresholds": {},
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
                "thresholds": {},
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
    public_cluster_path.write_text(
        json.dumps(public_cluster_gate(False)),
        encoding="utf-8",
    )
    public_strict_cluster_path.write_text(
        json.dumps(public_cluster_gate(False)),
        encoding="utf-8",
    )
    public_online_path.write_text(
        json.dumps(public_online_gate(False)),
        encoding="utf-8",
    )

    summary = write_final_summary(
        cluster_path,
        online_path,
        output_path,
        public_cluster_gate_path=public_cluster_path,
        public_strict_cluster_gate_path=public_strict_cluster_path,
        public_online_gate_path=public_online_path,
    )

    assert summary["public_risk_control_ready"] is False
    assert summary["production_ready"] is False
