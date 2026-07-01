#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build public S2AND author-mention datasets for Article 2 validation.

S2AND cluster ids are used only as evaluation labels.  The matching algorithm
receives bibliographic metadata: author name, affiliation, paper id, year, and
coauthor names.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_ROOT = Path("external_data/s2and")


def full_name_from_author_info(author_info: dict[str, Any]) -> str:
    parts = [
        str(author_info.get("first") or "").strip(),
        str(author_info.get("middle") or "").strip(),
        str(author_info.get("last") or "").strip(),
    ]
    return " ".join(part for part in parts if part)


def label_by_signature(clusters: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for cluster_id, cluster in clusters.items():
        label = str(cluster.get("cluster_id") or cluster_id)
        for signature_id in cluster.get("signature_ids", []):
            labels[str(signature_id)] = f"s2and:{label.lower()}"
    return labels


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_dataset_records(source_root: Path, dataset: str) -> list[dict[str, object]]:
    dataset_root = source_root / dataset
    signatures = load_json(dataset_root / f"{dataset}_signatures.json")
    papers = load_json(dataset_root / f"{dataset}_papers.json")
    clusters = load_json(dataset_root / f"{dataset}_clusters.json")
    labels = label_by_signature(clusters)

    records: list[dict[str, object]] = []
    for signature_id, signature in sorted(signatures.items(), key=lambda item: str(item[0])):
        label = labels.get(str(signature_id))
        if not label:
            continue
        author_info = signature.get("author_info") or {}
        first = str(author_info.get("first") or "").strip()
        middle = str(author_info.get("middle") or "").strip()
        last = str(author_info.get("last") or "").strip()
        if not first or not last:
            continue
        paper_id = str(signature.get("paper_id") or "")
        paper = papers.get(paper_id)
        if paper is None and paper_id.isdigit():
            paper = papers.get(int(paper_id))
        if not paper:
            continue
        authors = paper.get("authors") or []
        position = author_info.get("position")
        original_name = ""
        coauthors: list[str] = []
        for author in authors:
            author_name = str(author.get("author_name") or "").strip()
            if not author_name:
                continue
            if position is not None and author.get("position") == position:
                original_name = author_name
            else:
                coauthors.append(author_name)
        if not original_name:
            original_name = full_name_from_author_info(author_info)
        affiliation_values = [
            str(item).strip()
            for item in (author_info.get("affiliations") or [])
            if str(item).strip()
        ]
        firstname = " ".join(part for part in [first, middle] if part)
        records.append(
            {
                "id": f"s2and:{dataset}:{signature_id}",
                "firstname": firstname,
                "lastname": last,
                "original_name": original_name,
                "doi": "",
                "article_id": f"s2and:{dataset}:{paper_id}",
                "year": paper.get("year"),
                "affiliation": "; ".join(affiliation_values),
                "coauthors": coauthors,
                "orcid": label,
                "source": f"s2and-{dataset}",
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["qian", "arnetminer", "zbmath"],
    )
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    dataset_summaries: list[dict[str, object]] = []
    for dataset in args.datasets:
        dataset_records = build_dataset_records(args.source_root, dataset)
        records.extend(dataset_records)
        dataset_summaries.append(
            {
                "dataset": dataset,
                "records": len(dataset_records),
                "unique_labels": len({record["orcid"] for record in dataset_records}),
                "unique_papers": len({record["article_id"] for record in dataset_records}),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "records": len(records),
                "unique_labels": len({record["orcid"] for record in records}),
                "unique_papers": len({record["article_id"] for record in records}),
                "datasets": dataset_summaries,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
