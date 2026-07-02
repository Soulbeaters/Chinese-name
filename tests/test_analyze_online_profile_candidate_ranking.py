# -*- coding: utf-8 -*-
"""Tests for online mention-to-profile candidate ranking diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.analyze_online_profile_candidate_ranking import (  # noqa: E402
    evaluate_examples,
    rank_scores,
    select_setting,
)


def test_rank_scores_uses_score_then_author_id_tiebreaker():
    candidates = [
        {"author_id": "b", "is_truth": False, "scores": {"score": 0.7}},
        {"author_id": "a", "is_truth": True, "scores": {"score": 0.7}},
        {"author_id": "c", "is_truth": False, "scores": {"score": 0.2}},
    ]

    ranked = rank_scores(candidates, "score")

    assert ranked["top_author_id"] == "a"
    assert ranked["top_is_truth"] is True
    assert ranked["margin"] == 0.0


def test_evaluate_examples_counts_unknown_wrong_and_new_false_links():
    examples = [
        {
            "truth_in_history": True,
            "ranked": {
                "score": {
                    "has_candidate": True,
                    "top_score": 0.9,
                    "margin": 0.2,
                    "top_is_truth": True,
                }
            },
        },
        {
            "truth_in_history": True,
            "ranked": {
                "score": {
                    "has_candidate": True,
                    "top_score": 0.8,
                    "margin": 0.1,
                    "top_is_truth": False,
                }
            },
        },
        {
            "truth_in_history": True,
            "ranked": {
                "score": {
                    "has_candidate": False,
                    "top_score": 0.0,
                    "margin": 0.0,
                    "top_is_truth": False,
                }
            },
        },
        {
            "truth_in_history": False,
            "ranked": {
                "score": {
                    "has_candidate": True,
                    "top_score": 0.9,
                    "margin": 0.2,
                    "top_is_truth": False,
                }
            },
        },
    ]

    metrics = evaluate_examples(examples, "score", threshold=0.5, margin=0.0)

    assert metrics["correct"] == 1
    assert metrics["wrong"] == 1
    assert metrics["unknown"] == 1
    assert metrics["new_author_false_links"] == 1
    assert metrics["precision"] == 0.5


def test_select_setting_prefers_safe_recall():
    examples = [
        {
            "truth_in_history": True,
            "ranked": {
                "score": {
                    "has_candidate": True,
                    "top_score": 0.9,
                    "margin": 0.1,
                    "top_is_truth": True,
                }
            },
        },
        {
            "truth_in_history": False,
            "ranked": {
                "score": {
                    "has_candidate": True,
                    "top_score": 0.1,
                    "margin": 0.0,
                    "top_is_truth": False,
                }
            },
        },
    ]

    setting = select_setting(examples, "score")

    assert setting["precision"] == 1.0
    assert setting["recall"] == 1.0
    assert setting["new_author_false_link_rate"] == 0.0
