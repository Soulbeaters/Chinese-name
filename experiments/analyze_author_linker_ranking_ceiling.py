#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze mention-level candidate ranking from exported pairwise features.

This is an experiment-only diagnostic.  It does not change the production
author-disambiguation path.  The goal is to test whether the already exported
pairwise feature table contains enough signal for a low-UNKNOWN candidate
ranker before adding heavier supervised dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Callable


DEFAULT_MIN_PRECISION = 0.995
DEFAULT_MAX_FALSE_LINK = 0.01
DEFAULT_MIN_LOW_UNKNOWN_RECALL = 0.90
DEFAULT_MAX_LOW_UNKNOWN_RATE = 0.10
DEFAULT_THRESHOLDS = [index / 20 for index in range(0, 61)]
DEFAULT_MARGINS = [0.0, 0.01, 0.025, 0.05, 0.10, 0.20, 0.40]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def relation_weight(row: dict[str, object]) -> float:
    relation = row.get("given_relation")
    if relation == "exact":
        return 0.45
    if relation == "prefix":
        return 0.25
    if relation == "initial_compatible":
        return 0.12
    return 0.0


def context_score(row: dict[str, object]) -> float:
    family_frequency = max(1.0, safe_float(row.get("family_frequency"), 1.0))
    score = relation_weight(row)
    score += safe_float(row.get("framework_balanced_score")) * 0.85
    score += safe_float(row.get("framework_strict_score")) * 0.35
    score += safe_float(row.get("coauthor_jaccard")) * 1.20
    score += safe_float(row.get("affiliation_weighted_jaccard")) * 0.80
    score += safe_float(row.get("affiliation_jaccard")) * 0.30
    if row.get("left_has_affiliation") and row.get("right_has_affiliation"):
        score += 0.05
    if row.get("name_is_chinese_like"):
        score -= 0.10
    if row.get("either_initial_only"):
        score -= 0.08
    score -= min(math.log1p(family_frequency) / 20.0, 0.20)
    return score


SCORERS: dict[str, Callable[[dict[str, object]], float]] = {
    "framework_balanced_score": lambda row: safe_float(row.get("framework_balanced_score")),
    "framework_strict_score": lambda row: safe_float(row.get("framework_strict_score")),
    "context_score": context_score,
}


def load_rows(path: Path, limit: int | None = None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def directed_candidates(
    rows: list[dict[str, object]],
    scorer: Callable[[dict[str, object]], float],
) -> dict[tuple[str, str], list[tuple[float, str, bool]]]:
    groups: dict[tuple[str, str], list[tuple[float, str, bool]]] = defaultdict(list)
    for row in rows:
        dataset = str(row["dataset"])
        left_id = str(row["left_mention_id"])
        right_id = str(row["right_mention_id"])
        same_author = bool(row["same_author"])
        score = scorer(row)
        groups[(dataset, left_id)].append((score, right_id, same_author))
        groups[(dataset, right_id)].append((score, left_id, same_author))
    return groups


def best_candidate(candidates: list[tuple[float, str, bool]]) -> tuple[float, float, bool]:
    ordered = sorted(candidates, key=lambda item: (-item[0], item[1]))
    top_score, _, top_truth = ordered[0]
    second_score = ordered[1][0] if len(ordered) > 1 else 0.0
    return top_score, top_score - second_score, top_truth


def anchor_examples(
    rows: list[dict[str, object]],
    scorer: Callable[[dict[str, object]], float],
) -> list[dict[str, object]]:
    examples: list[dict[str, object]] = []
    for (dataset, anchor_id), candidates in directed_candidates(rows, scorer).items():
        has_positive = any(candidate[2] for candidate in candidates)
        top_score, margin, top_truth = best_candidate(candidates)
        examples.append(
            {
                "dataset": dataset,
                "anchor_id": anchor_id,
                "candidate_count": len(candidates),
                "has_positive": has_positive,
                "top_score": top_score,
                "margin": margin,
                "top_is_positive": top_truth,
            }
        )
    return examples


def evaluate_examples(
    examples: list[dict[str, object]],
    threshold: float,
    margin: float,
) -> dict[str, float | int]:
    linkable = [example for example in examples if example["has_positive"]]
    new_author = [example for example in examples if not example["has_positive"]]
    linked = [
        example
        for example in linkable
        if example["top_score"] >= threshold and example["margin"] >= margin
    ]
    correct = sum(1 for example in linked if example["top_is_positive"])
    wrong = len(linked) - correct
    false_links = sum(
        1
        for example in new_author
        if example["top_score"] >= threshold and example["margin"] >= margin
    )
    precision = correct / len(linked) if linked else 0.0
    recall = correct / len(linkable) if linkable else 0.0
    unknown_rate = 1.0 - (len(linked) / len(linkable)) if linkable else 0.0
    false_link_rate = false_links / len(new_author) if new_author else 0.0
    return {
        "threshold": threshold,
        "margin": margin,
        "linkable_anchors": len(linkable),
        "new_author_like_anchors": len(new_author),
        "predicted_linkable": len(linked),
        "correct": correct,
        "wrong": wrong,
        "precision": precision,
        "recall": recall,
        "unknown_rate": unknown_rate,
        "new_author_false_links": false_links,
        "new_author_false_link_rate": false_link_rate,
        "low_unknown_ready": (
            precision >= DEFAULT_MIN_PRECISION
            and recall >= DEFAULT_MIN_LOW_UNKNOWN_RECALL
            and unknown_rate <= DEFAULT_MAX_LOW_UNKNOWN_RATE
            and false_link_rate <= DEFAULT_MAX_FALSE_LINK
        ),
    }


def select_setting(examples: list[dict[str, object]]) -> dict[str, float | int]:
    evaluated = [
        evaluate_examples(examples, threshold, margin)
        for threshold in DEFAULT_THRESHOLDS
        for margin in DEFAULT_MARGINS
    ]
    safe = [
        item
        for item in evaluated
        if item["precision"] >= DEFAULT_MIN_PRECISION
        and item["new_author_false_link_rate"] <= DEFAULT_MAX_FALSE_LINK
        and item["correct"] > 0
    ]
    if not safe:
        return max(
            evaluated,
            key=lambda item: (
                item["precision"],
                -item["new_author_false_link_rate"],
                item["recall"],
            ),
        )
    return max(
        safe,
        key=lambda item: (
            item["recall"],
            -item["unknown_rate"],
            item["precision"],
            -item["threshold"],
            -item["margin"],
        ),
    )


def leave_one_dataset_out(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    datasets = sorted({str(row["dataset"]) for row in rows})
    results: list[dict[str, object]] = []
    for scorer_name, scorer in SCORERS.items():
        examples = anchor_examples(rows, scorer)
        by_dataset: dict[str, list[dict[str, object]]] = defaultdict(list)
        for example in examples:
            by_dataset[str(example["dataset"])].append(example)
        for held_out in datasets:
            train_examples = [
                example
                for dataset, dataset_examples in by_dataset.items()
                if dataset != held_out
                for example in dataset_examples
            ]
            selected = select_setting(train_examples)
            test_metrics = evaluate_examples(
                by_dataset[held_out],
                float(selected["threshold"]),
                float(selected["margin"]),
            )
            results.append(
                {
                    "scorer": scorer_name,
                    "held_out_dataset": held_out,
                    "selected_threshold": selected["threshold"],
                    "selected_margin": selected["margin"],
                    "train_precision": selected["precision"],
                    "train_recall": selected["recall"],
                    "train_unknown_rate": selected["unknown_rate"],
                    "train_new_author_false_link_rate": (
                        selected["new_author_false_link_rate"]
                    ),
                    "test": test_metrics,
                }
            )
    return results


def build_summary(
    features: Path,
    manifest: Path | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    rows = load_rows(features, limit)
    folds = leave_one_dataset_out(rows)
    datasets = sorted({str(row["dataset"]) for row in rows})
    return {
        "features": str(features),
        "features_sha256": sha256_file(features),
        "feature_manifest": str(manifest) if manifest else None,
        "feature_manifest_sha256": sha256_file(manifest) if manifest else None,
        "rows": len(rows),
        "datasets": datasets,
        "scorers": sorted(SCORERS),
        "threshold_grid": DEFAULT_THRESHOLDS,
        "margin_grid": DEFAULT_MARGINS,
        "folds": folds,
        "all_low_unknown_ready": all(item["test"]["low_unknown_ready"] for item in folds),
        "production_candidate": False,
        "scope": (
            "Diagnostic mention-level ranking over sampled pairwise features; "
            "not an end-to-end production author-profile ranker."
        ),
    }


def print_table(summary: dict[str, object]) -> None:
    print("| Scorer | Held-out | Test P/R/UNKNOWN | New false-link | Low-UNKNOWN |")
    print("|---|---|---:|---:|---|")
    for fold in summary["folds"]:
        test = fold["test"]
        print(
            "| {scorer} | {dataset} | {p:.3f}/{r:.3f}/{u:.3f} | {fl:.3f} | {gate} |".format(
                scorer=fold["scorer"],
                dataset=fold["held_out_dataset"],
                p=100 * float(test["precision"]),
                r=100 * float(test["recall"]),
                u=100 * float(test["unknown_rate"]),
                fl=100 * float(test["new_author_false_link_rate"]),
                gate="PASS" if test["low_unknown_ready"] else "FAIL",
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    summary = build_summary(args.features, args.manifest, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print_table(summary)


if __name__ == "__main__":
    main()
