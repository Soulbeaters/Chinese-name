# -*- coding: utf-8 -*-
"""Tests for supervised author-linker feature export."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.export_author_linker_features import (  # noqa: E402
    export_dataset_features,
    write_jsonl,
)


def test_export_dataset_features_without_label_leakage(tmp_path):
    dataset = tmp_path / "authors.json"
    dataset.write_text(
        json.dumps(
            [
                {
                    "id": "m1",
                    "firstname": "Jane",
                    "lastname": "Smith",
                    "doi": "10.test/a",
                    "year": 2020,
                    "affiliation": "Example University Graph Lab",
                    "orcid": "0000-0001-0000-0001",
                    "coauthors": ["John Doe"],
                },
                {
                    "id": "m2",
                    "firstname": "Jane",
                    "lastname": "Smith",
                    "doi": "10.test/b",
                    "year": 2021,
                    "affiliation": "Example University Graph Laboratory",
                    "orcid": "0000-0001-0000-0001",
                    "coauthors": ["John Doe"],
                },
                {
                    "id": "m3",
                    "firstname": "Jane",
                    "lastname": "Smith",
                    "doi": "10.test/c",
                    "year": 2022,
                    "affiliation": "Different Hospital",
                    "orcid": "0000-0002-0000-0002",
                    "coauthors": ["Alice Roe"],
                },
                {
                    "id": "m4",
                    "firstname": "Jane",
                    "lastname": "Smith",
                    "doi": "10.test/a",
                    "year": 2020,
                    "affiliation": "Example University Graph Lab",
                    "orcid": "0000-0003-0000-0003",
                    "coauthors": ["Jane Smith"],
                },
            ]
        ),
        encoding="utf-8",
    )

    rows, manifest = export_dataset_features(
        dataset,
        "toy",
        max_block_size=20,
        max_pairs=10,
        negative_positive_ratio=2,
        seed=7,
    )

    assert manifest["labeled_mentions"] == 4
    assert manifest["same_paper_skipped_pairs"] == 1
    assert manifest["exported_positive_pairs"] == 1
    assert manifest["exported_negative_pairs"] >= 1
    assert any(row["same_author"] for row in rows)
    assert any(not row["same_author"] for row in rows)
    assert all("orcid" not in key.lower() for row in rows for key in row)
    assert rows[0]["dataset"] == "toy"
    assert "framework_balanced_rule" in rows[0]


def test_write_jsonl_round_trips_rows(tmp_path):
    output = tmp_path / "features.jsonl"
    rows = [
        {"dataset": "toy", "same_author": True, "affiliation_jaccard": 1.0},
        {"dataset": "toy", "same_author": False, "affiliation_jaccard": 0.0},
    ]

    write_jsonl(output, rows)

    loaded = [
        json.loads(line)
        for line in output.read_text(encoding="utf-8").splitlines()
    ]
    assert loaded == rows
