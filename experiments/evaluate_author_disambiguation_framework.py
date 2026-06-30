#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evaluate author-disambiguation algorithms with ORCID labels.

ORCID is used only as ground truth for evaluation and is never passed into the
pairwise decision function.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.author_disambiguation import DisambiguationConfig, evaluate_file  # noqa: E402


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": result["dataset"],
        "algorithm": result["algorithm"],
        "profile": result["profile"],
        "labeled_mentions": result["labeled_mentions"],
        "unique_orcid": result["unique_orcid"],
        "evaluated_pairs": result["evaluated_pairs"],
        "skipped_large_blocks": result["skipped_large_blocks"],
        "large_block_exact_subblocks": result["large_block_exact_subblocks"],
        "large_block_exact_subblock_candidate_pairs": (
            result["large_block_exact_subblock_candidate_pairs"]
        ),
        "candidate_pairwise": result["candidate_pairwise"],
        "cluster_pairwise": result["cluster_pairwise"],
        "b_cubed": result["b_cubed"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--algorithm",
        choices=["baseline_exact_context", "framework_v1"],
        default="framework_v1",
    )
    parser.add_argument(
        "--profile",
        choices=["conservative", "balanced", "strict"],
        default="conservative",
    )
    parser.add_argument("--max-block-size", type=int, default=200)
    parser.add_argument("--example-limit", type=int, default=25)
    args = parser.parse_args()

    config = DisambiguationConfig(
        algorithm=args.algorithm,
        profile=args.profile,
        max_block_size=args.max_block_size,
        example_limit=args.example_limit,
    )
    result = evaluate_file(args.dataset, config)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(compact_result(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
