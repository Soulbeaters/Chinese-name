# -*- coding: utf-8 -*-
"""Tests for S2AND public author-mention dataset builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.build_s2and_public_author_mentions import (  # noqa: E402
    build_dataset_records,
    full_name_from_author_info,
    label_by_signature,
)


def test_label_by_signature_uses_cluster_ids_as_gold_labels():
    labels = label_by_signature(
        {
            "cluster-a": {
                "cluster_id": "Person_A",
                "signature_ids": ["1", "2"],
            }
        }
    )

    assert labels == {"1": "s2and:person_a", "2": "s2and:person_a"}


def test_full_name_from_author_info_joins_available_parts():
    assert (
        full_name_from_author_info({"first": "Jane", "middle": "Q.", "last": "Smith"})
        == "Jane Q. Smith"
    )


def test_build_dataset_records_maps_s2and_metadata(tmp_path):
    dataset_root = tmp_path / "toy"
    dataset_root.mkdir()
    (dataset_root / "toy_signatures.json").write_text(
        json.dumps(
            {
                "s1": {
                    "paper_id": 10,
                    "signature_id": "s1",
                    "author_info": {
                        "position": 1,
                        "first": "Jane",
                        "middle": "Q.",
                        "last": "Smith",
                        "affiliations": ["Example University"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (dataset_root / "toy_papers.json").write_text(
        json.dumps(
            {
                "10": {
                    "paper_id": 10,
                    "year": 2020,
                    "authors": [
                        {"position": 0, "author_name": "John Doe"},
                        {"position": 1, "author_name": "J. Q. Smith"},
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    (dataset_root / "toy_clusters.json").write_text(
        json.dumps(
            {
                "c1": {
                    "cluster_id": "Cluster_1",
                    "signature_ids": ["s1"],
                }
            }
        ),
        encoding="utf-8",
    )

    records = build_dataset_records(tmp_path, "toy")

    assert records == [
        {
            "id": "s2and:toy:s1",
            "firstname": "Jane Q.",
            "lastname": "Smith",
            "original_name": "J. Q. Smith",
            "doi": "",
            "article_id": "s2and:toy:10",
            "year": 2020,
            "affiliation": "Example University",
            "coauthors": ["John Doe"],
            "orcid": "s2and:cluster_1",
            "source": "s2and-toy",
        }
    ]


def test_build_dataset_records_keeps_nonnumeric_paper_ids(tmp_path):
    dataset_root = tmp_path / "toy"
    dataset_root.mkdir()
    (dataset_root / "toy_signatures.json").write_text(
        json.dumps(
            {
                "s1": {
                    "paper_id": "paper-alpha",
                    "signature_id": "s1",
                    "author_info": {
                        "position": 0,
                        "first": "Ada",
                        "middle": "",
                        "last": "Lovelace",
                        "affiliations": [],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (dataset_root / "toy_papers.json").write_text(
        json.dumps(
            {
                "paper-alpha": {
                    "paper_id": "paper-alpha",
                    "year": 1843,
                    "authors": [{"position": 0, "author_name": "Ada Lovelace"}],
                }
            }
        ),
        encoding="utf-8",
    )
    (dataset_root / "toy_clusters.json").write_text(
        json.dumps({"c1": {"cluster_id": "Cluster_1", "signature_ids": ["s1"]}}),
        encoding="utf-8",
    )

    records = build_dataset_records(tmp_path, "toy")

    assert len(records) == 1
    assert records[0]["article_id"] == "s2and:toy:paper-alpha"
