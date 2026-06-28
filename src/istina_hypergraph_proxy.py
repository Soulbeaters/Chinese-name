# -*- coding: utf-8 -*-
"""Online assignment benchmark for the ISTINA hypergraph disambiguation idea.

The original C++ service in ``disambiguation-authors`` is not directly runnable
on the local JSON datasets: its test harness depends on ISTINA database tables
and Oracle client libraries, and the archived service entry point is incomplete.

This module therefore implements a source-faithful proxy for comparison:

* candidate generation follows the old same-family / compatible-given-name idea;
* ORCID is used only as a surrogate historical author id for evaluation;
* the ISTINA proxy scores candidates by historical coauthor support from the
  current paper's other candidate sets;
* the framework method uses the current ``framework_v1`` pairwise rules as a
  risk-controlled profile linker on the same candidate sets.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.author_disambiguation import (
    AuthorMention,
    DisambiguationConfig,
    affiliation_tokens,
    build_affiliation_weights,
    decide_pair,
    f1,
    given_relation,
    load_labeled_mentions,
    sha256_file,
)


@dataclass(frozen=True)
class OnlineBenchmarkConfig:
    cutoff_year: int = 2021
    max_profile_mentions: int = 30


@dataclass
class AuthorProfile:
    author_id: str
    mention_positions: list[int]
    family_keys: set[str]
    given_variants: set[tuple[str, ...]]
    coauthor_counts: Counter[str]


def relation_score(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    relation = given_relation(left, right)
    if relation == "exact":
        return 1.0
    if relation == "prefix":
        return 0.82
    if relation == "initial_compatible":
        return 0.66
    return 0.0


def build_profiles(
    mentions: list[AuthorMention],
    history_positions: list[int],
) -> tuple[dict[str, AuthorProfile], dict[str, set[str]], dict[int, set[str]]]:
    profiles: dict[str, AuthorProfile] = {}
    family_index: dict[str, set[str]] = defaultdict(set)
    positions_by_paper: dict[str, list[int]] = defaultdict(list)
    coauthor_names_by_position: dict[int, set[str]] = {}

    for position in history_positions:
        mention = mentions[position]
        profile = profiles.setdefault(
            mention.label_orcid,
            AuthorProfile(
                author_id=mention.label_orcid,
                mention_positions=[],
                family_keys=set(),
                given_variants=set(),
                coauthor_counts=Counter(),
            ),
        )
        profile.mention_positions.append(position)
        profile.family_keys.add(mention.family_key)
        profile.given_variants.add(mention.given_tokens)
        family_index[mention.family_key].add(mention.label_orcid)
        if mention.paper_key:
            positions_by_paper[mention.paper_key].append(position)

    for positions in positions_by_paper.values():
        author_ids = {mentions[position].label_orcid for position in positions}
        names = {mentions[position].entity_name_key for position in positions}
        for position in positions:
            author_id = mentions[position].label_orcid
            profiles[author_id].coauthor_counts.update(author_ids - {author_id})
            coauthor_names_by_position[position] = names - {mentions[position].entity_name_key}

    return profiles, family_index, coauthor_names_by_position


def get_candidates(
    mention: AuthorMention,
    profiles: dict[str, AuthorProfile],
    family_index: dict[str, set[str]],
) -> list[str]:
    candidates: list[tuple[float, int, str]] = []
    for author_id in family_index.get(mention.family_key, set()):
        profile = profiles[author_id]
        score = max(
            relation_score(mention.given_tokens, variant)
            for variant in profile.given_variants
        )
        if score > 0:
            candidates.append((score, len(profile.mention_positions), author_id))
    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [author_id for _, _, author_id in candidates]


def choose_name_most_frequent(
    candidates: list[str],
    profiles: dict[str, AuthorProfile],
) -> str | None:
    if not candidates:
        return None
    return max(candidates, key=lambda author_id: (len(profiles[author_id].mention_positions), author_id))


def choose_istina_hypergraph_proxy(
    position: int,
    candidate_sets: dict[int, list[str]],
    profiles: dict[str, AuthorProfile],
) -> str | None:
    candidates = candidate_sets[position]
    if not candidates:
        return None

    best_author: str | None = None
    best_score = -1.0
    for author_id in candidates:
        profile = profiles[author_id]
        graph_support = 0.0
        for other_position, other_candidates in candidate_sets.items():
            if other_position == position:
                continue
            best_edge = 0.0
            for other_author_id in other_candidates:
                if other_author_id == author_id:
                    continue
                count = profile.coauthor_counts.get(other_author_id, 0)
                if count:
                    best_edge = max(best_edge, math.log1p(count))
            graph_support += best_edge

        score = graph_support + 0.01 * math.log1p(len(profile.mention_positions))
        if score > best_score or (score == best_score and (best_author is None or author_id < best_author)):
            best_score = score
            best_author = author_id
    return best_author


def choose_framework_profile(
    mention: AuthorMention,
    test_coauthor_names: set[str],
    candidates: list[str],
    profiles: dict[str, AuthorProfile],
    mentions: list[AuthorMention],
    coauthor_names_by_position: dict[int, set[str]],
    affiliations_by_position: dict[int, frozenset[str]],
    affiliation_weights: dict[str, float],
    family_frequencies: Counter[str],
    max_profile_mentions: int,
) -> str | None:
    best_author: str | None = None
    best_score = 0.0
    config = DisambiguationConfig(algorithm="framework_v1", profile="balanced")

    for author_id in candidates:
        profile_positions = sorted(
            profiles[author_id].mention_positions,
            key=lambda position: mentions[position].year or 0,
            reverse=True,
        )[:max_profile_mentions]
        candidate_score = 0.0
        for history_position in profile_positions:
            history_mention = mentions[history_position]
            decision = decide_pair(
                mention,
                history_mention,
                affiliation_tokens(mention.affiliation),
                affiliations_by_position[history_position],
                test_coauthor_names,
                coauthor_names_by_position.get(history_position, set()),
                affiliation_weights,
                config,
                family_frequencies[history_mention.family_key],
            )
            if decision.same_author:
                candidate_score = max(candidate_score, decision.score)
        if candidate_score > best_score or (
            candidate_score == best_score
            and candidate_score > 0
            and (best_author is None or author_id < best_author)
        ):
            best_score = candidate_score
            best_author = author_id

    return best_author


def empty_method_counts() -> Counter[str]:
    return Counter(
        evaluated=0,
        predicted=0,
        correct=0,
        wrong=0,
        unknown=0,
        paper_exact=0,
    )


def summarize_method(
    counts: Counter[str],
    evaluated_papers: int | None,
) -> dict[str, float | int]:
    evaluated = counts["evaluated"]
    predicted = counts["predicted"]
    correct = counts["correct"]
    wrong = counts["wrong"]
    unknown = counts["unknown"]
    precision = correct / predicted if predicted else 0.0
    recall = correct / evaluated if evaluated else 0.0
    summary: dict[str, float | int] = {
        "evaluated_mentions": evaluated,
        "predicted_mentions": predicted,
        "correct": correct,
        "wrong": wrong,
        "unknown": unknown,
        "precision": precision,
        "recall": recall,
        "f1": f1(precision, recall),
        "accuracy_counting_unknown_as_wrong": correct / evaluated if evaluated else 0.0,
        "unknown_rate": unknown / evaluated if evaluated else 0.0,
    }
    if evaluated_papers is not None:
        summary["paper_exact"] = counts["paper_exact"]
        summary["paper_exact_rate"] = (
            counts["paper_exact"] / evaluated_papers if evaluated_papers else 0.0
        )
    return summary


def update_assignment_counts(
    counts: Counter[str],
    prediction: str | None,
    truth: str,
) -> None:
    counts["evaluated"] += 1
    if prediction is None:
        counts["unknown"] += 1
    elif prediction == truth:
        counts["predicted"] += 1
        counts["correct"] += 1
    else:
        counts["predicted"] += 1
        counts["wrong"] += 1


def update_new_author_counts(counts: Counter[str], prediction: str | None) -> None:
    counts["evaluated"] += 1
    if prediction is None:
        counts["unknown"] += 1
        counts["correct"] += 1
    else:
        counts["predicted"] += 1
        counts["wrong"] += 1


def summarize_new_author(counts: Counter[str]) -> dict[str, float | int]:
    evaluated = counts["evaluated"]
    false_links = counts["wrong"]
    no_prediction = counts["unknown"]
    return {
        "evaluated_mentions": evaluated,
        "false_links": false_links,
        "no_prediction": no_prediction,
        "false_link_rate": false_links / evaluated if evaluated else 0.0,
        "no_prediction_rate": no_prediction / evaluated if evaluated else 0.0,
    }


def evaluate_online_assignment(
    mentions: list[AuthorMention],
    config: OnlineBenchmarkConfig,
) -> dict[str, Any]:
    usable_positions = [
        position
        for position, mention in enumerate(mentions)
        if mention.year is not None and mention.paper_key
    ]
    history_positions = [
        position for position in usable_positions if mentions[position].year <= config.cutoff_year
    ]
    test_positions = [
        position for position in usable_positions if mentions[position].year > config.cutoff_year
    ]
    profiles, family_index, history_coauthor_names = build_profiles(mentions, history_positions)
    history_author_ids = set(profiles)
    affiliation_weights = build_affiliation_weights(mentions)
    affiliations_by_position = {
        position: affiliation_tokens(mention.affiliation)
        for position, mention in enumerate(mentions)
    }
    family_frequencies: Counter[str] = Counter(mentions[position].family_key for position in history_positions)

    test_positions_by_paper: dict[str, list[int]] = defaultdict(list)
    for position in test_positions:
        test_positions_by_paper[mentions[position].paper_key].append(position)

    totals = Counter()
    candidate_sizes: Counter[int] = Counter()
    method_counts = {
        "name_most_frequent": empty_method_counts(),
        "istina_hypergraph_proxy": empty_method_counts(),
        "framework_v1_profile": empty_method_counts(),
    }
    linkable_method_counts = {
        "name_most_frequent": empty_method_counts(),
        "istina_hypergraph_proxy": empty_method_counts(),
        "framework_v1_profile": empty_method_counts(),
    }
    new_author_counts = {
        "name_most_frequent": Counter(evaluated=0, predicted=0, correct=0, wrong=0, unknown=0),
        "istina_hypergraph_proxy": Counter(evaluated=0, predicted=0, correct=0, wrong=0, unknown=0),
        "framework_v1_profile": Counter(evaluated=0, predicted=0, correct=0, wrong=0, unknown=0),
    }
    evaluated_papers = 0

    for paper_positions in test_positions_by_paper.values():
        candidate_sets = {
            position: get_candidates(mentions[position], profiles, family_index)
            for position in paper_positions
        }
        coauthor_names = {
            position: {
                mentions[other_position].entity_name_key
                for other_position in paper_positions
                if other_position != position
            }
            for position in paper_positions
        }
        covered_positions = [
            position
            for position in paper_positions
            if mentions[position].label_orcid in candidate_sets[position]
        ]

        totals["test_mentions"] += len(paper_positions)
        totals["truth_in_history"] += sum(
            1 for position in paper_positions if mentions[position].label_orcid in history_author_ids
        )
        totals["candidate_covered_mentions"] += len(covered_positions)
        for position in paper_positions:
            candidate_sizes[len(candidate_sets[position])] += 1

        if not covered_positions:
            paper_correct = {}
        else:
            evaluated_papers += 1
            paper_correct = {method: True for method in method_counts}

        for position in paper_positions:
            truth = mentions[position].label_orcid
            predictions = {
                "name_most_frequent": choose_name_most_frequent(candidate_sets[position], profiles),
                "istina_hypergraph_proxy": choose_istina_hypergraph_proxy(
                    position,
                    candidate_sets,
                    profiles,
                ),
                "framework_v1_profile": choose_framework_profile(
                    mentions[position],
                    coauthor_names[position],
                    candidate_sets[position],
                    profiles,
                    mentions,
                    history_coauthor_names,
                    affiliations_by_position,
                    affiliation_weights,
                    family_frequencies,
                    config.max_profile_mentions,
                ),
            }

            if truth in history_author_ids:
                for method, prediction in predictions.items():
                    update_assignment_counts(linkable_method_counts[method], prediction, truth)
            else:
                for method, prediction in predictions.items():
                    update_new_author_counts(new_author_counts[method], prediction)

            if position not in covered_positions:
                continue

            for method, prediction in predictions.items():
                update_assignment_counts(method_counts[method], prediction, truth)
                if prediction is None:
                    paper_correct[method] = False
                elif prediction != truth:
                    paper_correct[method] = False

        for method, is_correct in paper_correct.items():
            if is_correct:
                method_counts[method]["paper_exact"] += 1

    return {
        "cutoff_year": config.cutoff_year,
        "max_profile_mentions": config.max_profile_mentions,
        "history_mentions": len(history_positions),
        "history_authors": len(history_author_ids),
        "test_mentions": totals["test_mentions"],
        "truth_in_history_mentions": totals["truth_in_history"],
        "candidate_covered_mentions": totals["candidate_covered_mentions"],
        "candidate_coverage_vs_truth_in_history": (
            totals["candidate_covered_mentions"] / totals["truth_in_history"]
            if totals["truth_in_history"]
            else 0.0
        ),
        "evaluated_papers": evaluated_papers,
        "candidate_size_histogram": dict(sorted(candidate_sizes.items())),
        "methods": {
            method: summarize_method(counts, evaluated_papers)
            for method, counts in method_counts.items()
        },
        "linkable_end_to_end_methods": {
            method: summarize_method(counts, None)
            for method, counts in linkable_method_counts.items()
        },
        "new_author_methods": {
            method: summarize_new_author(counts)
            for method, counts in new_author_counts.items()
        },
        "limitations": [
            "This is a source-faithful Python proxy, not the compiled ISTINA C++ service.",
            "ORCID labels are used as surrogate historical author ids for evaluation.",
            "Only ORCID-labeled mentions are used, matching the available gold labels.",
        ],
    }


def evaluate_file(path: Path, config: OnlineBenchmarkConfig) -> dict[str, Any]:
    mentions = load_labeled_mentions(path)
    result = evaluate_online_assignment(mentions, config)
    result["dataset"] = str(path)
    result["dataset_sha256"] = sha256_file(path)
    result["labeled_mentions"] = len(mentions)
    result["unique_orcid"] = len({mention.label_orcid for mention in mentions})
    return result
