# -*- coding: utf-8 -*-
"""Multilingual author-name normalization and conservative author disambiguation.

The module intentionally does not use ORCID, email, or any external person ID as
features.  Those identifiers are accepted only by the evaluation layer as labels.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping

from data.surname_pinyin_db import is_surname_pinyin
from src.pinyin_validator import is_valid_pinyin_name
from src.surname_identifier_v8 import preprocess_name


AFFILIATION_STOPWORDS = {
    "academy",
    "and",
    "center",
    "centre",
    "clinic",
    "college",
    "department",
    "division",
    "faculty",
    "for",
    "hospital",
    "institute",
    "institutes",
    "key",
    "lab",
    "laboratory",
    "national",
    "of",
    "research",
    "school",
    "science",
    "sciences",
    "state",
    "the",
    "univ",
    "universidad",
    "universidade",
    "universita",
    "universitat",
    "university",
}

TOKEN_RE = re.compile(r"[0-9a-z]+|[\u0400-\u04ff]+|[\u4e00-\u9fff]+", re.I)
ORCID_RE = re.compile(r"(\d{4}-\d{4}-\d{4}-[\dXx]{4})")


@dataclass(frozen=True)
class AuthorMention:
    """A single author occurrence in one publication."""

    index: int
    mention_id: str
    firstname: str
    lastname: str
    original_name: str
    doi: str
    article_id: str
    year: int | None
    affiliation: str
    label_orcid: str = ""
    given_tokens: tuple[str, ...] = field(default_factory=tuple)
    family_tokens: tuple[str, ...] = field(default_factory=tuple)

    @property
    def paper_key(self) -> str:
        return self.doi or self.article_id

    @property
    def given_key(self) -> str:
        return " ".join(self.given_tokens)

    @property
    def family_key(self) -> str:
        return " ".join(self.family_tokens)

    @property
    def canonical_name(self) -> str:
        return " ".join(self.given_tokens + self.family_tokens)

    @property
    def entity_name_key(self) -> str:
        return f"{self.family_key}|{self.given_key}"


@dataclass(frozen=True)
class PairFeatures:
    same_family: bool
    given_relation: str
    name_is_chinese_like: bool
    exact_canonical_name: bool
    affiliation_jaccard: float
    affiliation_weighted_jaccard: float
    coauthor_jaccard: float
    year_gap: int | None


@dataclass(frozen=True)
class PairDecision:
    same_author: bool
    rule: str
    score: float
    features: PairFeatures


@dataclass(frozen=True)
class DisambiguationConfig:
    """Thresholds for deterministic conservative author disambiguation."""

    algorithm: str = "framework_v1"
    profile: str = "conservative"
    max_block_size: int = 200
    example_limit: int = 25


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.size[left_root] < self.size[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        self.size[left_root] += self.size[right_root]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_year(value: Any) -> int | None:
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    return year if 1500 <= year <= 2200 else None


def normalize_orcid(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = ORCID_RE.search(text)
    return match.group(1).upper() if match else text.lower()


@lru_cache(maxsize=None)
def normalized_tokens(value: str) -> tuple[str, ...]:
    """Return stable lowercase tokens across Latin/Cyrillic/CJK scripts."""

    tokens: list[str] = []
    for token in preprocess_name(value).tokens:
        for part in TOKEN_RE.findall(token.ascii.lower()):
            if part:
                tokens.append(part)
    return tuple(tokens)


@lru_cache(maxsize=None)
def affiliation_tokens(value: str) -> frozenset[str]:
    tokens = {
        token
        for token in normalized_tokens(value)
        if len(token) >= 3 and token not in AFFILIATION_STOPWORDS
    }
    return frozenset(tokens)


def jaccard(left: set[str] | frozenset[str], right: set[str] | frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def weighted_jaccard(
    left: set[str] | frozenset[str],
    right: set[str] | frozenset[str],
    weights: Mapping[str, float],
) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    numerator = sum(weights.get(token, 1.0) for token in sorted(left & right))
    denominator = sum(weights.get(token, 1.0) for token in sorted(union))
    return numerator / denominator if denominator else 0.0


def f1(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def n_choose_2(n: int) -> int:
    return n * (n - 1) // 2


def row_to_mention(row: Mapping[str, Any], index: int) -> AuthorMention:
    firstname = str(row.get("firstname", "") or "").strip()
    lastname = str(row.get("lastname", "") or "").strip()
    original_name = str(row.get("original_name", "") or "").strip()
    doi = str(row.get("doi", "") or "").strip().lower()
    article_id = str(row.get("article_id", "") or "").strip().lower()
    mention_id = str(row.get("id") or row.get("mention_id") or f"row-{index}")
    return AuthorMention(
        index=index,
        mention_id=mention_id,
        firstname=firstname,
        lastname=lastname,
        original_name=original_name,
        doi=doi,
        article_id=article_id,
        year=safe_year(row.get("year")),
        affiliation=str(row.get("affiliation", "") or ""),
        label_orcid=normalize_orcid(row.get("orcid")),
        given_tokens=normalized_tokens(firstname),
        family_tokens=normalized_tokens(lastname),
    )


def load_labeled_mentions(path: Path) -> list[AuthorMention]:
    import json

    records = json.loads(path.read_text(encoding="utf-8"))
    mentions = [row_to_mention(row, index) for index, row in enumerate(records)]
    return [
        mention
        for mention in mentions
        if mention.label_orcid and mention.given_tokens and mention.family_tokens
    ]


def block_key(mention: AuthorMention) -> str | None:
    if not mention.family_tokens or not mention.given_tokens:
        return None
    return f"{mention.family_key}|{mention.given_tokens[0][:1]}"


def build_blocks(mentions: Iterable[AuthorMention]) -> dict[str, list[int]]:
    blocks: dict[str, list[int]] = defaultdict(list)
    for position, mention in enumerate(mentions):
        key = block_key(mention)
        if key:
            blocks[key].append(position)
    return blocks


def exact_name_subblocks(mentions: list[AuthorMention], positions: list[int]) -> list[list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for position in positions:
        groups[mentions[position].entity_name_key].append(position)
    return [group for group in groups.values() if len(group) >= 2]


def build_coauthor_sets(mentions: list[AuthorMention]) -> dict[int, set[str]]:
    names_by_paper: dict[str, set[str]] = defaultdict(set)
    for mention in mentions:
        if mention.paper_key:
            names_by_paper[mention.paper_key].add(mention.entity_name_key)

    coauthors: dict[int, set[str]] = {}
    for position, mention in enumerate(mentions):
        names = set(names_by_paper.get(mention.paper_key, set()))
        names.discard(mention.entity_name_key)
        coauthors[position] = names
    return coauthors


def build_affiliation_weights(mentions: list[AuthorMention]) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    for mention in mentions:
        document_frequency.update(affiliation_tokens(mention.affiliation))

    total = max(1, len(mentions))
    return {
        token: min(5.0, math.log((total + 1) / (frequency + 1)) + 1.0)
        for token, frequency in document_frequency.items()
    }


def given_relation(left: tuple[str, ...], right: tuple[str, ...]) -> str:
    if left == right:
        return "exact"
    if not left or not right:
        return "missing"
    if left[0] == right[0] and (left == right[: len(left)] or right == left[: len(right)]):
        return "prefix"
    left_initials = tuple(token[:1] for token in left if token)
    right_initials = tuple(token[:1] for token in right if token)
    if not left_initials or not right_initials or left_initials[0] != right_initials[0]:
        return "different"
    shortest = min(len(left_initials), len(right_initials))
    if left_initials[:shortest] == right_initials[:shortest]:
        if any(len(token) == 1 for token in left + right):
            return "initial_compatible"
        if left[0][:1] == right[0][:1]:
            return "first_initial_only"
    return "different"


def is_initial_only_given(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and all(len(token) == 1 for token in tokens)


@lru_cache(maxsize=None)
def is_pinyin_token(token: str) -> bool:
    compact = "".join(normalized_tokens(token))
    return bool(compact and is_valid_pinyin_name(compact)[0])


def is_chinese_like_name(mention: AuthorMention) -> bool:
    if not mention.family_tokens or not mention.given_tokens:
        return False
    family = "".join(mention.family_tokens)
    given = "".join(mention.given_tokens)
    return is_surname_pinyin(family) and is_pinyin_token(given)


def pair_features(
    left: AuthorMention,
    right: AuthorMention,
    left_affiliation: frozenset[str],
    right_affiliation: frozenset[str],
    left_coauthors: set[str],
    right_coauthors: set[str],
    affiliation_weights: Mapping[str, float],
) -> PairFeatures:
    year_gap = (
        abs(left.year - right.year)
        if left.year is not None and right.year is not None
        else None
    )
    return PairFeatures(
        same_family=left.family_tokens == right.family_tokens,
        given_relation=given_relation(left.given_tokens, right.given_tokens),
        name_is_chinese_like=is_chinese_like_name(left) or is_chinese_like_name(right),
        exact_canonical_name=left.entity_name_key == right.entity_name_key,
        affiliation_jaccard=jaccard(left_affiliation, right_affiliation),
        affiliation_weighted_jaccard=weighted_jaccard(
            left_affiliation,
            right_affiliation,
            affiliation_weights,
        ),
        coauthor_jaccard=jaccard(left_coauthors, right_coauthors),
        year_gap=year_gap,
    )


def baseline_exact_context_decision(features: PairFeatures) -> tuple[bool, str, float]:
    """Replicate the previous exact-name/context baseline for comparison."""

    if not features.exact_canonical_name:
        return False, "different_full_name", 0.0
    if features.year_gap is not None and features.year_gap > 15:
        return False, "year_gap_gt_15", 0.0
    if features.affiliation_jaccard >= 0.35:
        return True, "exact_name_affiliation_jaccard_ge_0.35", 0.78
    if features.coauthor_jaccard >= 0.15:
        return True, "exact_name_coauthor_jaccard_ge_0.15", 0.84
    if (
        features.year_gap is not None
        and features.year_gap <= 2
        and features.affiliation_jaccard >= 0.20
    ):
        return True, "exact_name_recent_affiliation_jaccard_ge_0.20", 0.65
    return False, "insufficient_context", 0.0


def framework_v1_decision(
    left: AuthorMention,
    right: AuthorMention,
    features: PairFeatures,
    profile: str = "conservative",
) -> tuple[bool, str, float]:
    """Conservative deterministic entity-resolution rules.

    The balanced profile is useful for ablation experiments.  The conservative
    profile is the production-facing default.
    """

    if not features.same_family:
        return False, "different_family", 0.0

    year_gap = features.year_gap
    aff = features.affiliation_weighted_jaccard
    raw_aff = features.affiliation_jaccard
    co = features.coauthor_jaccard
    relation = features.given_relation
    initial_only = is_initial_only_given(left.given_tokens) or is_initial_only_given(right.given_tokens)
    chinese_like = features.name_is_chinese_like

    if year_gap is not None and year_gap > 25 and co < 0.20 and aff < 0.75:
        return False, "year_gap_gt_25_without_strong_context", 0.0

    if relation == "exact":
        if co >= 0.12:
            return True, "exact_name_coauthor_jaccard_ge_0.12", 0.91
        if initial_only:
            if co >= 0.08 and aff >= 0.45:
                return True, "exact_initial_name_affiliation_and_coauthor", 0.82
            return False, "initial_only_name_requires_stronger_context", 0.0
        if chinese_like:
            if co >= 0.05 and aff >= 0.35:
                return True, "cn_like_exact_name_affiliation_and_coauthor", 0.86
            if profile == "balanced" and aff >= 0.58 and raw_aff >= 0.50:
                return True, "balanced_cn_like_exact_name_strong_affiliation", 0.72
            return False, "cn_like_exact_name_requires_coauthor_or_very_strong_context", 0.0
        if aff >= 0.42:
            return True, "exact_name_weighted_affiliation_ge_0.42", 0.82
        if year_gap is not None and year_gap <= 2 and aff >= 0.32 and raw_aff >= 0.20:
            return True, "exact_name_recent_weighted_affiliation_ge_0.32", 0.70
        if profile == "balanced" and aff >= 0.30 and raw_aff >= 0.20:
            return True, "balanced_exact_name_affiliation_ge_0.30", 0.66
        return True, "exact_non_chinese_full_name", 0.60

    if relation == "prefix":
        if co >= 0.16:
            return True, "given_prefix_coauthor_jaccard_ge_0.16", 0.88
        if aff >= 0.58 and (year_gap is None or year_gap <= 12):
            return True, "given_prefix_weighted_affiliation_ge_0.58", 0.82
        if aff >= 0.42 and raw_aff >= 0.35 and year_gap is not None and year_gap <= 5:
            return True, "given_prefix_recent_affiliation_ge_0.42", 0.76
        if profile == "balanced" and aff >= 0.35 and raw_aff >= 0.25:
            return True, "balanced_given_prefix_affiliation_ge_0.35", 0.68
        return False, "given_prefix_insufficient_context", 0.0

    if relation == "initial_compatible":
        if co >= 0.30:
            return True, "given_initial_coauthor_jaccard_ge_0.30", 0.90
        if aff >= 0.72 and raw_aff >= 0.55 and (year_gap is None or year_gap <= 8):
            return True, "given_initial_strong_affiliation_ge_0.72", 0.80
        if aff >= 0.58 and co >= 0.08:
            return True, "given_initial_affiliation_and_coauthor", 0.82
        if profile == "balanced" and aff >= 0.58 and raw_aff >= 0.45 and year_gap is not None and year_gap <= 5:
            return True, "balanced_given_initial_recent_affiliation", 0.66
        return False, "given_initial_insufficient_context", 0.0

    return False, f"given_relation_{relation}", 0.0


def decide_pair(
    left: AuthorMention,
    right: AuthorMention,
    left_affiliation: frozenset[str],
    right_affiliation: frozenset[str],
    left_coauthors: set[str],
    right_coauthors: set[str],
    affiliation_weights: Mapping[str, float],
    config: DisambiguationConfig,
) -> PairDecision:
    features = pair_features(
        left,
        right,
        left_affiliation,
        right_affiliation,
        left_coauthors,
        right_coauthors,
        affiliation_weights,
    )
    if config.algorithm == "baseline_exact_context":
        same_author, rule, score = baseline_exact_context_decision(features)
    elif config.algorithm == "framework_v1":
        same_author, rule, score = framework_v1_decision(left, right, features, config.profile)
    else:
        raise ValueError(f"Unknown author-disambiguation algorithm: {config.algorithm}")
    return PairDecision(same_author=same_author, rule=rule, score=score, features=features)


def b_cubed(mentions: list[AuthorMention], uf: UnionFind) -> dict[str, float]:
    predicted: dict[int, set[int]] = defaultdict(set)
    truth: dict[str, set[int]] = defaultdict(set)
    for position, mention in enumerate(mentions):
        predicted[uf.find(position)].add(position)
        truth[mention.label_orcid].add(position)

    precision_sum = 0.0
    recall_sum = 0.0
    for position, mention in enumerate(mentions):
        pred_cluster = predicted[uf.find(position)]
        true_cluster = truth[mention.label_orcid]
        overlap = len(pred_cluster & true_cluster)
        precision_sum += overlap / len(pred_cluster)
        recall_sum += overlap / len(true_cluster)
    n = len(mentions)
    precision = precision_sum / n if n else 0.0
    recall = recall_sum / n if n else 0.0
    return {"precision": precision, "recall": recall, "f1": f1(precision, recall)}


def cluster_pairwise(mentions: list[AuthorMention], uf: UnionFind) -> dict[str, float | int]:
    truth_cluster_sizes: Counter[str] = Counter(mention.label_orcid for mention in mentions)
    total_truth_pairs = sum(n_choose_2(size) for size in truth_cluster_sizes.values())

    predicted_labels: dict[int, Counter[str]] = defaultdict(Counter)
    for position, mention in enumerate(mentions):
        predicted_labels[uf.find(position)][mention.label_orcid] += 1

    predicted_pairs = 0
    tp = 0
    for label_counts in predicted_labels.values():
        cluster_size = sum(label_counts.values())
        predicted_pairs += n_choose_2(cluster_size)
        tp += sum(n_choose_2(size) for size in label_counts.values())

    fp = predicted_pairs - tp
    fn = total_truth_pairs - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1(precision, recall),
        "truth_pairs": total_truth_pairs,
        "predicted_pairs": predicted_pairs,
    }


def format_example(
    key: str,
    left: AuthorMention,
    right: AuthorMention,
    decision: PairDecision,
) -> dict[str, Any]:
    features = decision.features
    return {
        "block": key,
        "left_name": left.canonical_name,
        "right_name": right.canonical_name,
        "left_orcid": left.label_orcid,
        "right_orcid": right.label_orcid,
        "left_doi": left.paper_key,
        "right_doi": right.paper_key,
        "left_year": left.year,
        "right_year": right.year,
        "affiliation_jaccard": features.affiliation_jaccard,
        "affiliation_weighted_jaccard": features.affiliation_weighted_jaccard,
        "coauthor_jaccard": features.coauthor_jaccard,
        "given_relation": features.given_relation,
        "name_is_chinese_like": features.name_is_chinese_like,
        "rule": decision.rule,
        "score": decision.score,
    }


def evaluate_mentions(
    mentions: list[AuthorMention],
    config: DisambiguationConfig,
) -> dict[str, Any]:
    blocks = build_blocks(mentions)
    coauthors = build_coauthor_sets(mentions)
    affiliations = {
        position: affiliation_tokens(mention.affiliation)
        for position, mention in enumerate(mentions)
    }
    affiliation_weights = build_affiliation_weights(mentions)
    uf = UnionFind(len(mentions))

    pair_counts: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped_large_blocks = 0
    large_block_exact_subblocks = 0
    large_block_exact_subblock_candidate_pairs = 0

    for key, positions in blocks.items():
        candidate_groups = [positions]
        if len(positions) > config.max_block_size:
            skipped_large_blocks += 1
            candidate_groups = [
                group
                for group in exact_name_subblocks(mentions, positions)
                if len(group) <= config.max_block_size
            ]
            large_block_exact_subblocks += len(candidate_groups)
            large_block_exact_subblock_candidate_pairs += sum(
                n_choose_2(len(group)) for group in candidate_groups
            )

        for candidate_positions in candidate_groups:
            for left_position, right_position in combinations(candidate_positions, 2):
                left = mentions[left_position]
                right = mentions[right_position]
                if left.paper_key and left.paper_key == right.paper_key:
                    pair_counts["same_paper_skipped"] += 1
                    continue

                decision = decide_pair(
                    left,
                    right,
                    affiliations[left_position],
                    affiliations[right_position],
                    coauthors[left_position],
                    coauthors[right_position],
                    affiliation_weights,
                    config,
                )
                rule_counts[decision.rule] += 1

                same_truth = left.label_orcid == right.label_orcid
                if decision.same_author:
                    uf.union(left_position, right_position)

                bucket = ""
                if decision.same_author and same_truth:
                    pair_counts["tp"] += 1
                elif decision.same_author and not same_truth:
                    pair_counts["fp"] += 1
                    bucket = "false_positive"
                elif not decision.same_author and same_truth:
                    pair_counts["fn"] += 1
                    bucket = "false_negative"
                else:
                    pair_counts["tn"] += 1

                if bucket and len(examples[bucket]) < config.example_limit:
                    examples[bucket].append(format_example(key, left, right, decision))

    tp = pair_counts["tp"]
    fp = pair_counts["fp"]
    fn = pair_counts["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "algorithm": config.algorithm,
        "profile": config.profile,
        "labeled_mentions": len(mentions),
        "unique_orcid": len({mention.label_orcid for mention in mentions}),
        "blocks": len(blocks),
        "max_block_size": config.max_block_size,
        "skipped_large_blocks": skipped_large_blocks,
        "large_block_exact_subblocks": large_block_exact_subblocks,
        "large_block_exact_subblock_candidate_pairs": large_block_exact_subblock_candidate_pairs,
        "evaluated_pairs": tp + fp + fn + pair_counts["tn"],
        "same_paper_skipped_pairs": pair_counts["same_paper_skipped"],
        "candidate_pairwise": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": pair_counts["tn"],
            "precision": precision,
            "recall": recall,
            "f1": f1(precision, recall),
        },
        "cluster_pairwise": cluster_pairwise(mentions, uf),
        "b_cubed": b_cubed(mentions, uf),
        "rule_counts": dict(rule_counts.most_common()),
        "examples": dict(examples),
        "production_targets": {
            "candidate_pairwise_precision": 0.99,
            "cluster_pairwise_precision": 0.99,
            "b_cubed_f1": 0.95,
        },
    }


def evaluate_file(path: Path, config: DisambiguationConfig) -> dict[str, Any]:
    mentions = load_labeled_mentions(path)
    result = evaluate_mentions(mentions, config)
    result["dataset"] = str(path)
    result["dataset_sha256"] = sha256_file(path)
    return result
