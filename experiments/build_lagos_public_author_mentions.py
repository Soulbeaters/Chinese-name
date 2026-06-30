#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a public LAGOS-AND author-mention dataset for Article 2 validation.

The LAGOS-AND trimmed file is a public ORCID/DOI-based author-name
disambiguation dataset.  ORCID is used only as the evaluation label.  Author
names, affiliations, DOI/paper id, publication year, and coauthor strings are
ordinary bibliographic metadata available to a production import pipeline.
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import random
import tarfile
from pathlib import Path
from typing import Iterable, Iterator


DEFAULT_SOURCE = Path("external_data/lagos_and/LAGOS-AND-BLOCK-TRIMMED.csv.tar.gz")


def split_author_name(value: str) -> tuple[str, str]:
    text = " ".join(str(value or "").replace(".", " ").split())
    if not text:
        return "", ""
    if "," in text:
        family, given = [part.strip() for part in text.split(",", 1)]
        return given, family
    parts = text.split()
    if len(parts) < 2:
        return "", ""
    return " ".join(parts[:-1]), parts[-1]


def parse_list_field(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return [item.strip() for item in text.split(";") if item.strip()]
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def iter_csv_rows(source: Path) -> Iterator[dict[str, str]]:
    if source.suffixes[-2:] == [".tar", ".gz"]:
        with tarfile.open(source, "r:gz") as archive:
            member = next(
                item
                for item in archive.getmembers()
                if item.isfile() and item.name.lower().endswith(".csv")
            )
            extracted = archive.extractfile(member)
            if extracted is None:
                return
            with extracted:
                text_handle = io.TextIOWrapper(
                    extracted,
                    encoding="utf-8",
                    errors="replace",
                    newline="",
                )
                yield from csv.DictReader(text_handle)
    else:
        with source.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            yield from csv.DictReader(handle)


def row_to_record(row: dict[str, str], index: int) -> dict[str, object] | None:
    author_name = str(row.get("author_name", "") or "").strip()
    if not author_name:
        return None
    firstname, lastname = split_author_name(author_name)
    if not firstname or not lastname:
        return None
    orcid = str(row.get("orcid", "") or "").strip()
    if not orcid:
        return None
    pid = str(row.get("pid", "") or "").strip()
    doi = str(row.get("doi", "") or "").strip().lower()
    paper_key = doi or (f"lagos:{pid}" if pid else "")
    if not paper_key:
        return None
    try:
        year = int(str(row.get("pub_year", "") or ""))
    except ValueError:
        year = None
    return {
        "id": f"lagos:{pid or index}:{row.get('author_position', '')}",
        "firstname": firstname,
        "lastname": lastname,
        "original_name": author_name,
        "doi": doi,
        "article_id": f"lagos:{pid}" if pid else paper_key,
        "year": year,
        "affiliation": str(row.get("author_affiliation", "") or "").strip(),
        "coauthors": parse_list_field(str(row.get("coauthors", "") or "")),
        "orcid": orcid,
        "source": "lagos-and-block-trimmed",
        "split": str(row.get("train1_test0_val2", "") or "").strip(),
    }


def reservoir_sample(
    items: Iterable[dict[str, object]],
    max_mentions: int,
    seed: int,
) -> list[dict[str, object]]:
    rng = random.Random(seed)
    sample: list[dict[str, object]] = []
    seen = 0
    for item in items:
        seen += 1
        if len(sample) < max_mentions:
            sample.append(item)
            continue
        replacement = rng.randrange(seen)
        if replacement < max_mentions:
            sample[replacement] = item
    sample.sort(key=lambda record: str(record["id"]))
    return sample


def build_records(source: Path, max_mentions: int, seed: int) -> list[dict[str, object]]:
    def records() -> Iterator[dict[str, object]]:
        for index, row in enumerate(iter_csv_rows(source)):
            record = row_to_record(row, index)
            if record is not None:
                yield record

    return reservoir_sample(records(), max_mentions, seed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-mentions", type=int, default=80000)
    parser.add_argument("--seed", type=int, default=20260701)
    args = parser.parse_args()

    records = build_records(args.source, args.max_mentions, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "output": str(args.output),
                "records": len(records),
                "unique_orcid": len({record["orcid"] for record in records}),
                "unique_papers": len({record["doi"] or record["article_id"] for record in records}),
                "source": str(args.source),
                "seed": args.seed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
