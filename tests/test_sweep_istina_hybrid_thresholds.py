# -*- coding: utf-8 -*-
"""Tests for the hybrid threshold sweep summary."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.sweep_istina_hybrid_thresholds import select_recommended_threshold  # noqa: E402


def _row(label: str, threshold: float, precision: float, f1: float) -> dict:
    return {
        "label": label,
        "hypergraph_support_threshold": threshold,
        "hybrid_linkable": {
            "precision": precision,
            "f1": f1,
        },
        "hybrid_new_author": {
            "false_link_rate": 0.005,
        },
        "delta_vs_framework": {
            "linkable_recall": 0.05,
        },
    }


def test_threshold_selection_requires_precision_safety_margin():
    rows = [
        _row("Crossref ORCID", 1.0, 0.99520, 0.94),
        _row("Advisor DOI ORCID", 1.0, 0.99900, 0.95),
        _row("Crossref ORCID", 1.25, 0.99543, 0.93),
        _row("Advisor DOI ORCID", 1.25, 0.99900, 0.94),
    ]

    selection = select_recommended_threshold(rows)

    assert selection["threshold"] == 1.25
    assert selection["selected"]["precision_margin_ready"] is True
