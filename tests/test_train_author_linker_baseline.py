# -*- coding: utf-8 -*-
"""Tests for the no-dependency supervised author-linker baseline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.train_author_linker_baseline import (  # noqa: E402
    evaluate_leave_one_dataset_out,
    load_rows,
    metrics_at_threshold,
    select_threshold,
)


def row(dataset: str, same_author: bool, score: float) -> dict[str, object]:
    return {
        "dataset": dataset,
        "same_author": same_author,
        "same_family": True,
        "given_relation": "exact",
        "exact_canonical_name": True,
        "name_is_chinese_like": False,
        "either_initial_only": False,
        "affiliation_jaccard": score,
        "affiliation_weighted_jaccard": score,
        "coauthor_jaccard": score,
        "year_gap": 1,
        "family_frequency": 10,
        "left_has_affiliation": True,
        "right_has_affiliation": True,
        "left_coauthor_count": 2,
        "right_coauthor_count": 2,
        "baseline_same": score > 0.8,
        "baseline_rule": "exact_name_affiliation_jaccard_ge_0.35",
        "baseline_score": score,
        "framework_conservative_same": score > 0.7,
        "framework_conservative_rule": "exact_name_weighted_affiliation_ge_0.42",
        "framework_conservative_score": score,
        "framework_balanced_same": score > 0.6,
        "framework_balanced_rule": "balanced_exact_name_affiliation_ge_0.30",
        "framework_balanced_score": score,
        "framework_strict_same": score > 0.9,
        "framework_strict_rule": "strict_exact_name_requires_strong_context",
        "framework_strict_score": score,
    }


def test_metrics_and_threshold_selection():
    scored = [
        ({"same_author": True}, 0.9),
        ({"same_author": True}, 0.8),
        ({"same_author": False}, 0.7),
        ({"same_author": False}, 0.1),
    ]

    metrics = metrics_at_threshold(scored, 0.75)
    selected = select_threshold(scored, min_precision=1.0)

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert selected["precision"] == 1.0
    assert selected["recall"] == 1.0


def test_leave_one_dataset_out_runs_on_toy_features():
    rows = [
        row("A", True, 0.95),
        row("A", False, 0.05),
        row("A", True, 0.90),
        row("A", False, 0.10),
        row("B", True, 0.96),
        row("B", False, 0.04),
        row("B", True, 0.88),
        row("B", False, 0.12),
    ]

    result = evaluate_leave_one_dataset_out(
        rows,
        epochs=2,
        learning_rate=0.05,
        l2=0.0001,
        min_precision=0.5,
        seed=1,
    )

    assert result["rows"] == 8
    assert result["positive_rows"] == 4
    assert result["negative_rows"] == 4
    assert "all_test_precision_gates_passed" in result
    assert [fold["test_dataset"] for fold in result["folds"]] == ["A", "B"]
    assert all(fold["feature_count"] > 1 for fold in result["folds"])
    assert all("test_precision_gate_passed" in fold for fold in result["folds"])


def test_load_rows_respects_limit(tmp_path):
    features = tmp_path / "features.jsonl"
    features.write_text(
        "\n".join(json.dumps(row("A", index % 2 == 0, 0.5)) for index in range(3)),
        encoding="utf-8",
    )

    assert len(load_rows(features, limit=2)) == 2
