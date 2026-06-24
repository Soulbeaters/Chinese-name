#!/usr/bin/env python3
"""Build a frozen, non-overlapping structured-name evaluation set from Wikidata."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluate_mentor_large_scale import normalized_tokens  # noqa: E402


ENDPOINT = "https://query.wikidata.org/sparql"
SIMPLE_LATIN_NAME = re.compile(r"^[A-Za-z]+(?:[-'][A-Za-z]+)*$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_bindings(limit: int, offset: int) -> tuple[list[dict], str, str]:
    query = f"""SELECT DISTINCT ?person ?givenLabel ?familyLabel WHERE {{
  ?person wdt:P31 wd:Q5;
          wdt:P735 ?given;
          wdt:P734 ?family.
  ?given rdfs:label ?givenLabel.
  ?family rdfs:label ?familyLabel.
  FILTER(LANG(?givenLabel) = "en")
  FILTER(LANG(?familyLabel) = "en")
}}
LIMIT {limit}
OFFSET {offset}"""
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query})
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/csv",
            "User-Agent": "Chinese-name-research/1.0 (academic reproducibility)",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read()
    bindings = list(csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace"))))
    return bindings, query, sha256_bytes(raw)


def load_seen_pairs(path: Path) -> set[tuple[tuple[str, ...], tuple[str, ...]]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {
        (
            normalized_tokens(str(row.get("firstname", ""))),
            normalized_tokens(str(row.get("lastname", ""))),
        )
        for row in rows
        if row.get("firstname") and row.get("lastname")
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exclude-dataset", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    bindings, query, response_sha256 = fetch_bindings(args.limit, args.offset)
    seen_pairs = set().union(*(load_seen_pairs(path) for path in args.exclude_dataset))
    records_by_pair: dict[tuple[tuple[str, ...], tuple[str, ...]], dict] = {}
    rejected_non_latin = 0
    rejected_overlap = 0
    for binding in bindings:
        given = binding["givenLabel"].strip()
        family = binding["familyLabel"].strip()
        if not SIMPLE_LATIN_NAME.fullmatch(given) or not SIMPLE_LATIN_NAME.fullmatch(
            family
        ):
            rejected_non_latin += 1
            continue
        pair = (normalized_tokens(given), normalized_tokens(family))
        if not pair[0] or not pair[1] or pair in seen_pairs:
            rejected_overlap += 1
            continue
        records_by_pair.setdefault(
            pair,
            {
                "firstname": given,
                "lastname": family,
                "orcid": binding["person"],
                "source_record": binding["person"],
            },
        )

    records = list(records_by_pair.values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8")
    args.output.write_bytes(encoded)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Wikidata Query Service",
        "endpoint": ENDPOINT,
        "license": "CC0-1.0",
        "properties": {"given_name": "P735", "family_name": "P734"},
        "query": query,
        "query_limit": args.limit,
        "query_offset": args.offset,
        "raw_bindings": len(bindings),
        "rejected_non_latin_or_compound": rejected_non_latin,
        "rejected_local_pair_overlap": rejected_overlap,
        "unique_output_pairs": len(records),
        "response_sha256": response_sha256,
        "output_sha256": sha256_bytes(encoded),
        "excluded_datasets": [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in args.exclude_dataset
        ],
        "evaluation_note": (
            "Names are structured by Wikidata P735/P734. Both display orders are generated "
            "during evaluation; no Wikidata record is used to train or tune the model."
        ),
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
