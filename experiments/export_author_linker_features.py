#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export supervised author-linker features from labeled author-mention datasets.

The exported JSONL file is intended for the next low-UNKNOWN iteration.  Labels
are used only to create the `same_author` target; ORCID/cluster ids are not
written as model features.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.author_disambiguation import (  # noqa: E402
    DisambiguationConfig,
    affiliation_tokens,
    build_affiliation_weights,
    build_blocks,
    build_coauthor_sets,
    decide_pair,
    exact_name_subblocks,
    is_initial_only_given,
    load_labeled_mentions,
    n_choose_2,
    sha256_file,
)


def reservoir_index(seen: int, limit: int, rng: random.Random) -> int | None:
    if limit <= 0:
        return None
    if seen <= limit:
        return seen - 1
    index = rng.randrange(seen)
    return index if index < limit else None


def pair_feature_row(
    dataset_label: str,
    block: str,
    left_position: int,
    right_position: int,
    context: dict[str, Any],
) -> dict[str, object]:
    mentions = context["mentions"]
    affiliations = context["affiliations"]
    coauthors = context["coauthors"]
    affiliation_weights = context["affiliation_weights"]
    family_frequencies = context["family_frequencies"]
    left = mentions[left_position]
    right = mentions[right_position]
    family_frequency = family_frequencies[left.family_key]

    decisions = {
        "baseline": decide_pair(
            left,
            right,
            affiliations[left_position],
            affiliations[right_position],
            coauthors[left_position],
            coauthors[right_position],
            affiliation_weights,
            DisambiguationConfig(algorithm="baseline_exact_context"),
            family_frequency,
        ),
        "framework_conservative": decide_pair(
            left,
            right,
            affiliations[left_position],
            affiliations[right_position],
            coauthors[left_position],
            coauthors[right_position],
            affiliation_weights,
            DisambiguationConfig(algorithm="framework_v1", profile="conservative"),
            family_frequency,
        ),
        "framework_balanced": decide_pair(
            left,
            right,
            affiliations[left_position],
            affiliations[right_position],
            coauthors[left_position],
            coauthors[right_position],
            affiliation_weights,
            DisambiguationConfig(algorithm="framework_v1", profile="balanced"),
            family_frequency,
        ),
        "framework_strict": decide_pair(
            left,
            right,
            affiliations[left_position],
            affiliations[right_position],
            coauthors[left_position],
            coauthors[right_position],
            affiliation_weights,
            DisambiguationConfig(algorithm="framework_v1", profile="strict"),
            family_frequency,
        ),
    }
    features = decisions["framework_balanced"].features
    same_author = left.label_orcid == right.label_orcid
    year_gap = -1 if features.year_gap is None else features.year_gap
    return {
        "dataset": dataset_label,
        "block": block,
        "left_mention_id": left.mention_id,
        "right_mention_id": right.mention_id,
        "same_author": same_author,
        "same_family": features.same_family,
        "given_relation": features.given_relation,
        "exact_canonical_name": features.exact_canonical_name,
        "name_is_chinese_like": features.name_is_chinese_like,
        "either_initial_only": (
            is_initial_only_given(left.given_tokens)
            or is_initial_only_given(right.given_tokens)
        ),
        "affiliation_jaccard": features.affiliation_jaccard,
        "affiliation_weighted_jaccard": features.affiliation_weighted_jaccard,
        "coauthor_jaccard": features.coauthor_jaccard,
        "year_gap": year_gap,
        "family_frequency": features.family_frequency,
        "left_year": left.year,
        "right_year": right.year,
        "left_has_affiliation": bool(left.affiliation.strip()),
        "right_has_affiliation": bool(right.affiliation.strip()),
        "left_coauthor_count": len(coauthors[left_position]),
        "right_coauthor_count": len(coauthors[right_position]),
        "baseline_same": decisions["baseline"].same_author,
        "baseline_rule": decisions["baseline"].rule,
        "baseline_score": decisions["baseline"].score,
        "framework_conservative_same": decisions["framework_conservative"].same_author,
        "framework_conservative_rule": decisions["framework_conservative"].rule,
        "framework_conservative_score": decisions["framework_conservative"].score,
        "framework_balanced_same": decisions["framework_balanced"].same_author,
        "framework_balanced_rule": decisions["framework_balanced"].rule,
        "framework_balanced_score": decisions["framework_balanced"].score,
        "framework_strict_same": decisions["framework_strict"].same_author,
        "framework_strict_rule": decisions["framework_strict"].rule,
        "framework_strict_score": decisions["framework_strict"].score,
    }


def export_dataset_features(
    dataset_path: Path,
    dataset_label: str,
    max_block_size: int,
    max_pairs: int,
    negative_positive_ratio: int,
    seed: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    mentions = load_labeled_mentions(dataset_path)
    blocks = build_blocks(mentions)
    context = {
        "mentions": mentions,
        "affiliations": {
            position: affiliation_tokens(mention.affiliation)
            for position, mention in enumerate(mentions)
        },
        "coauthors": build_coauthor_sets(mentions),
        "affiliation_weights": build_affiliation_weights(mentions),
        "family_frequencies": Counter(mention.family_key for mention in mentions),
    }

    positive_limit = max_pairs // (negative_positive_ratio + 1)
    negative_limit = max_pairs - positive_limit
    positives: list[dict[str, object]] = []
    negatives: list[dict[str, object]] = []
    rng = random.Random(seed)
    counts: Counter[str] = Counter()

    for block, positions in blocks.items():
        candidate_groups = [positions]
        if len(positions) > max_block_size:
            counts["skipped_large_blocks"] += 1
            candidate_groups = [
                group
                for group in exact_name_subblocks(mentions, positions)
                if len(group) <= max_block_size
            ]
            counts["large_block_exact_subblocks"] += len(candidate_groups)
            counts["large_block_exact_subblock_candidate_pairs"] += sum(
                n_choose_2(len(group)) for group in candidate_groups
            )

        for candidate_positions in candidate_groups:
            for left_position, right_position in combinations(candidate_positions, 2):
                left = mentions[left_position]
                right = mentions[right_position]
                if left.paper_key and left.paper_key == right.paper_key:
                    counts["same_paper_skipped_pairs"] += 1
                    continue
                same_author = left.label_orcid == right.label_orcid
                bucket = positives if same_author else negatives
                limit = positive_limit if same_author else negative_limit
                key = "positive_pairs_seen" if same_author else "negative_pairs_seen"
                counts[key] += 1
                index = reservoir_index(counts[key], limit, rng)
                if index is None:
                    continue
                row = pair_feature_row(
                    dataset_label,
                    block,
                    left_position,
                    right_position,
                    context,
                )
                if index == len(bucket):
                    bucket.append(row)
                else:
                    bucket[index] = row

    rows = positives + negatives
    rows.sort(
        key=lambda row: (
            str(row["dataset"]),
            str(row["block"]),
            str(row["left_mention_id"]),
            str(row["right_mention_id"]),
        )
    )
    manifest = {
        "dataset": str(dataset_path),
        "dataset_label": dataset_label,
        "dataset_sha256": sha256_file(dataset_path),
        "labeled_mentions": len(mentions),
        "unique_labels": len({mention.label_orcid for mention in mentions}),
        "blocks": len(blocks),
        "max_block_size": max_block_size,
        "max_pairs": max_pairs,
        "negative_positive_ratio": negative_positive_ratio,
        "positive_pairs_seen": counts["positive_pairs_seen"],
        "negative_pairs_seen": counts["negative_pairs_seen"],
        "same_paper_skipped_pairs": counts["same_paper_skipped_pairs"],
        "skipped_large_blocks": counts["skipped_large_blocks"],
        "large_block_exact_subblocks": counts["large_block_exact_subblocks"],
        "large_block_exact_subblock_candidate_pairs": counts[
            "large_block_exact_subblock_candidate_pairs"
        ],
        "exported_positive_pairs": len(positives),
        "exported_negative_pairs": len(negatives),
        "exported_pairs": len(rows),
    }
    return rows, manifest


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument(
        "--dataset",
        nargs=2,
        action="append",
        metavar=("LABEL", "PATH"),
        required=True,
    )
    parser.add_argument("--max-block-size", type=int, default=200)
    parser.add_argument("--max-pairs-per-dataset", type=int, default=100000)
    parser.add_argument("--negative-positive-ratio", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260702)
    args = parser.parse_args()

    all_rows: list[dict[str, object]] = []
    datasets: list[dict[str, object]] = []
    for offset, (label, path_text) in enumerate(args.dataset):
        rows, manifest = export_dataset_features(
            Path(path_text),
            label,
            args.max_block_size,
            args.max_pairs_per_dataset,
            args.negative_positive_ratio,
            args.seed + offset,
        )
        all_rows.extend(rows)
        datasets.append(manifest)

    write_jsonl(args.output, all_rows)
    summary = {
        "output": str(args.output),
        "output_sha256": sha256_file(args.output),
        "feature_schema": {
            "target": "same_author",
            "label_leakage_guard": "ORCID/cluster ids are not exported as features.",
            "format": "JSON Lines",
        },
        "seed": args.seed,
        "max_block_size": args.max_block_size,
        "max_pairs_per_dataset": args.max_pairs_per_dataset,
        "negative_positive_ratio": args.negative_positive_ratio,
        "datasets": datasets,
        "total_exported_pairs": len(all_rows),
        "total_positive_pairs": sum(1 for row in all_rows if row["same_author"]),
        "total_negative_pairs": sum(1 for row in all_rows if not row["same_author"]),
    }
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
