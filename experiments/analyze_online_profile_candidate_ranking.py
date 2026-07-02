#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose true mention-to-profile candidate ranking on online datasets.

This experiment uses the same history/test split and candidate generation as
the online ISTINA-proxy benchmark, but evaluates candidate-profile scores
directly.  It is intentionally not wired into production decisions.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.run_article2_final_validation import (  # noqa: E402
    DEFAULT_ADVISOR_DATASET,
    DEFAULT_CROSSREF_DATASET,
)
from src.author_disambiguation import (  # noqa: E402
    DisambiguationConfig,
    affiliation_tokens,
    build_affiliation_weights,
    decide_pair,
    load_labeled_mentions,
    sha256_file,
)
from src.istina_hypergraph_proxy import (  # noqa: E402
    AuthorProfile,
    OnlineBenchmarkConfig,
    build_profiles,
    coauthor_support,
    get_candidates,
)


DEFAULT_MIN_PRECISION = 0.995
DEFAULT_MAX_NEW_AUTHOR_FALSE_LINK = 0.01
DEFAULT_MIN_LOW_UNKNOWN_RECALL = 0.90
DEFAULT_MAX_LOW_UNKNOWN_RATE = 0.10
DEFAULT_MAX_PROFILE_MENTIONS = 30


@dataclass(frozen=True)
class DatasetSpec:
    label: str
    path: Path
    cutoff_year: int
    framework_profile: str


DEFAULT_DATASETS = [
    DatasetSpec("Crossref ORCID", DEFAULT_CROSSREF_DATASET, 2021, "balanced"),
    DatasetSpec("Advisor DOI ORCID", DEFAULT_ADVISOR_DATASET, 2021, "balanced"),
    DatasetSpec("DBLP public", Path("runs/public_dblp_20260701/dblp_public_mentions.json"), 2021, "balanced"),
    DatasetSpec("LAGOS-AND public", Path("runs/public_lagos_and_20260701/lagos_public_mentions.json"), 2018, "strict"),
    DatasetSpec("S2AND public", Path("runs/public_s2and_20260701/s2and_public_mentions.json"), 2000, "strict"),
]


SCORERS = (
    "framework_profile_score",
    "framework_balanced_score",
    "framework_strict_score",
    "graph_support",
    "combined_profile_graph_score",
)


def profile_score(
    position: int,
    author_id: str,
    context: dict[str, Any],
    framework_profile: str,
) -> float:
    mentions = context["mentions"]
    profiles: dict[str, AuthorProfile] = context["profiles"]
    history_coauthor_names: dict[int, set[str]] = context["history_coauthor_names"]
    affiliations_by_position: dict[int, frozenset[str]] = context["affiliations_by_position"]
    affiliation_weights: dict[str, float] = context["affiliation_weights"]
    family_frequencies: Counter[str] = context["family_frequencies"]
    test_coauthor_names: set[str] = context["test_coauthor_names"][position]
    config = DisambiguationConfig(algorithm="framework_v1", profile=framework_profile)
    mention = mentions[position]

    best_score = 0.0
    profile_positions = sorted(
        profiles[author_id].mention_positions,
        key=lambda history_position: mentions[history_position].year or 0,
        reverse=True,
    )[: context["max_profile_mentions"]]
    for history_position in profile_positions:
        history_mention = mentions[history_position]
        decision = decide_pair(
            mention,
            history_mention,
            affiliation_tokens(mention.affiliation),
            affiliations_by_position[history_position],
            test_coauthor_names,
            history_coauthor_names.get(history_position, set()),
            affiliation_weights,
            config,
            family_frequencies[history_mention.family_key],
        )
        if decision.same_author:
            best_score = max(best_score, decision.score)
    return best_score


def candidate_graph_support(
    position: int,
    author_id: str,
    candidate_sets: dict[int, list[str]],
    profiles: dict[str, AuthorProfile],
) -> float:
    support = 0.0
    for other_position, other_candidates in candidate_sets.items():
        if other_position == position:
            continue
        support += max(
            (coauthor_support(author_id, other_author_id, profiles) for other_author_id in other_candidates),
            default=0.0,
        )
    return support


def candidate_scores(
    position: int,
    author_id: str,
    candidate_sets: dict[int, list[str]],
    context: dict[str, Any],
    dataset_profile: str,
) -> dict[str, float]:
    profiles: dict[str, AuthorProfile] = context["profiles"]
    balanced = profile_score(position, author_id, context, "balanced")
    strict = profile_score(position, author_id, context, "strict")
    profile = strict if dataset_profile == "strict" else balanced
    graph = candidate_graph_support(position, author_id, candidate_sets, profiles)
    profile_mentions = len(profiles[author_id].mention_positions)
    candidate_count = len(candidate_sets[position])
    combined = (
        profile
        + 0.12 * graph
        + 0.02 * math.log1p(profile_mentions)
        - 0.03 * math.log1p(candidate_count)
    )
    return {
        "framework_profile_score": profile,
        "framework_balanced_score": balanced,
        "framework_strict_score": strict,
        "graph_support": graph,
        "combined_profile_graph_score": combined,
    }


def rank_scores(
    candidates: list[dict[str, Any]],
    scorer: str,
) -> dict[str, float | bool | str | None]:
    if not candidates:
        return {
            "has_candidate": False,
            "top_score": 0.0,
            "margin": 0.0,
            "top_is_truth": False,
            "top_author_id": None,
        }
    ordered = sorted(
        candidates,
        key=lambda item: (-float(item["scores"][scorer]), str(item["author_id"])),
    )
    top = ordered[0]
    top_score = float(top["scores"][scorer])
    second_score = float(ordered[1]["scores"][scorer]) if len(ordered) > 1 else 0.0
    return {
        "has_candidate": True,
        "top_score": top_score,
        "margin": top_score - second_score,
        "top_is_truth": bool(top["is_truth"]),
        "top_author_id": str(top["author_id"]),
    }


def build_dataset_examples(
    spec: DatasetSpec,
    max_profile_mentions: int,
) -> dict[str, Any]:
    mentions = load_labeled_mentions(spec.path)
    usable_positions = [
        position
        for position, mention in enumerate(mentions)
        if mention.year is not None and mention.paper_key
    ]
    history_positions = [
        position for position in usable_positions if mentions[position].year <= spec.cutoff_year
    ]
    test_positions = [
        position for position in usable_positions if mentions[position].year > spec.cutoff_year
    ]
    profiles, family_index, history_coauthor_names = build_profiles(mentions, history_positions)
    history_author_ids = set(profiles)
    affiliations_by_position = {
        position: affiliation_tokens(mention.affiliation)
        for position, mention in enumerate(mentions)
    }
    test_positions_by_paper: dict[str, list[int]] = defaultdict(list)
    for position in test_positions:
        test_positions_by_paper[mentions[position].paper_key].append(position)

    context = {
        "mentions": mentions,
        "profiles": profiles,
        "history_coauthor_names": history_coauthor_names,
        "affiliations_by_position": affiliations_by_position,
        "affiliation_weights": build_affiliation_weights(mentions),
        "family_frequencies": Counter(mentions[position].family_key for position in history_positions),
        "max_profile_mentions": max_profile_mentions,
        "test_coauthor_names": {},
    }

    examples: list[dict[str, Any]] = []
    candidate_size_histogram: Counter[int] = Counter()
    for paper_positions in test_positions_by_paper.values():
        candidate_sets = {
            position: get_candidates(mentions[position], profiles, family_index)
            for position in paper_positions
        }
        for position in paper_positions:
            context["test_coauthor_names"][position] = {
                mentions[other_position].entity_name_key
                for other_position in paper_positions
                if other_position != position
            }
        for position in paper_positions:
            mention = mentions[position]
            candidates = [
                {
                    "author_id": author_id,
                    "is_truth": author_id == mention.label_orcid,
                    "scores": candidate_scores(
                        position,
                        author_id,
                        candidate_sets,
                        context,
                        spec.framework_profile,
                    ),
                }
                for author_id in candidate_sets[position]
            ]
            candidate_size_histogram[len(candidates)] += 1
            ranked = {scorer: rank_scores(candidates, scorer) for scorer in SCORERS}
            truth_in_history = mention.label_orcid in history_author_ids
            examples.append(
                {
                    "dataset": spec.label,
                    "mention_id": mention.mention_id,
                    "truth_in_history": truth_in_history,
                    "truth_in_candidates": any(candidate["is_truth"] for candidate in candidates),
                    "candidate_count": len(candidates),
                    "ranked": ranked,
                }
            )

    return {
        "label": spec.label,
        "dataset": str(spec.path),
        "dataset_sha256": sha256_file(spec.path),
        "cutoff_year": spec.cutoff_year,
        "framework_profile": spec.framework_profile,
        "history_mentions": len(history_positions),
        "history_authors": len(history_author_ids),
        "test_mentions": len(test_positions),
        "truth_in_history_mentions": sum(1 for item in examples if item["truth_in_history"]),
        "truth_in_candidates": sum(1 for item in examples if item["truth_in_candidates"]),
        "candidate_size_histogram": dict(sorted(candidate_size_histogram.items())),
        "examples": examples,
    }


def evaluate_examples(
    examples: list[dict[str, Any]],
    scorer: str,
    threshold: float,
    margin: float,
) -> dict[str, float | int | bool]:
    linkable = [example for example in examples if example["truth_in_history"]]
    new_author = [example for example in examples if not example["truth_in_history"]]
    correct = wrong = unknown = 0
    for example in linkable:
        ranked = example["ranked"][scorer]
        if (
            not ranked["has_candidate"]
            or float(ranked["top_score"]) < threshold
            or float(ranked["margin"]) < margin
        ):
            unknown += 1
        elif ranked["top_is_truth"]:
            correct += 1
        else:
            wrong += 1

    false_links = 0
    for example in new_author:
        ranked = example["ranked"][scorer]
        if (
            ranked["has_candidate"]
            and float(ranked["top_score"]) >= threshold
            and float(ranked["margin"]) >= margin
        ):
            false_links += 1

    predicted = correct + wrong
    precision = correct / predicted if predicted else 0.0
    recall = correct / len(linkable) if linkable else 0.0
    unknown_rate = unknown / len(linkable) if linkable else 0.0
    false_link_rate = false_links / len(new_author) if new_author else 0.0
    return {
        "threshold": threshold,
        "margin": margin,
        "linkable_mentions": len(linkable),
        "new_author_mentions": len(new_author),
        "predicted": predicted,
        "correct": correct,
        "wrong": wrong,
        "unknown": unknown,
        "precision": precision,
        "recall": recall,
        "unknown_rate": unknown_rate,
        "new_author_false_links": false_links,
        "new_author_false_link_rate": false_link_rate,
        "low_unknown_ready": (
            precision >= DEFAULT_MIN_PRECISION
            and recall >= DEFAULT_MIN_LOW_UNKNOWN_RECALL
            and unknown_rate <= DEFAULT_MAX_LOW_UNKNOWN_RATE
            and false_link_rate <= DEFAULT_MAX_NEW_AUTHOR_FALSE_LINK
        ),
    }


def grid_values(examples: list[dict[str, Any]], scorer: str, field: str) -> list[float]:
    values = sorted(
        float(example["ranked"][scorer][field])
        for example in examples
        if example["ranked"][scorer]["has_candidate"]
    )
    if not values:
        return [0.0]
    fractions = [0.0, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 0.90, 0.95, 0.99, 1.0]
    sampled = {0.0}
    for fraction in fractions:
        index = min(len(values) - 1, int(fraction * (len(values) - 1)))
        sampled.add(round(values[index], 6))
    return sorted(sampled)


def select_setting(
    examples: list[dict[str, Any]],
    scorer: str,
) -> dict[str, float | int | bool]:
    rows = [
        evaluate_examples(examples, scorer, threshold, margin)
        for threshold in grid_values(examples, scorer, "top_score")
        for margin in grid_values(examples, scorer, "margin")
    ]
    safe = [
        row
        for row in rows
        if row["precision"] >= DEFAULT_MIN_PRECISION
        and row["new_author_false_link_rate"] <= DEFAULT_MAX_NEW_AUTHOR_FALSE_LINK
        and row["correct"] > 0
    ]
    if not safe:
        return max(
            rows,
            key=lambda row: (
                row["precision"],
                -row["new_author_false_link_rate"],
                row["recall"],
            ),
        )
    return max(
        safe,
        key=lambda row: (
            row["recall"],
            -row["unknown_rate"],
            row["precision"],
        ),
    )


def leave_one_dataset_out(dataset_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples_by_dataset = {
        str(result["label"]): list(result["examples"])
        for result in dataset_results
    }
    folds: list[dict[str, Any]] = []
    for scorer in SCORERS:
        for held_out, test_examples in examples_by_dataset.items():
            train_examples = [
                example
                for dataset, examples in examples_by_dataset.items()
                if dataset != held_out
                for example in examples
            ]
            selected = select_setting(train_examples, scorer)
            test = evaluate_examples(
                test_examples,
                scorer,
                float(selected["threshold"]),
                float(selected["margin"]),
            )
            folds.append(
                {
                    "scorer": scorer,
                    "held_out_dataset": held_out,
                    "selected_threshold": selected["threshold"],
                    "selected_margin": selected["margin"],
                    "train": selected,
                    "test": test,
                }
            )
    return folds


def parse_dataset_specs(values: list[list[str]] | None) -> list[DatasetSpec]:
    if not values:
        return DEFAULT_DATASETS
    specs: list[DatasetSpec] = []
    for label, path, cutoff_year, profile in values:
        specs.append(DatasetSpec(label, Path(path), int(cutoff_year), profile))
    return specs


def build_summary(specs: list[DatasetSpec], max_profile_mentions: int) -> dict[str, Any]:
    dataset_results = [
        build_dataset_examples(spec, max_profile_mentions)
        for spec in specs
    ]
    folds = leave_one_dataset_out(dataset_results)
    return {
        "datasets": [
            {
                key: value
                for key, value in result.items()
                if key != "examples"
            }
            for result in dataset_results
        ],
        "scorers": list(SCORERS),
        "folds": folds,
        "all_low_unknown_ready": all(fold["test"]["low_unknown_ready"] for fold in folds),
        "production_candidate": False,
        "scope": (
            "Diagnostic mention-to-profile candidate ranking; not connected to "
            "production LINK/NEW/UNKNOWN decisions."
        ),
        "limits": {
            "max_profile_mentions": max_profile_mentions,
            "min_precision": DEFAULT_MIN_PRECISION,
            "max_new_author_false_link": DEFAULT_MAX_NEW_AUTHOR_FALSE_LINK,
            "min_low_unknown_recall": DEFAULT_MIN_LOW_UNKNOWN_RECALL,
            "max_low_unknown_rate": DEFAULT_MAX_LOW_UNKNOWN_RATE,
        },
    }


def print_table(summary: dict[str, Any]) -> None:
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
    parser.add_argument(
        "--dataset",
        action="append",
        nargs=4,
        metavar=("LABEL", "PATH", "CUTOFF_YEAR", "PROFILE"),
        help="Dataset spec. If omitted, uses the Article 2 default online datasets.",
    )
    parser.add_argument("--max-profile-mentions", type=int, default=DEFAULT_MAX_PROFILE_MENTIONS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    summary = build_summary(parse_dataset_specs(args.dataset), args.max_profile_mentions)
    target = PROJECT_ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print_table(summary)


if __name__ == "__main__":
    main()
