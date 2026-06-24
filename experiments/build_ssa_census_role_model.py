#!/usr/bin/env python3
"""Build a frozen surname/given-name role model from official US data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import defaultdict
from pathlib import Path


SSA_SOURCE_URL = "https://www.ssa.gov/oact/babynames/names.zip"
CENSUS_SOURCE_URL = "https://www2.census.gov/topics/genealogy/2010surnames/names.zip"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_given_counts(path: Path) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    with zipfile.ZipFile(path) as archive:
        for filename in archive.namelist():
            if not (filename.startswith("yob") and filename.endswith(".txt")):
                continue
            for raw_line in archive.read(filename).decode("utf-8").splitlines():
                name, _sex, count = raw_line.split(",")
                counts[name.lower()] += int(count)
    return dict(counts)


def load_surname_counts(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("name") and row.get("count"):
                counts[row["name"].lower()] = int(row["count"])
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ssa-zip", type=Path, required=True)
    parser.add_argument("--census-zip", type=Path, required=True)
    parser.add_argument("--census-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    given_counts = load_given_counts(args.ssa_zip)
    surname_counts = load_surname_counts(args.census_csv)
    vocabulary = sorted(set(given_counts) | set(surname_counts))
    payload = {
        "version": 1,
        "description": "Frozen token role counts from SSA given names and 2010 US Census surnames.",
        "sources": {
            "ssa_national_names": {
                "url": SSA_SOURCE_URL,
                "sha256": sha256_file(args.ssa_zip),
            },
            "census_2010_surnames": {
                "url": CENSUS_SOURCE_URL,
                "archive_sha256": sha256_file(args.census_zip),
                "extracted_csv_sha256": sha256_file(args.census_csv),
            },
        },
        "totals": {
            "given": sum(given_counts.values()),
            "surname": sum(surname_counts.values()),
            "vocabulary": len(vocabulary),
        },
        "counts": {
            token: [surname_counts.get(token, 0), given_counts.get(token, 0)]
            for token in vocabulary
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), **payload["totals"]}, indent=2))


if __name__ == "__main__":
    main()
