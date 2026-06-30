# -*- coding: utf-8 -*-
"""Tests for DBLP public author-mention dataset builder."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.build_dblp_public_author_mentions import (  # noqa: E402
    clean_author_name,
    extract_doi,
    label_author,
    split_name,
)


def test_dblp_suffix_is_removed_from_features_but_can_remain_label():
    assert clean_author_name("Manish Singh 0001") == "Manish Singh"
    assert split_name("Manish Singh 0001") == ("Manish", "Singh")


def test_extracts_doi_from_dblp_ee_values():
    assert (
        extract_doi(["https://doi.org/10.1007/978-0-387-31439-6_559"])
        == "10.1007/978-0-387-31439-6_559"
    )


def test_prefers_stable_dblp_pid_for_gold_label():
    assert label_author("Manish Singh 0001", "12/3456") == "dblp-pid:12/3456"
    assert label_author("Manish Singh 0001", "") == "dblp-name:manish singh 0001"
