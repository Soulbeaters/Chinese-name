# -*- coding: utf-8 -*-
"""Tests for LAGOS-AND public author-mention dataset builder."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.build_lagos_public_author_mentions import (  # noqa: E402
    parse_list_field,
    row_to_record,
    split_author_name,
)


def test_split_author_name_handles_initials_and_comma_forms():
    assert split_author_name("B. Rajakumar") == ("B", "Rajakumar")
    assert split_author_name("Rajakumar, Balla") == ("Balla", "Rajakumar")


def test_parse_list_field_handles_python_style_lists():
    assert parse_list_field("['A. Parandaman','B. Rajakumar']") == [
        "A. Parandaman",
        "B. Rajakumar",
    ]


def test_row_to_record_preserves_orcid_as_label_and_coauthors_as_metadata():
    record = row_to_record(
        {
            "orcid": "0000-0003-0788-1499",
            "doi": "10.1021/acs.jpca.6b06386",
            "pid": "2462355537",
            "author_position": "2",
            "author_name": "B. Rajakumar",
            "author_affiliation": "Department of Chemistry",
            "coauthors": "['A. Parandaman','B. Rajakumar']",
            "pub_year": "2016",
            "train1_test0_val2": "2",
        },
        0,
    )

    assert record is not None
    assert record["firstname"] == "B"
    assert record["lastname"] == "Rajakumar"
    assert record["orcid"] == "0000-0003-0788-1499"
    assert record["coauthors"] == ["A. Parandaman", "B. Rajakumar"]
