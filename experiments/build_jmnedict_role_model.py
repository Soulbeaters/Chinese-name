# -*- coding: utf-8 -*-
"""Build romanized surname/given role counts from JMnedict."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluate_mentor_large_scale import normalized_tokens


SURNAME_TYPES = {"family or surname"}
GIVEN_TYPES = {
    "given name or forename, gender not specified",
    "female given name or forename",
    "male given name or forename",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def single_ascii_token(value: str) -> str | None:
    tokens = normalized_tokens(value)
    if len(tokens) == 1 and tokens[0].isalpha():
        return tokens[0]
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    surname_counts: Counter[str] = Counter()
    given_counts: Counter[str] = Counter()
    with gzip.open(args.input, "rb") as handle:
        for _, entry in ET.iterparse(handle, events=("end",)):
            if entry.tag != "entry":
                continue
            name_types = {node.text for node in entry.findall("./trans/name_type")}
            for node in entry.findall("./trans/trans_det"):
                token = single_ascii_token(node.text or "")
                if not token:
                    continue
                if name_types & SURNAME_TYPES:
                    surname_counts[token] += 1
                if name_types & GIVEN_TYPES:
                    given_counts[token] += 1
            entry.clear()

    counts = {
        token: [surname_counts[token], given_counts[token]]
        for token in sorted(set(surname_counts) | set(given_counts))
    }
    payload = {
        "source": "JMnedict",
        "source_sha256": sha256_file(args.input),
        "source_documentation": "https://www.edrdg.org/enamdict/enamdict_doc.html",
        "license": "CC BY-SA 4.0; see data/JMNEDICT_ATTRIBUTION.md",
        "surname_token_count": len(surname_counts),
        "given_token_count": len(given_counts),
        "overlap_token_count": len(set(surname_counts) & set(given_counts)),
        "counts": counts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "counts"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
