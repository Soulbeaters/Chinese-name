# -*- coding: utf-8 -*-
"""Build a leakage-controlled token role model from split-name metadata."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluate_mentor_large_scale import (
    load_candidates,
    name_pair_bucket,
    normalized_tokens,
    sha256_file,
)


def single_token_key(value: object) -> str | None:
    tokens = normalized_tokens(str(value))
    return tokens[0] if len(tokens) == 1 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-support", type=int, default=3)
    args = parser.parse_args()

    rows = load_candidates(args.dataset)
    train_rows = [row for row in rows if name_pair_bucket(row) < 3]
    surname_counts: Counter[str] = Counter()
    given_counts: Counter[str] = Counter()
    for row in train_rows:
        surname = single_token_key(row["lastname"])
        given = single_token_key(row["firstname"])
        if surname:
            surname_counts[surname] += 1
        if given:
            given_counts[given] += 1

    counts = {
        token: [surname_counts[token], given_counts[token]]
        for token in sorted(set(surname_counts) | set(given_counts))
        if surname_counts[token] + given_counts[token] >= args.min_support
    }
    result = {
        "dataset_sha256": sha256_file(args.dataset),
        "split": "normalized_name_pair_sha256_mod5_buckets_0_1_2",
        "candidate_records": len(rows),
        "train_records": len(train_rows),
        "min_support": args.min_support,
        "token_count": len(counts),
        "counts": counts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in result.items() if key != "counts"}, indent=2))


if __name__ == "__main__":
    main()
