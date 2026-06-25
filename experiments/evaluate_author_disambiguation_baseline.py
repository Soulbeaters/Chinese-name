#!/usr/bin/env python3
"""Conservative non-GNN author-disambiguation baseline with ORCID labels."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.evaluate_mentor_large_scale import normalized_tokens, sha256_file  # noqa: E402


STOPWORDS = {
    "and",
    "department",
    "faculty",
    "institute",
    "laboratory",
    "school",
    "the",
    "university",
}


def load_labeled_rows(path: Path) -> list[dict[str, Any]]:
    records = json.loads(path.read_text(encoding="utf-8"))
    return [
        row
        for row in records
        if str(row.get("orcid", "")).strip()
        and str(row.get("firstname", "")).strip()
        and str(row.get("lastname", "")).strip()
    ]


def name_tokens(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return normalized_tokens(str(row.get("firstname", ""))), normalized_tokens(str(row.get("lastname", "")))


def normalized_full_name(row: dict[str, Any]) -> str:
    first, last = name_tokens(row)
    return " ".join(first + last)


def block_key(row: dict[str, Any]) -> str | None:
    first, last = name_tokens(row)
    if not first or not last:
        return None
    return f"{' '.join(last)}|{first[0][:1]}"


def affiliation_tokens(value: Any) -> set[str]:
    text = " ".join(normalized_tokens(str(value or "")))
    return {
        token
        for token in re.findall(r"[a-z]{3,}", text)
        if token not in STOPWORDS
    }


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def safe_year(row: dict[str, Any]) -> int | None:
    try:
        return int(row.get("year"))
    except (TypeError, ValueError):
        return None


def build_coauthor_sets(rows: list[dict[str, Any]]) -> dict[int, set[str]]:
    names_by_doi: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        doi = str(row.get("doi") or row.get("article_id") or "").strip()
        if doi:
            names_by_doi[doi].add(normalized_full_name(row))

    coauthors: dict[int, set[str]] = {}
    for index, row in enumerate(rows):
        doi = str(row.get("doi") or row.get("article_id") or "").strip()
        names = set(names_by_doi.get(doi, set()))
        names.discard(normalized_full_name(row))
        coauthors[index] = names
    return coauthors


def same_author_rule(
    left: dict[str, Any],
    right: dict[str, Any],
    left_affiliation: set[str],
    right_affiliation: set[str],
    left_coauthors: set[str],
    right_coauthors: set[str],
) -> tuple[bool, str]:
    if normalized_full_name(left) != normalized_full_name(right):
        return False, "different_full_name"

    left_year = safe_year(left)
    right_year = safe_year(right)
    year_gap = abs(left_year - right_year) if left_year is not None and right_year is not None else None
    if year_gap is not None and year_gap > 15:
        return False, "year_gap_gt_15"

    affiliation_overlap = jaccard(left_affiliation, right_affiliation)
    coauthor_overlap = jaccard(left_coauthors, right_coauthors)
    if affiliation_overlap >= 0.35:
        return True, "exact_name_affiliation_jaccard_ge_0.35"
    if coauthor_overlap >= 0.15:
        return True, "exact_name_coauthor_jaccard_ge_0.15"
    if year_gap is not None and year_gap <= 2 and affiliation_overlap >= 0.20:
        return True, "exact_name_recent_affiliation_jaccard_ge_0.20"
    return False, "insufficient_context"


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def f1(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def b_cubed(rows: list[dict[str, Any]], uf: UnionFind) -> dict[str, float]:
    predicted: dict[int, set[int]] = defaultdict(set)
    truth: dict[str, set[int]] = defaultdict(set)
    for index, row in enumerate(rows):
        predicted[uf.find(index)].add(index)
        truth[str(row["orcid"])].add(index)

    precision_sum = 0.0
    recall_sum = 0.0
    for index, row in enumerate(rows):
        pred_cluster = predicted[uf.find(index)]
        true_cluster = truth[str(row["orcid"])]
        overlap = len(pred_cluster & true_cluster)
        precision_sum += overlap / len(pred_cluster)
        recall_sum += overlap / len(true_cluster)
    n = len(rows)
    precision = precision_sum / n if n else 0.0
    recall = recall_sum / n if n else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1(precision, recall),
    }


def evaluate(path: Path, max_block_size: int) -> dict[str, Any]:
    rows = load_labeled_rows(path)
    blocks: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        key = block_key(row)
        if key:
            blocks[key].append(index)

    coauthors = build_coauthor_sets(rows)
    affiliations = {index: affiliation_tokens(row.get("affiliation")) for index, row in enumerate(rows)}
    uf = UnionFind(len(rows))
    pair_counts = Counter()
    rule_counts = Counter()
    skipped_large_blocks = 0
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for key, indices in blocks.items():
        if len(indices) > max_block_size:
            skipped_large_blocks += 1
            continue
        for pos, left_index in enumerate(indices):
            left = rows[left_index]
            left_doi = str(left.get("doi") or left.get("article_id") or "").strip()
            for right_index in indices[pos + 1:]:
                right = rows[right_index]
                right_doi = str(right.get("doi") or right.get("article_id") or "").strip()
                if left_doi and left_doi == right_doi:
                    pair_counts["same_doi_skipped"] += 1
                    continue
                same_truth = str(left["orcid"]) == str(right["orcid"])
                predicted_same, rule = same_author_rule(
                    left,
                    right,
                    affiliations[left_index],
                    affiliations[right_index],
                    coauthors[left_index],
                    coauthors[right_index],
                )
                rule_counts[rule] += 1
                if predicted_same:
                    uf.union(left_index, right_index)

                if predicted_same and same_truth:
                    pair_counts["tp"] += 1
                elif predicted_same and not same_truth:
                    pair_counts["fp"] += 1
                    bucket = "false_positive"
                elif not predicted_same and same_truth:
                    pair_counts["fn"] += 1
                    bucket = "false_negative"
                else:
                    pair_counts["tn"] += 1
                    bucket = ""

                if bucket and len(examples[bucket]) < 25:
                    examples[bucket].append({
                        "block": key,
                        "left_name": normalized_full_name(left),
                        "right_name": normalized_full_name(right),
                        "left_orcid": left.get("orcid"),
                        "right_orcid": right.get("orcid"),
                        "left_doi": left_doi,
                        "right_doi": right_doi,
                        "left_year": left.get("year"),
                        "right_year": right.get("year"),
                        "affiliation_jaccard": jaccard(affiliations[left_index], affiliations[right_index]),
                        "coauthor_jaccard": jaccard(coauthors[left_index], coauthors[right_index]),
                        "rule": rule,
                    })

    tp = pair_counts["tp"]
    fp = pair_counts["fp"]
    fn = pair_counts["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "dataset": str(path),
        "dataset_sha256": sha256_file(path),
        "labeled_mentions": len(rows),
        "unique_orcid": len({str(row["orcid"]) for row in rows}),
        "blocks": len(blocks),
        "max_block_size": max_block_size,
        "skipped_large_blocks": skipped_large_blocks,
        "evaluated_pairs": tp + fp + fn + pair_counts["tn"],
        "same_doi_skipped_pairs": pair_counts["same_doi_skipped"],
        "pairwise": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": pair_counts["tn"],
            "precision": precision,
            "recall": recall,
            "f1": f1(precision, recall),
        },
        "b_cubed": b_cubed(rows, uf),
        "rule_counts": dict(rule_counts.most_common()),
        "examples": examples,
        "production_targets": {
            "pairwise_precision": 0.99,
            "pairwise_recall": 0.95,
            "b_cubed_f1": 0.95,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-block-size", type=int, default=200)
    args = parser.parse_args()

    result = evaluate(args.dataset, args.max_block_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    compact = {
        "labeled_mentions": result["labeled_mentions"],
        "unique_orcid": result["unique_orcid"],
        "evaluated_pairs": result["evaluated_pairs"],
        "skipped_large_blocks": result["skipped_large_blocks"],
        "pairwise": result["pairwise"],
        "b_cubed": result["b_cubed"],
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
