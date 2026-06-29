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
from heapq import nlargest
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
    is_chinese_like_name,
    is_initial_only_given,
    load_labeled_mentions,
    sha256_file,
)


METHOD_NAMES = (
    "name_most_frequent",
    "istina_hypergraph_proxy",
    "framework_v1_profile",
    "risk_controlled_hybrid",
)
HYPERGRAPH_ASSIGNMENT_BEAM_SIZE = 256


@dataclass(frozen=True)
class OnlineBenchmarkConfig:
    cutoff_year: int = 2021
    max_profile_mentions: int = 30
    hypergraph_support_threshold: float = 1.25


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


def score_istina_hypergraph_proxy(
    position: int,
    candidate_sets: dict[int, list[str]],
    profiles: dict[str, AuthorProfile],
) -> tuple[str | None, float]:
    candidates = candidate_sets[position]
    if not candidates:
        return None, 0.0

    best_author: str | None = None
    best_score = -1.0
    best_graph_support = 0.0
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
            best_graph_support = graph_support
    return best_author, best_graph_support


def coauthor_support(
    left_author_id: str,
    right_author_id: str,
    profiles: dict[str, AuthorProfile],
) -> float:
    if left_author_id == right_author_id:
        return 0.0
    count = max(
        profiles[left_author_id].coauthor_counts.get(right_author_id, 0),
        profiles[right_author_id].coauthor_counts.get(left_author_id, 0),
    )
    return math.log1p(count) if count else 0.0


def score_istina_hypergraph_proxy_paper(
    paper_positions: list[int],
    candidate_sets: dict[int, list[str]],
    profiles: dict[str, AuthorProfile],
    beam_size: int = HYPERGRAPH_ASSIGNMENT_BEAM_SIZE,
) -> dict[int, tuple[str | None, float]]:
    """Choose a paper-level candidate combination using coauthor support.

    The original ISTINA service optimizes the author combination for the whole
    paper.  The local proxy keeps that idea with a deterministic beam search:
    each signature receives at most one historical author and the same author is
    not assigned to two signatures in the same paper.
    """
    ordered_positions = sorted(
        paper_positions,
        key=lambda position: (
            len(candidate_sets[position]) if candidate_sets[position] else math.inf,
            position,
        ),
    )
    beams: list[tuple[float, dict[int, str], frozenset[str]]] = [(0.0, {}, frozenset())]

    for position in ordered_positions:
        candidates = candidate_sets[position]
        if not candidates:
            continue

        next_beams: list[tuple[float, dict[int, str], frozenset[str]]] = []
        for score, assignment, used_author_ids in beams:
            for author_id in candidates:
                if author_id in used_author_ids:
                    continue
                increment = 0.01 * math.log1p(len(profiles[author_id].mention_positions))
                for selected_author_id in assignment.values():
                    increment += coauthor_support(author_id, selected_author_id, profiles)
                next_assignment = dict(assignment)
                next_assignment[position] = author_id
                next_beams.append(
                    (
                        score + increment,
                        next_assignment,
                        used_author_ids | {author_id},
                    )
                )

        if next_beams:
            beams = nlargest(beam_size, next_beams, key=lambda item: item[0])

    best_assignment = max(beams, key=lambda item: item[0])[1] if beams else {}
    predictions: dict[int, tuple[str | None, float]] = {}
    for position, author_id in best_assignment.items():
        graph_support = sum(
            coauthor_support(author_id, selected_author_id, profiles)
            for other_position, selected_author_id in best_assignment.items()
            if other_position != position
        )
        predictions[position] = (author_id, graph_support)
    return predictions


def choose_istina_hypergraph_proxy(
    position: int,
    candidate_sets: dict[int, list[str]],
    profiles: dict[str, AuthorProfile],
) -> str | None:
    author_id, _ = score_istina_hypergraph_proxy(position, candidate_sets, profiles)
    return author_id


def choose_risk_controlled_hybrid(
    framework_prediction: str | None,
    hypergraph_prediction: str | None,
    hypergraph_support: float,
    support_threshold: float,
) -> str | None:
    if framework_prediction is not None:
        return framework_prediction
    if hypergraph_prediction is not None and hypergraph_support >= support_threshold:
        return hypergraph_prediction
    return None


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


def hard_case_labels(
    mention: AuthorMention,
    candidates: list[str],
    profiles: dict[str, AuthorProfile],
    truth_in_history: bool,
    framework_prediction: str | None,
    hypergraph_prediction: str | None,
    hypergraph_support: float,
    support_threshold: float,
) -> list[str]:
    labels: list[str] = []
    if len(candidates) >= 2:
        labels.append("ambiguous_candidates")
    exact_name_candidates = sum(
        1 for author_id in candidates if mention.given_tokens in profiles[author_id].given_variants
    )
    if exact_name_candidates >= 2:
        labels.append("exact_name_ambiguous")
    if is_initial_only_given(mention.given_tokens):
        labels.append("initial_only_signature")
    if is_chinese_like_name(mention):
        labels.append("chinese_like_signature")
    if not truth_in_history and candidates:
        labels.append("new_author_with_candidates")
    if hypergraph_prediction is not None and hypergraph_support >= support_threshold:
        labels.append("graph_supported_candidate")
    if (
        framework_prediction is None
        and hypergraph_prediction is not None
        and hypergraph_support >= support_threshold
    ):
        labels.append("framework_unknown_graph_supported")
    return labels


def empty_method_map() -> dict[str, Counter[str]]:
    return {method: empty_method_counts() for method in METHOD_NAMES}


def empty_new_author_method_map() -> dict[str, Counter[str]]:
    return {
        method: Counter(evaluated=0, predicted=0, correct=0, wrong=0, unknown=0)
        for method in METHOD_NAMES
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
    method_counts = empty_method_map()
    linkable_method_counts = empty_method_map()
    new_author_counts = empty_new_author_method_map()
    hard_linkable_counts: dict[str, dict[str, Counter[str]]] = defaultdict(empty_method_map)
    hard_new_author_counts: dict[str, dict[str, Counter[str]]] = defaultdict(
        empty_new_author_method_map
    )
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
        hypergraph_predictions = score_istina_hypergraph_proxy_paper(
            paper_positions,
            candidate_sets,
            profiles,
        )
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
            hypergraph_prediction, hypergraph_support = hypergraph_predictions.get(
                position,
                (None, 0.0),
            )
            framework_prediction = choose_framework_profile(
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
            )
            predictions = {
                "name_most_frequent": choose_name_most_frequent(candidate_sets[position], profiles),
                "istina_hypergraph_proxy": hypergraph_prediction,
                "framework_v1_profile": framework_prediction,
                "risk_controlled_hybrid": choose_risk_controlled_hybrid(
                    framework_prediction,
                    hypergraph_prediction,
                    hypergraph_support,
                    config.hypergraph_support_threshold,
                ),
            }
            truth_in_history = truth in history_author_ids
            labels = hard_case_labels(
                mentions[position],
                candidate_sets[position],
                profiles,
                truth_in_history,
                framework_prediction,
                hypergraph_prediction,
                hypergraph_support,
                config.hypergraph_support_threshold,
            )

            if truth_in_history:
                for method, prediction in predictions.items():
                    update_assignment_counts(linkable_method_counts[method], prediction, truth)
                for label in labels:
                    for method, prediction in predictions.items():
                        update_assignment_counts(
                            hard_linkable_counts[label][method],
                            prediction,
                            truth,
                        )
            else:
                for method, prediction in predictions.items():
                    update_new_author_counts(new_author_counts[method], prediction)
                for label in labels:
                    for method, prediction in predictions.items():
                        update_new_author_counts(
                            hard_new_author_counts[label][method],
                            prediction,
                        )

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
        "hypergraph_support_threshold": config.hypergraph_support_threshold,
        "hypergraph_assignment_beam_size": HYPERGRAPH_ASSIGNMENT_BEAM_SIZE,
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
        "hard_case_linkable_methods": {
            label: {
                method: summarize_method(counts, None)
                for method, counts in method_counts_by_name.items()
            }
            for label, method_counts_by_name in sorted(hard_linkable_counts.items())
        },
        "hard_case_new_author_methods": {
            label: {
                method: summarize_new_author(counts)
                for method, counts in method_counts_by_name.items()
            }
            for label, method_counts_by_name in sorted(hard_new_author_counts.items())
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
