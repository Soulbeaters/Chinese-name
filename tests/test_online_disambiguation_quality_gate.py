# -*- coding: utf-8 -*-
"""Tests for the online author-assignment production gate."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.online_disambiguation_quality_gate import dataset_summary  # noqa: E402


def _result(
    hybrid_precision: float,
    hybrid_recall: float,
    new_false_link: float,
    threshold: float = 1.25,
):
    return {
        "dataset": "synthetic.json",
        "dataset_sha256": "abc123",
        "history_mentions": 100,
        "test_mentions": 200,
        "truth_in_history_mentions": 80,
        "candidate_covered_mentions": 75,
        "hypergraph_support_threshold": threshold,
        "linkable_end_to_end_methods": {
            "framework_v1_profile": {
                "precision": 0.998,
                "recall": 0.80,
                "f1": 0.89,
                "unknown_rate": 0.18,
            },
            "risk_controlled_hybrid": {
                "precision": hybrid_precision,
                "recall": hybrid_recall,
                "f1": 0.91,
                "unknown_rate": 0.13,
            },
        },
        "new_author_methods": {
            "risk_controlled_hybrid": {
                "false_link_rate": new_false_link,
                "false_links": 5,
                "evaluated_mentions": 1000,
                "no_prediction_rate": 1.0 - new_false_link,
            }
        },
    }


def test_online_quality_gate_passes_for_high_precision_low_false_link_hybrid():
    summary = dataset_summary(
        "synthetic",
        _result(hybrid_precision=0.996, hybrid_recall=0.86, new_false_link=0.006),
        {
            "hybrid_linkable_precision": 0.995,
            "hybrid_new_author_false_link_rate": 0.01,
            "hybrid_recall_gain_vs_framework": 0.0,
            "hypergraph_support_threshold": 1.25,
        },
    )

    assert summary["production_ready"] is True
    assert summary["production_checks"]["hybrid_linkable_precision"] is True
    assert summary["production_checks"]["hybrid_new_author_false_link_rate"] is True
    assert summary["dataset_sha256"] == "abc123"
    assert round(summary["delta_vs_framework"]["linkable_recall"], 3) == 0.06


def test_online_quality_gate_fails_when_new_author_false_link_is_too_high():
    summary = dataset_summary(
        "synthetic",
        _result(hybrid_precision=0.996, hybrid_recall=0.86, new_false_link=0.02),
        {
            "hybrid_linkable_precision": 0.995,
            "hybrid_new_author_false_link_rate": 0.01,
            "hybrid_recall_gain_vs_framework": 0.0,
            "hypergraph_support_threshold": 1.25,
        },
    )

    assert summary["production_ready"] is False
    assert summary["production_checks"]["hybrid_new_author_false_link_rate"] is False
