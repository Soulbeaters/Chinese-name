# -*- coding: utf-8 -*-
"""Tests for author-disambiguation production quality gate."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.author_disambiguation_quality_gate import dataset_summary  # noqa: E402


def _result(algorithm: str, b3_f1: float, cluster_f1: float = 0.80):
    return {
        "algorithm": algorithm,
        "profile": "balanced",
        "dataset": "synthetic.json",
        "dataset_sha256": "sha256",
        "labeled_mentions": 100,
        "unique_orcid": 50,
        "candidate_pairwise": {
            "precision": 0.995,
            "recall": 0.70,
            "f1": 0.82,
        },
        "cluster_pairwise": {
            "precision": 0.992,
            "recall": 0.68,
            "f1": cluster_f1,
        },
        "b_cubed": {
            "precision": 0.997,
            "recall": 0.88,
            "f1": b3_f1,
        },
    }


def test_quality_gate_fails_when_b_cubed_f1_below_production_target():
    summary = dataset_summary(
        "synthetic",
        _result("baseline_exact_context", b3_f1=0.91, cluster_f1=0.70),
        _result("framework_v1", b3_f1=0.94, cluster_f1=0.80),
        {
            "candidate_pairwise_precision": 0.99,
            "cluster_pairwise_precision": 0.99,
            "b_cubed_f1": 0.95,
        },
    )

    assert summary["production_ready"] is False
    assert summary["production_checks"]["candidate_pairwise_precision"] is True
    assert summary["production_checks"]["cluster_pairwise_precision"] is True
    assert summary["production_checks"]["b_cubed_f1"] is False
    assert round(summary["delta_vs_baseline"]["b_cubed_f1"], 3) == 0.03


def test_quality_gate_passes_when_all_production_targets_are_met():
    summary = dataset_summary(
        "synthetic",
        _result("baseline_exact_context", b3_f1=0.91, cluster_f1=0.70),
        _result("framework_v1", b3_f1=0.96, cluster_f1=0.83),
        {
            "candidate_pairwise_precision": 0.99,
            "cluster_pairwise_precision": 0.99,
            "b_cubed_f1": 0.95,
        },
    )

    assert summary["production_ready"] is True
