# -*- coding: utf-8 -*-
"""Tests for the ISTINA hypergraph-style online benchmark proxy."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.author_disambiguation import row_to_mention  # noqa: E402
from src.istina_hypergraph_proxy import (  # noqa: E402
    OnlineBenchmarkConfig,
    build_profiles,
    choose_istina_hypergraph_proxy,
    choose_risk_controlled_hybrid,
    evaluate_online_assignment,
    get_candidates,
    hard_case_labels,
    score_istina_hypergraph_proxy,
    score_istina_hypergraph_proxy_paper,
)


def _mention(row: dict, index: int):
    return row_to_mention(row, index)


def _toy_mentions():
    rows = [
        {
            "firstname": "Alice",
            "lastname": "Smith",
            "doi": "10.hist/1",
            "year": 2020,
            "affiliation": "Institute A",
            "orcid": "0000-0001-0000-0001",
        },
        {
            "firstname": "Bob",
            "lastname": "Jones",
            "doi": "10.hist/1",
            "year": 2020,
            "affiliation": "Institute A",
            "orcid": "0000-0002-0000-0002",
        },
        {
            "firstname": "Alice",
            "lastname": "Smith",
            "doi": "10.hist/2",
            "year": 2020,
            "affiliation": "Institute X",
            "orcid": "0000-0003-0000-0003",
        },
        {
            "firstname": "Alice",
            "lastname": "Smith",
            "doi": "10.test/1",
            "year": 2022,
            "affiliation": "Institute A",
            "orcid": "0000-0001-0000-0001",
        },
        {
            "firstname": "Bob",
            "lastname": "Jones",
            "doi": "10.test/1",
            "year": 2022,
            "affiliation": "Institute A",
            "orcid": "0000-0002-0000-0002",
        },
    ]
    return [_mention(row, index) for index, row in enumerate(rows)]


def test_candidate_generation_uses_same_family_and_compatible_given_name():
    mentions = _toy_mentions()
    profiles, family_index, _ = build_profiles(mentions, [0, 1, 2])

    candidates = get_candidates(mentions[3], profiles, family_index)

    assert candidates == ["0000-0001-0000-0001", "0000-0003-0000-0003"]


def test_istina_proxy_prefers_candidate_supported_by_current_coauthor_candidates():
    mentions = _toy_mentions()
    profiles, family_index, _ = build_profiles(mentions, [0, 1, 2])
    candidate_sets = {
        3: get_candidates(mentions[3], profiles, family_index),
        4: get_candidates(mentions[4], profiles, family_index),
    }

    prediction = choose_istina_hypergraph_proxy(3, candidate_sets, profiles)

    assert prediction == "0000-0001-0000-0001"


def test_istina_proxy_reports_graph_support():
    mentions = _toy_mentions()
    profiles, family_index, _ = build_profiles(mentions, [0, 1, 2])
    candidate_sets = {
        3: get_candidates(mentions[3], profiles, family_index),
        4: get_candidates(mentions[4], profiles, family_index),
    }

    prediction, support = score_istina_hypergraph_proxy(3, candidate_sets, profiles)

    assert prediction == "0000-0001-0000-0001"
    assert support > 0


def test_paper_level_proxy_does_not_reuse_same_author_for_two_signatures():
    rows = [
        {
            "firstname": "Alice",
            "lastname": "Smith",
            "doi": "10.hist/1",
            "year": 2020,
            "orcid": "0000-0001-0000-0001",
        },
        {
            "firstname": "Alice",
            "lastname": "Smith",
            "doi": "10.hist/2",
            "year": 2020,
            "orcid": "0000-0002-0000-0002",
        },
        {
            "firstname": "Alice",
            "lastname": "Smith",
            "doi": "10.test/1",
            "year": 2022,
            "orcid": "0000-0001-0000-0001",
        },
        {
            "firstname": "Alice",
            "lastname": "Smith",
            "doi": "10.test/1",
            "year": 2022,
            "orcid": "0000-0002-0000-0002",
        },
    ]
    mentions = [_mention(row, index) for index, row in enumerate(rows)]
    profiles, family_index, _ = build_profiles(mentions, [0, 1])
    candidate_sets = {
        2: get_candidates(mentions[2], profiles, family_index),
        3: get_candidates(mentions[3], profiles, family_index),
    }

    predictions = score_istina_hypergraph_proxy_paper([2, 3], candidate_sets, profiles)
    assigned_author_ids = [author_id for author_id, _ in predictions.values()]

    assert len(assigned_author_ids) == 2
    assert len(set(assigned_author_ids)) == 2


def test_risk_controlled_hybrid_prefers_framework_then_supported_graph():
    assert choose_risk_controlled_hybrid("framework-id", "graph-id", 10.0, 1.0) == "framework-id"
    assert choose_risk_controlled_hybrid(None, "graph-id", 1.0, 1.0) == "graph-id"
    assert choose_risk_controlled_hybrid(None, "graph-id", 0.5, 1.0) is None


def test_hard_case_labels_mark_ambiguous_and_graph_supported_cases():
    mentions = _toy_mentions()
    profiles, family_index, _ = build_profiles(mentions, [0, 1, 2])
    candidate_sets = {
        3: get_candidates(mentions[3], profiles, family_index),
        4: get_candidates(mentions[4], profiles, family_index),
    }
    prediction, support = score_istina_hypergraph_proxy(3, candidate_sets, profiles)

    labels = hard_case_labels(
        mentions[3],
        candidate_sets[3],
        profiles,
        truth_in_history=True,
        framework_prediction=None,
        hypergraph_prediction=prediction,
        hypergraph_support=support,
        support_threshold=0.5,
    )

    assert "ambiguous_candidates" in labels
    assert "exact_name_ambiguous" in labels
    assert "graph_supported_candidate" in labels
    assert "framework_unknown_graph_supported" in labels


def test_online_assignment_reports_proxy_metrics():
    result = evaluate_online_assignment(
        _toy_mentions(),
        OnlineBenchmarkConfig(cutoff_year=2021, max_profile_mentions=10),
    )

    assert result["truth_in_history_mentions"] == 2
    assert result["candidate_covered_mentions"] == 2
    assert result["methods"]["istina_hypergraph_proxy"]["correct"] == 2
    assert "risk_controlled_hybrid" in result["methods"]
    assert "ambiguous_candidates" in result["hard_case_linkable_methods"]
