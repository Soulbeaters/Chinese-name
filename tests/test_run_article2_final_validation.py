# -*- coding: utf-8 -*-
"""Tests for the Article 2 final validation runner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.run_article2_final_validation import build_steps  # noqa: E402


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
        "Crossref baseline",
        "Advisor baseline",
        "Crossref framework_v1",
        "Advisor framework_v1",
        "Cluster quality gate",
        "Crossref online comparison",
        "Advisor online comparison",
        "Online quality gate",
    ]
    assert any("author_disambiguation_quality_gate.py" in part for part in steps[4][1])
    assert any("online_disambiguation_quality_gate.py" in part for part in steps[-1][1])
    assert "3.0" in steps[5][1]
