#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Train a no-dependency supervised author-linker baseline on exported features."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


CATEGORICAL_FEATURES = [
    "given_relation",
    "baseline_rule",
    "framework_conservative_rule",
    "framework_balanced_rule",
    "framework_strict_rule",
]

NUMERIC_FEATURES = [
    "affiliation_jaccard",
    "affiliation_weighted_jaccard",
    "coauthor_jaccard",
    "baseline_score",
    "framework_conservative_score",
    "framework_balanced_score",
    "framework_strict_score",
]

BOOLEAN_FEATURES = [
    "same_family",
    "exact_canonical_name",
    "name_is_chinese_like",
    "either_initial_only",
    "left_has_affiliation",
    "right_has_affiliation",
    "baseline_same",
    "framework_conservative_same",
    "framework_balanced_same",
    "framework_strict_same",
]


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


def engineered_numeric(row: dict[str, object]) -> dict[str, float]:
    family_frequency = max(1.0, safe_float(row.get("family_frequency"), 1.0))
    left_coauthors = max(0.0, safe_float(row.get("left_coauthor_count"), 0.0))
    right_coauthors = max(0.0, safe_float(row.get("right_coauthor_count"), 0.0))
    year_gap = safe_float(row.get("year_gap"), -1.0)
    return {
        "log_family_frequency": math.log1p(family_frequency),
        "log_left_coauthor_count": math.log1p(left_coauthors),
        "log_right_coauthor_count": math.log1p(right_coauthors),
        "known_year_gap": 1.0 if year_gap >= 0 else 0.0,
        "clipped_year_gap": min(max(year_gap, 0.0), 50.0) / 50.0 if year_gap >= 0 else 0.0,
    }


def collect_categories(rows: Iterable[dict[str, object]]) -> dict[str, set[str]]:
    categories = {name: set() for name in CATEGORICAL_FEATURES}
    for row in rows:
        for name in CATEGORICAL_FEATURES:
            categories[name].add(str(row.get(name, "")))
    return categories


def feature_names(categories: dict[str, set[str]]) -> list[str]:
    names = ["bias"]
    names.extend(NUMERIC_FEATURES)
    names.extend(engineered_numeric({}).keys())
    names.extend(BOOLEAN_FEATURES)
    for name in CATEGORICAL_FEATURES:
        for value in sorted(categories[name]):
            names.append(f"{name}={value}")
    return names


def vectorize(
    row: dict[str, object],
    names: list[str],
    index: dict[str, int],
) -> list[tuple[int, float]]:
    values: list[tuple[int, float]] = [(index["bias"], 1.0)]
    for name in NUMERIC_FEATURES:
        values.append((index[name], safe_float(row.get(name), 0.0)))
    for name, value in engineered_numeric(row).items():
        values.append((index[name], value))
    for name in BOOLEAN_FEATURES:
        values.append((index[name], 1.0 if row.get(name) else 0.0))
    for name in CATEGORICAL_FEATURES:
        key = f"{name}={str(row.get(name, ''))}"
        if key in index:
            values.append((index[key], 1.0))
    return [(feature_index, value) for feature_index, value in values if value]


def sigmoid(value: float) -> float:
    if value >= 35:
        return 1.0
    if value <= -35:
        return 0.0
    return 1.0 / (1.0 + math.exp(-value))


def dot(weights: list[float], features: list[tuple[int, float]]) -> float:
    return sum(weights[index] * value for index, value in features)


def train_logistic(
    rows: list[dict[str, object]],
    names: list[str],
    epochs: int,
    learning_rate: float,
    l2: float,
    seed: int,
) -> list[float]:
    rng = random.Random(seed)
    index = {name: position for position, name in enumerate(names)}
    weights = [0.0 for _ in names]
    examples = [
        (vectorize(row, names, index), 1.0 if row["same_author"] else 0.0)
        for row in rows
    ]
    for epoch in range(epochs):
        rng.shuffle(examples)
        rate = learning_rate / math.sqrt(epoch + 1)
        for features, label in examples:
            prediction = sigmoid(dot(weights, features))
            error = prediction - label
            for feature_index, value in features:
                weights[feature_index] -= rate * (error * value + l2 * weights[feature_index])
    return weights


def score_rows(
    rows: list[dict[str, object]],
    names: list[str],
    weights: list[float],
) -> list[tuple[dict[str, object], float]]:
    index = {name: position for position, name in enumerate(names)}
    return [
        (row, sigmoid(dot(weights, vectorize(row, names, index))))
        for row in rows
    ]


def metrics_at_threshold(
    scored: list[tuple[dict[str, object], float]],
    threshold: float,
) -> dict[str, float | int]:
    tp = fp = fn = tn = 0
    for row, score in scored:
        predicted = score >= threshold
        truth = bool(row["same_author"])
        if predicted and truth:
            tp += 1
        elif predicted and not truth:
            fp += 1
        elif not predicted and truth:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "predicted_positive_rate": (tp + fp) / len(scored) if scored else 0.0,
    }


def select_threshold(
    scored: list[tuple[dict[str, object], float]],
    min_precision: float,
) -> dict[str, float | int]:
    thresholds = [index / 1000 for index in range(1, 1000)]
    candidates = [
        metrics_at_threshold(scored, threshold)
        for threshold in thresholds
    ]
    passing = [item for item in candidates if item["precision"] >= min_precision and item["tp"] > 0]
    if not passing:
        return max(candidates, key=lambda item: (item["precision"], item["recall"]))
    return max(passing, key=lambda item: (item["recall"], item["precision"]))


def baseline_metrics(rows: list[dict[str, object]], column: str) -> dict[str, float | int]:
    scored = [(row, 1.0 if row.get(column) else 0.0) for row in rows]
    return metrics_at_threshold(scored, 0.5)


def load_rows(path: Path, limit: int | None = None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
                if limit is not None and len(rows) >= limit:
                    break
    return rows


def evaluate_leave_one_dataset_out(
    rows: list[dict[str, object]],
    epochs: int,
    learning_rate: float,
    l2: float,
    min_precision: float,
    seed: int,
) -> dict[str, object]:
    by_dataset: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_dataset[str(row["dataset"])].append(row)

    fold_results: list[dict[str, object]] = []
    for fold_index, test_dataset in enumerate(sorted(by_dataset)):
        test_rows = by_dataset[test_dataset]
        train_rows = [
            row
            for dataset, dataset_rows in by_dataset.items()
            if dataset != test_dataset
            for row in dataset_rows
        ]
        categories = collect_categories(train_rows)
        names = feature_names(categories)
        weights = train_logistic(
            train_rows,
            names,
            epochs,
            learning_rate,
            l2,
            seed + fold_index,
        )
        train_scored = score_rows(train_rows, names, weights)
        test_scored = score_rows(test_rows, names, weights)
        selected = select_threshold(train_scored, min_precision)
        test_metrics = metrics_at_threshold(test_scored, float(selected["threshold"]))
        train_gate_passed = selected["precision"] >= min_precision
        test_gate_passed = test_metrics["precision"] >= min_precision
        fold_results.append(
            {
                "test_dataset": test_dataset,
                "train_rows": len(train_rows),
                "test_rows": len(test_rows),
                "feature_count": len(names),
                "selected_threshold": selected["threshold"],
                "train_precision_gate_passed": train_gate_passed,
                "test_precision_gate_passed": test_gate_passed,
                "train_selected_metrics": selected,
                "test_metrics": test_metrics,
                "framework_balanced_metrics": baseline_metrics(
                    test_rows,
                    "framework_balanced_same",
                ),
                "framework_strict_metrics": baseline_metrics(
                    test_rows,
                    "framework_strict_same",
                ),
            }
        )
    return {
        "folds": fold_results,
        "datasets": sorted(by_dataset),
        "rows": len(rows),
        "positive_rows": sum(1 for row in rows if row["same_author"]),
        "negative_rows": sum(1 for row in rows if not row["same_author"]),
        "all_test_precision_gates_passed": all(
            fold["test_precision_gate_passed"] for fold in fold_results
        ),
    }


def compact_summary(result: dict[str, object]) -> str:
    lines = [
        "| Test dataset | Model P/R/F1 | Threshold | Balanced P/R/F1 | Strict P/R/F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for fold in result["folds"]:
        model = fold["test_metrics"]
        balanced = fold["framework_balanced_metrics"]
        strict = fold["framework_strict_metrics"]
        lines.append(
            f"| {fold['test_dataset']} | "
            f"{model['precision']:.3f}/{model['recall']:.3f}/{model['f1']:.3f} | "
            f"{fold['selected_threshold']:.3f} | "
            f"{balanced['precision']:.3f}/{balanced['recall']:.3f}/{balanced['f1']:.3f} | "
            f"{strict['precision']:.3f}/{strict['recall']:.3f}/{strict['f1']:.3f} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--l2", type=float, default=0.0001)
    parser.add_argument("--min-precision", type=float, default=0.995)
    parser.add_argument("--seed", type=int, default=20260702)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    rows = load_rows(args.features, args.limit)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = evaluate_leave_one_dataset_out(
        rows,
        args.epochs,
        args.learning_rate,
        args.l2,
        args.min_precision,
        args.seed,
    )
    result.update(
        {
            "features": str(args.features),
            "features_sha256": sha256_file(args.features),
            "feature_manifest": str(args.manifest),
            "feature_manifest_sha256": sha256_file(args.manifest),
            "feature_manifest_output_sha256": manifest.get("output_sha256"),
            "manifest_hash_matches_features": (
                manifest.get("output_sha256") == sha256_file(args.features)
            ),
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "l2": args.l2,
            "min_precision": args.min_precision,
            "seed": args.seed,
            "production_candidate": False,
            "production_candidate_reason": (
                "Experimental pairwise baseline only; precision gates and "
                "end-to-end LINK/NEW/UNKNOWN behavior must be validated before use."
            ),
            "scope": (
                "No-dependency supervised pairwise baseline; not connected to "
                "production LINK/NEW/UNKNOWN path."
            ),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(compact_summary(result))


if __name__ == "__main__":
    main()
