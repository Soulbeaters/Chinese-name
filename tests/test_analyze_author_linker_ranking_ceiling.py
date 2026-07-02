# -*- coding: utf-8 -*-
"""Tests for mention-level ranking diagnostics over exported linker features."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.analyze_author_linker_ranking_ceiling import (  # noqa: E402
    anchor_examples,
    context_score,
    evaluate_examples,
    leave_one_dataset_out,
)


def _row(
    dataset: str,
    left: str,
    right: str,
    same: bool,
    balanced_score: float,
    coauthor: float = 0.0,
) -> dict[str, object]:
    return {
        "dataset": dataset,
        "left_mention_id": left,
        "right_mention_id": right,
        "same_author": same,
        "given_relation": "exact",
        "framework_balanced_score": balanced_score,
        "framework_strict_score": 0.0,
        "coauthor_jaccard": coauthor,
        "affiliation_weighted_jaccard": 0.0,
        "affiliation_jaccard": 0.0,
        "left_has_affiliation": False,
        "right_has_affiliation": False,
        "name_is_chinese_like": False,
        "either_initial_only": False,
        "family_frequency": 10,
    }


def test_anchor_examples_build_directed_candidate_groups():
    rows = [
        _row("A", "m1", "m2", True, 0.8),
        _row("A", "m1", "m3", False, 0.2),
    ]

    examples = anchor_examples(rows, lambda row: float(row["framework_balanced_score"]))
    by_anchor = {example["anchor_id"]: example for example in examples}

    assert by_anchor["m1"]["has_positive"] is True
    assert by_anchor["m1"]["top_is_positive"] is True
    assert by_anchor["m1"]["candidate_count"] == 2
    assert by_anchor["m3"]["has_positive"] is False


def test_evaluate_examples_separates_link_precision_and_new_author_false_links():
    examples = [
        {
            "dataset": "A",
            "anchor_id": "link-ok",
            "has_positive": True,
            "top_score": 0.9,
            "margin": 0.3,
            "top_is_positive": True,
        },
        {
            "dataset": "A",
            "anchor_id": "new-false",
            "has_positive": False,
            "top_score": 0.9,
            "margin": 0.3,
            "top_is_positive": False,
        },
    ]

    metrics = evaluate_examples(examples, threshold=0.5, margin=0.0)

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["new_author_false_link_rate"] == 1.0
    assert metrics["low_unknown_ready"] is False


def test_leave_one_dataset_out_reports_each_scorer_and_dataset():
    rows = [
        _row("A", "a1", "a2", True, 0.9, 0.2),
        _row("A", "a1", "a3", False, 0.1),
        _row("B", "b1", "b2", True, 0.9, 0.2),
        _row("B", "b1", "b3", False, 0.1),
    ]

    folds = leave_one_dataset_out(rows)

    assert {fold["held_out_dataset"] for fold in folds} == {"A", "B"}
    assert {fold["scorer"] for fold in folds} == {
        "context_score",
        "framework_balanced_score",
        "framework_strict_score",
    }
    assert all("test" in fold for fold in folds)


def test_context_score_rewards_context_evidence():
    weak = _row("A", "m1", "m2", True, 0.0, 0.0)
    strong = _row("A", "m1", "m2", True, 0.6, 0.4)

    assert context_score(strong) > context_score(weak)
