# -*- coding: utf-8 -*-
"""Leak-free large-scale evaluation for the mentor experiment design.

The algorithm receives only a constructed full-name string. Split Crossref
fields are used to construct the two tested orders and are never passed as
features to the model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.non_chinese_surnames import is_non_chinese_surname
from src.pinyin_validator import is_valid_pinyin_name
from src.config_v8 import AblationConfig, get_config, set_ablation_config
from src.surname_identifier_v8 import (
    NameDecision,
    NameRecord,
    adjust_by_person,
    adjust_by_publication,
    local_decision,
    preprocess_name,
)


CONTEXT_MODES = {
    "none": (False, False),
    "publication": (False, True),
    "person": (True, False),
    "person_publication": (True, True),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=None)
def normalized_tokens(value: str) -> Tuple[str, ...]:
    return tuple(token.ascii.lower() for token in preprocess_name(value).tokens if token.ascii)


@lru_cache(maxsize=None)
def is_pinyin_component(value: str) -> bool:
    compact = "".join(normalized_tokens(value))
    return bool(compact and is_valid_pinyin_name(compact)[0])


@lru_cache(maxsize=None)
def is_known_non_chinese_component(value: str) -> bool:
    tokens = normalized_tokens(value)
    if not tokens:
        return False
    candidates = {tokens[0], "".join(tokens), " ".join(tokens)}
    return any(is_non_chinese_surname(candidate) for candidate in candidates)


def load_candidates(path: Path) -> List[Dict[str, Any]]:
    records = json.loads(path.read_text(encoding="utf-8"))
    return [
        record
        for record in records
        if record.get("firstname")
        and record.get("lastname")
        and is_pinyin_component(str(record["firstname"]))
        and is_pinyin_component(str(record["lastname"]))
    ]


def load_all_split_names(path: Path) -> List[Dict[str, Any]]:
    """Load every record with non-empty structured given/family fields."""
    records = json.loads(path.read_text(encoding="utf-8"))
    return [
        record
        for record in records
        if str(record.get("firstname", "")).strip()
        and str(record.get("lastname", "")).strip()
    ]


def name_pair_bucket(row: Dict[str, Any]) -> int:
    """Assign a normalized name pair to a deterministic five-way split."""
    key = (
        " ".join(normalized_tokens(str(row["firstname"])))
        + "|"
        + " ".join(normalized_tokens(str(row["lastname"])))
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(key).digest()[:4], "big") % 5


def build_records(
    rows: Iterable[Dict[str, Any]],
    order: str,
    source: str,
) -> Tuple[List[NameRecord], Dict[str, bool]]:
    records: List[NameRecord] = []
    non_chinese_flags: Dict[str, bool] = {}

    for index, row in enumerate(rows):
        firstname = str(row["firstname"]).strip()
        lastname = str(row["lastname"]).strip()
        name_raw = (
            f"{firstname} {lastname}"
            if order == "given_first"
            else f"{lastname} {firstname}"
        )
        record_id = str(index)
        records.append(
            NameRecord(
                record_id=record_id,
                source=source,
                person_id=row.get("orcid") or None,
                publication_id=row.get("doi") or row.get("article_id") or None,
                name_raw=name_raw,
                affiliation_raw=row.get("affiliation"),
            )
        )
        non_chinese_flags[record_id] = is_known_non_chinese_component(lastname)

    return records, non_chinese_flags


def summarize(
    records: List[NameRecord],
    decisions: Dict[str, NameDecision],
    expected_order: str,
    non_chinese_flags: Dict[str, bool],
) -> Dict[str, Any]:
    records_by_id = {record.record_id: record for record in records}
    total = len(decisions)
    error_ids = [
        record_id
        for record_id, decision in decisions.items()
        if decision.order not in (expected_order, "unknown")
    ]
    unknown_ids = [
        record_id
        for record_id, decision in decisions.items()
        if decision.order == "unknown"
    ]
    non_chinese_ids = [record_id for record_id, flag in non_chinese_flags.items() if flag]
    non_chinese_error_ids = [record_id for record_id in error_ids if non_chinese_flags[record_id]]
    non_chinese_unknown_ids = [record_id for record_id in unknown_ids if non_chinese_flags[record_id]]

    return {
        "n_records": total,
        "errors": len(error_ids),
        "error_rate": len(error_ids) / total if total else 0.0,
        "unknown": len(unknown_ids),
        "unknown_rate": len(unknown_ids) / total if total else 0.0,
        "coverage": (total - len(unknown_ids)) / total if total else 0.0,
        "mode_counts": dict(Counter(decision.mode for decision in decisions.values())),
        "order_counts": dict(Counter(decision.order for decision in decisions.values())),
        "known_non_chinese_records": len(non_chinese_ids),
        "known_non_chinese_errors": len(non_chinese_error_ids),
        "known_non_chinese_unknown": len(non_chinese_unknown_ids),
        "known_non_chinese_chinese_mode": sum(
            1
            for record_id in non_chinese_ids
            if decisions[record_id].mode == "CHINESE"
        ),
        "error_samples": [
            {
                "record_id": record_id,
                "name_raw": records_by_id[record_id].name_raw,
                "publication_id": records_by_id[record_id].publication_id,
                "order": decisions[record_id].order,
                "mode": decisions[record_id].mode,
                "confidence": decisions[record_id].confidence,
                "reason_codes": decisions[record_id].reason_codes,
                "known_non_chinese": non_chinese_flags[record_id],
            }
            for record_id in error_ids[:25]
        ],
    }


def evaluate(
    path: Path,
    source: str,
    surname_frequency_strategy: str,
    surname_share_ratio_threshold: float,
    publication_same_mode_only: bool,
    pair_hash_bucket: int | None = None,
    enable_corpus_role_model: bool = True,
    enable_jmnedict_role_model: bool = True,
    enable_ssa_census_role_model: bool = True,
    candidate_filter: str = "pinyin",
) -> Dict[str, Any]:
    set_ablation_config(
        AblationConfig(
            surname_freq_strategy=surname_frequency_strategy,
            surname_share_ratio_threshold=surname_share_ratio_threshold,
            publication_same_mode_only=publication_same_mode_only,
            enable_corpus_role_model=enable_corpus_role_model,
            enable_jmnedict_role_model=enable_jmnedict_role_model,
            enable_ssa_census_role_model=enable_ssa_census_role_model,
        )
    )
    rows = load_candidates(path) if candidate_filter == "pinyin" else load_all_split_names(path)
    if pair_hash_bucket is not None:
        rows = [row for row in rows if name_pair_bucket(row) == pair_hash_bucket]
    results: Dict[str, Any] = {
        "dataset": str(path),
        "dataset_sha256": sha256_file(path),
        "candidate_records": len(rows),
        "unique_name_pairs": len(
            {
                (tuple(normalized_tokens(str(row["firstname"]))), tuple(normalized_tokens(str(row["lastname"]))))
                for row in rows
            }
        ),
        "source": source,
        "surname_frequency_strategy": surname_frequency_strategy,
        "surname_share_ratio_threshold": surname_share_ratio_threshold,
        "publication_same_mode_only": publication_same_mode_only,
        "pair_hash_bucket": pair_hash_bucket,
        "enable_corpus_role_model": enable_corpus_role_model,
        "enable_jmnedict_role_model": enable_jmnedict_role_model,
        "enable_ssa_census_role_model": enable_ssa_census_role_model,
        "candidate_filter": candidate_filter,
        "results": {},
    }

    for expected_order in ("given_first", "family_first"):
        records, non_chinese_flags = build_records(rows, expected_order, source)
        config = get_config(source)
        local_decisions = {
            record.record_id: local_decision(record, config)
            for record in records
        }
        order_results: Dict[str, Any] = {}
        for mode_name, (person_enabled, publication_enabled) in CONTEXT_MODES.items():
            decisions = dict(local_decisions)
            if publication_enabled:
                decisions = adjust_by_publication(records, decisions, config)
            if person_enabled:
                decisions = adjust_by_person(records, decisions, config)
            order_results[mode_name] = summarize(
                records,
                decisions,
                expected_order,
                non_chinese_flags,
            )
        results["results"][expected_order] = order_results

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", default="CROSSREF")
    parser.add_argument(
        "--surname-frequency-strategy",
        choices=("share_ratio", "rank_gap", "freq_disabled"),
        default="share_ratio",
    )
    parser.add_argument("--surname-share-ratio-threshold", type=float, default=1.0)
    parser.add_argument("--publication-same-mode-only", action="store_true")
    parser.add_argument("--pair-hash-bucket", type=int, choices=range(5))
    parser.add_argument("--disable-corpus-role-model", action="store_true")
    parser.add_argument("--disable-jmnedict-role-model", action="store_true")
    parser.add_argument("--disable-ssa-census-role-model", action="store_true")
    parser.add_argument("--candidate-filter", choices=("pinyin", "all"), default="pinyin")
    args = parser.parse_args()

    result = evaluate(
        args.dataset,
        args.source,
        args.surname_frequency_strategy,
        args.surname_share_ratio_threshold,
        args.publication_same_mode_only,
        args.pair_hash_bucket,
        not args.disable_corpus_role_model,
        not args.disable_jmnedict_role_model,
        not args.disable_ssa_census_role_model,
        args.candidate_filter,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "dataset_sha256": result["dataset_sha256"],
        "candidate_records": result["candidate_records"],
        "unique_name_pairs": result["unique_name_pairs"],
        "surname_frequency_strategy": result["surname_frequency_strategy"],
        "surname_share_ratio_threshold": result["surname_share_ratio_threshold"],
        "publication_same_mode_only": result["publication_same_mode_only"],
        "pair_hash_bucket": result["pair_hash_bucket"],
        "enable_corpus_role_model": result["enable_corpus_role_model"],
        "enable_jmnedict_role_model": result["enable_jmnedict_role_model"],
        "enable_ssa_census_role_model": result["enable_ssa_census_role_model"],
        "candidate_filter": result["candidate_filter"],
        "results": {
            order: {
                mode: {
                    key: metrics[key]
                    for key in (
                        "errors",
                        "error_rate",
                        "unknown",
                        "unknown_rate",
                        "known_non_chinese_records",
                        "known_non_chinese_errors",
                        "known_non_chinese_unknown",
                        "known_non_chinese_chinese_mode",
                    )
                }
                for mode, metrics in modes.items()
            }
            for order, modes in result["results"].items()
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
