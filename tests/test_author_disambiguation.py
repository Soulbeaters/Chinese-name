# -*- coding: utf-8 -*-
"""Tests for the article-2 author-disambiguation framework."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.author_disambiguation import (  # noqa: E402
    DisambiguationConfig,
    affiliation_tokens,
    build_affiliation_weights,
    build_coauthor_sets,
    decide_pair,
    evaluate_mentions,
    row_to_mention,
)


def _mention(row: dict, index: int = 0):
    return row_to_mention(row, index)


def _decision(left, right, algorithm="framework_v1"):
    mentions = [left, right]
    weights = build_affiliation_weights(mentions)
    coauthors = build_coauthor_sets(mentions)
    return decide_pair(
        left,
        right,
        affiliation_tokens(left.affiliation),
        affiliation_tokens(right.affiliation),
        coauthors[0],
        coauthors[1],
        weights,
        DisambiguationConfig(algorithm=algorithm),
    )


def test_exact_non_chinese_name_same_specific_affiliation_merges():
    left = _mention(
        {
            "firstname": "Ivan",
            "lastname": "Topisirovic",
            "doi": "10.test/a",
            "year": 2022,
            "affiliation": "Molecular Biology Program, McGill University, Montreal",
            "orcid": "0000-0002-5510-9762",
        },
        0,
    )
    right = _mention(
        {
            "firstname": "Ivan",
            "lastname": "Topisirovic",
            "doi": "10.test/b",
            "year": 2025,
            "affiliation": "Molecular Biology Program, McGill University, Montreal",
            "orcid": "0000-0002-5510-9762",
        },
        1,
    )
    decision = _decision(left, right)
    assert decision.same_author is True
    assert decision.rule == "exact_name_weighted_affiliation_ge_0.42"


def test_chinese_like_same_name_requires_stronger_context_than_affiliation_only():
    left = _mention(
        {
            "firstname": "Wei",
            "lastname": "Li",
            "doi": "10.test/a",
            "year": 2024,
            "affiliation": "Department of Materials Science, Tsinghua University",
            "orcid": "0000-0001-0000-0001",
        },
        0,
    )
    right = _mention(
        {
            "firstname": "Wei",
            "lastname": "Li",
            "doi": "10.test/b",
            "year": 2024,
            "affiliation": "Department of Materials Science, Tsinghua University",
            "orcid": "0000-0002-0000-0002",
        },
        1,
    )
    decision = _decision(left, right)
    assert decision.same_author is False
    assert decision.rule == "cn_like_exact_name_requires_coauthor_or_very_strong_context"


def test_exact_non_chinese_full_name_merges_without_context():
    left = _mention(
        {
            "firstname": "Ivan",
            "lastname": "Topisirovic",
            "doi": "10.test/a",
            "year": 2022,
            "affiliation": "",
            "orcid": "0000-0002-5510-9762",
        },
        0,
    )
    right = _mention(
        {
            "firstname": "Ivan",
            "lastname": "Topisirovic",
            "doi": "10.test/b",
            "year": 2025,
            "affiliation": "",
            "orcid": "0000-0002-5510-9762",
        },
        1,
    )
    decision = _decision(left, right)
    assert decision.same_author is True
    assert decision.rule == "exact_non_chinese_full_name"


def test_given_prefix_variant_merges_under_strong_affiliation():
    left = _mention(
        {
            "firstname": "Vyacheslav",
            "lastname": "Trofimov",
            "doi": "10.test/a",
            "year": 2025,
            "affiliation": "Baikov Institute of Metallurgy and Materials Science",
            "orcid": "0000-0002-0314-6545",
        },
        0,
    )
    right = _mention(
        {
            "firstname": "Vyacheslav A.",
            "lastname": "Trofimov",
            "doi": "10.test/b",
            "year": 2023,
            "affiliation": "Baikov Institute of Metallurgy and Materials Science",
            "orcid": "0000-0002-0314-6545",
        },
        1,
    )
    decision = _decision(left, right)
    assert decision.same_author is True
    assert decision.features.given_relation == "prefix"


def test_same_family_initial_without_context_does_not_merge():
    left = _mention(
        {
            "firstname": "W.",
            "lastname": "Li",
            "doi": "10.test/a",
            "year": 2017,
            "affiliation": "Space Physics Laboratory",
            "orcid": "0000-0003-1920-2406",
        },
        0,
    )
    right = _mention(
        {
            "firstname": "Wei",
            "lastname": "Li",
            "doi": "10.test/b",
            "year": 2019,
            "affiliation": "Materials Research Center",
            "orcid": "0000-0003-3495-4550",
        },
        1,
    )
    decision = _decision(left, right)
    assert decision.same_author is False
    assert decision.features.given_relation == "initial_compatible"


def test_orcid_is_label_only_not_decision_feature():
    left_row = {
        "firstname": "Alex",
        "lastname": "Smith",
        "doi": "10.test/a",
        "year": 2020,
        "affiliation": "Unrelated A",
        "orcid": "0000-0001-1111-1111",
    }
    right_row = {
        "firstname": "Alex",
        "lastname": "Smith",
        "doi": "10.test/b",
        "year": 2021,
        "affiliation": "Unrelated B",
        "orcid": "0000-0001-1111-1111",
    }
    same_label_decision = _decision(_mention(left_row, 0), _mention(right_row, 1))
    changed = dict(right_row)
    changed["orcid"] = "0000-0002-2222-2222"
    different_label_decision = _decision(_mention(left_row, 0), _mention(changed, 1))

    assert same_label_decision.same_author == different_label_decision.same_author
    assert same_label_decision.rule == different_label_decision.rule


def test_evaluate_mentions_reports_cluster_metrics():
    rows = [
        {
            "firstname": "Ivan",
            "lastname": "Topisirovic",
            "doi": "10.test/a",
            "year": 2022,
            "affiliation": "McGill Molecular Biology Program",
            "orcid": "0000-0002-5510-9762",
        },
        {
            "firstname": "Ivan",
            "lastname": "Topisirovic",
            "doi": "10.test/b",
            "year": 2025,
            "affiliation": "McGill Molecular Biology Program",
            "orcid": "0000-0002-5510-9762",
        },
        {
            "firstname": "Ivan",
            "lastname": "Topisirovic",
            "doi": "10.test/c",
            "year": 2025,
            "affiliation": "Other Institute",
            "orcid": "0000-0003-0000-0000",
        },
    ]
    result = evaluate_mentions(
        [_mention(row, index) for index, row in enumerate(rows)],
        DisambiguationConfig(),
    )
    assert result["candidate_pairwise"]["tp"] == 1
    assert result["cluster_pairwise"]["tp"] == 1
    assert result["b_cubed"]["f1"] > 0


def test_large_blocks_use_exact_name_subblocks_instead_of_full_skip():
    rows = [
        {
            "firstname": "Alex",
            "lastname": "Smith",
            "doi": "10.test/a",
            "year": 2020,
            "affiliation": "Specific Institute",
            "orcid": "0000-0001-0000-0001",
        },
        {
            "firstname": "Alex",
            "lastname": "Smith",
            "doi": "10.test/b",
            "year": 2021,
            "affiliation": "Specific Institute",
            "orcid": "0000-0001-0000-0001",
        },
        {
            "firstname": "Alice",
            "lastname": "Smith",
            "doi": "10.test/c",
            "year": 2021,
            "affiliation": "Other Institute",
            "orcid": "0000-0002-0000-0002",
        },
        {
            "firstname": "Andrew",
            "lastname": "Smith",
            "doi": "10.test/d",
            "year": 2021,
            "affiliation": "Other Institute",
            "orcid": "0000-0003-0000-0003",
        },
    ]
    result = evaluate_mentions(
        [_mention(row, index) for index, row in enumerate(rows)],
        DisambiguationConfig(max_block_size=3),
    )

    assert result["skipped_large_blocks"] == 1
    assert result["large_block_exact_subblocks"] == 1
    assert result["large_block_exact_subblock_candidate_pairs"] == 1
    assert result["evaluated_pairs"] == 1
    assert result["candidate_pairwise"]["tp"] == 1
