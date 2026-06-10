# -*- coding: utf-8 -*-
"""Run frozen 301k strong-rescue benchmark variants.

This script intentionally uses the same frozen Crossref author records for all
profiles and writes machine-readable audit artifacts for the strong dual
single-token rescue check.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data.pinyin_syllables import PINYIN_SYLLABLES
from src.affiliation_analyzer import analyze_affiliation
from src.config_v8 import AblationConfig, get_config, reset_ablation_config, set_ablation_config
from src.surname_identifier_v8 import (
    NameDecision,
    NameRecord,
    _field_family_first_candidate_strength,
    _publication_candidate_group_corrections,
    adjust_by_person,
    batch_identify_surname_position_v8,
    preprocess_name,
)


STRONG_RESCUE_PREFIX = "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE"


def locate_default_dataset() -> Path:
    matches = sorted(Path("C:/istina").rglob("crossref_authors.json"))
    if not matches:
        raise FileNotFoundError("Could not find crossref_authors.json under C:/istina")
    return matches[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_mentor_records() -> List[Dict[str, Any]]:
    path = PROJECT_ROOT / "runs" / "advisor_doi_20260507" / "advisor_doi_crossref_api_authors.json"
    if not path.exists():
        return []
    return load_records(path)


def name_tokens(value: Optional[str]) -> List[str]:
    return [tok.ascii.lower() for tok in preprocess_name(value or "").tokens if tok.ascii]


def infer_proxy_order(record: Dict[str, Any]) -> Optional[str]:
    original_tokens = name_tokens(record.get("original_name"))
    lastname_tokens = name_tokens(record.get("lastname"))
    firstname_tokens = name_tokens(record.get("firstname"))

    if not original_tokens or not lastname_tokens or not firstname_tokens:
        return None
    if lastname_tokens == firstname_tokens:
        return None
    if original_tokens == lastname_tokens + firstname_tokens:
        return "family_first"
    if original_tokens == firstname_tokens + lastname_tokens:
        return "given_first"
    if original_tokens[: len(lastname_tokens)] == lastname_tokens:
        return "family_first"
    if original_tokens[: len(firstname_tokens)] == firstname_tokens:
        return "given_first"
    return None


def proxy_skip_reason(record: Dict[str, Any]) -> str:
    original_tokens = name_tokens(record.get("original_name"))
    lastname_tokens = name_tokens(record.get("lastname"))
    firstname_tokens = name_tokens(record.get("firstname"))
    if not original_tokens:
        return "missing_original_name"
    if not lastname_tokens:
        return "missing_lastname"
    if not firstname_tokens:
        return "missing_firstname"
    if lastname_tokens == firstname_tokens:
        return "duplicate_firstname_lastname"
    return "split_fields_not_token_aligned"


def canonical_publication_id(doi: Optional[str]) -> str:
    if not doi:
        return ""
    normalized = doi.lower().strip()
    return re.sub(r"/v\d+$", "", normalized)


def mentor_challenge_cases() -> List[tuple]:
    """Hand-audited advisor SPLIT challenge cases used for acceptance checks."""
    return [
        ("10.1038/nature14656", "M. H. Eileen", "Tan", "given_first"),
        ("10.1063/1.2137890", "Lan", "Jin", "given_first"),
        ("10.1016/j.jmmm.2006.01.156", "Lan", "Jin", "given_first"),
        ("10.24272/j.issn.2095-8137.2021.228", "Jian-Huan", "Yang", "given_first"),
        ("10.1016/j.ppnp.2022.103948", "M.G.", "Di Luca", "given_first"),
        ("10.4289/0013-8797.124.2.287", "Li", "Yan", "family_first"),
        ("10.4289/0013-8797.124.2.287", "Li", "Nan", "family_first"),
        ("10.1515/pac-2024-0024", "Thi My Hanh Le", "Le", "given_first"),
        ("10.3847/1538-4365/ac4414", "Y. Sophia \u6631", "Dai \u6234", "given_first"),
        ("10.3847/1538-4365/ac4414", "Lihwai \u4fd0 \u6689", "Lin \u6797", "given_first"),
        ("10.1111/jvs.13235", "Michele", "Di\u00a0Musciano", "given_first"),
        ("10.1088/1674-1056/ad6b84", "Jin \u52b2", "Zhan \u6e5b", "given_first"),
        ("10.1088/1674-1056/ad6b84", "Yi \u4e00", "Wang \u738b", "given_first"),
        ("10.1088/1674-1056/ad6b84", "Yu \u90c1", "Sui \u968b", "given_first"),
        ("10.1088/1674-1056/ad6b84", "Bo \u6ce2", "Song \u5b8b", "given_first"),
        ("10.1016/j.jece.2025.117378", "Anqi", "Zhao", "given_first"),
        ("10.1109/ton.2025.3592491", "Xu", "Shu", "family_first"),
        ("10.1109/ton.2025.3592491", "Xiaoshan", "Zhang", "given_first"),
        ("10.1007/s12665-023-10937-9", "Wang", "Lei", "family_first"),
    ]


def make_name_records(records: List[Dict[str, Any]], use_orcid: bool) -> List[NameRecord]:
    converted: List[NameRecord] = []
    for idx, rec in enumerate(records):
        person_id = rec.get("person_id")
        if use_orcid:
            person_id = person_id or rec.get("orcid")
        converted.append(
            NameRecord(
                record_id=str(idx),
                name_raw="",
                firstname_raw=rec.get("firstname"),
                lastname_raw=rec.get("lastname"),
                affiliation_raw=rec.get("affiliation"),
                source="CROSSREF",
                person_id=person_id,
                publication_id=rec.get("doi") or rec.get("article_id"),
                field_only=True,
            )
        )
    return converted


@contextmanager
def legacy_pinyin_without_dong(enabled: bool) -> Iterable[None]:
    had_dong = "dong" in PINYIN_SYLLABLES
    if enabled:
        PINYIN_SYLLABLES.discard("dong")
    try:
        yield
    finally:
        if had_dong:
            PINYIN_SYLLABLES.add("dong")
        else:
            PINYIN_SYLLABLES.discard("dong")


def has_strong_rescue(decision: NameDecision) -> bool:
    return any(code.startswith(STRONG_RESCUE_PREFIX) for code in decision.reason_codes)


def has_pub_override(decision: NameDecision) -> bool:
    return "PUB_PATTERN_OVERRIDE" in decision.reason_codes


def publication_context_flags(reason_codes: List[str]) -> List[str]:
    flags = []
    for code in reason_codes:
        if code == "CN_AFFILIATION":
            flags.append("AUTHOR_CN_AFFIL")
        elif code == "FIELD_FAMILY_CJK_SURNAME_HINT":
            flags.append("FAMILY_CJK_SURNAME_HINT")
        elif code.startswith("FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE_"):
            subtype = code[len("FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE_"):]
            flags.append(subtype.split("(", 1)[0])
    return sorted(set(flags))


def affiliation_country(affiliation: Optional[str]) -> Optional[str]:
    info = analyze_affiliation(affiliation) if affiliation else None
    return info.country if info else None


def reason_counter(decisions: Iterable[NameDecision]) -> Counter:
    counter: Counter = Counter()
    for decision in decisions:
        counter.update(decision.reason_codes)
    return counter


def write_reason_counts(path: Path, counter: Counter, denominator: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["reason_code", "count", "rate"])
        writer.writeheader()
        for code, count in counter.most_common():
            writer.writerow(
                {
                    "reason_code": code,
                    "count": count,
                    "rate": count / denominator if denominator else 0.0,
                }
            )


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            {key: csv_value(row.get(key)) for key in fieldnames}
            for row in rows
        )


def row_for_record(
    record_id: int,
    record: Dict[str, Any],
    decision: NameDecision,
    proxy_label: Optional[str],
) -> Dict[str, Any]:
    return {
        "record_id": record_id,
        "doi": record.get("doi") or record.get("article_id"),
        "canonical_publication_id": canonical_publication_id(record.get("doi") or record.get("article_id")),
        "firstname": record.get("firstname"),
        "lastname": record.get("lastname"),
        "original_name": record.get("original_name"),
        "person_id": record.get("person_id"),
        "orcid": record.get("orcid"),
        "affiliation": record.get("affiliation"),
        "affiliation_country": affiliation_country(record.get("affiliation")),
        "proxy_label": proxy_label,
        "predicted": decision.order,
        "confidence": decision.confidence,
        "reason_codes": decision.reason_codes,
    }


def clone_decision(decision: NameDecision) -> NameDecision:
    return NameDecision(
        order=decision.order,
        confidence=decision.confidence,
        mode=decision.mode,
        reason_codes=list(decision.reason_codes),
    )


def clone_decisions(decisions: Dict[str, NameDecision]) -> Dict[str, NameDecision]:
    return {record_id: clone_decision(decision) for record_id, decision in decisions.items()}


def decisions_differ(before: NameDecision, after: NameDecision) -> bool:
    return (
        before.order != after.order
        or before.confidence != after.confidence
        or before.mode != after.mode
        or before.reason_codes != after.reason_codes
    )


def transition_row(
    record_id: int,
    record: Dict[str, Any],
    before: NameDecision,
    after: NameDecision,
    proxy_label: Optional[str],
    change_type: str,
) -> Dict[str, Any]:
    return {
        "record_id": record_id,
        "doi": record.get("doi") or record.get("article_id"),
        "canonical_publication_id": canonical_publication_id(record.get("doi") or record.get("article_id")),
        "firstname": record.get("firstname"),
        "lastname": record.get("lastname"),
        "original_name": record.get("original_name"),
        "person_id": record.get("person_id"),
        "orcid": record.get("orcid"),
        "affiliation": record.get("affiliation"),
        "affiliation_country": affiliation_country(record.get("affiliation")),
        "proxy_label": proxy_label,
        "is_proxy_labeled": proxy_label is not None,
        "before_proxy_correct": before.order == proxy_label if proxy_label else None,
        "after_proxy_correct": after.order == proxy_label if proxy_label else None,
        "proxy_error_delta": (
            int(after.order != proxy_label) - int(before.order != proxy_label)
            if proxy_label
            else 0
        ),
        "candidate_strength": _field_family_first_candidate_strength(before.reason_codes),
        "publication_context_flags": publication_context_flags(before.reason_codes),
        "change_type": change_type,
        "before_predicted": before.order,
        "before_confidence": before.confidence,
        "before_reason_codes": before.reason_codes,
        "after_predicted": after.order,
        "after_confidence": after.confidence,
        "after_reason_codes": after.reason_codes,
    }


def profile_counts(
    records: List[Dict[str, Any]],
    decisions: Dict[str, NameDecision],
    proxy_labels: List[Optional[str]],
    stage: str,
) -> Dict[str, Any]:
    order_counts = Counter(decision.order for decision in decisions.values())
    proxy_labeled = sum(1 for label in proxy_labels if label is not None)
    proxy_errors = sum(
        1
        for idx, label in enumerate(proxy_labels)
        if label and decisions[str(idx)].order != label
    )
    canonical_proxy_error_groups = {
        canonical_publication_id(records[idx].get("doi") or records[idx].get("article_id"))
        for idx, label in enumerate(proxy_labels)
        if label and decisions[str(idx)].order != label
    }
    canonical_proxy_error_groups.discard("")
    return {
        "stage": stage,
        "n_records": len(records),
        "proxy_labeled": proxy_labeled,
        "order_counts": dict(order_counts),
        "proxy_errors": proxy_errors,
        "canonical_publication_proxy_error_groups": len(canonical_proxy_error_groups),
        "proxy_accuracy": (proxy_labeled - proxy_errors) / proxy_labeled if proxy_labeled else 0.0,
        "non_given_first_count": sum(
            1 for decision in decisions.values() if decision.order != "given_first"
        ),
        "strong_rescue_count": sum(1 for decision in decisions.values() if has_strong_rescue(decision)),
        "pub_override_count": sum(1 for decision in decisions.values() if has_pub_override(decision)),
    }


def mentor_challenge_summary(
    records: List[Dict[str, Any]],
    decisions: Dict[str, NameDecision],
) -> Dict[str, Any]:
    by_key = {
        (
            (record.get("doi") or record.get("article_id") or "").lower(),
            record.get("firstname") or "",
            record.get("lastname") or "",
        ): decisions[str(idx)]
        for idx, record in enumerate(records)
    }
    errors = []
    for doi, firstname, lastname, expected in mentor_challenge_cases():
        decision = by_key.get((doi.lower(), firstname, lastname))
        if decision is None:
            errors.append(
                {
                    "doi": doi,
                    "firstname": firstname,
                    "lastname": lastname,
                    "expected": expected,
                    "actual": None,
                    "error": "missing",
                }
            )
            continue
        if decision.order != expected:
            errors.append(
                {
                    "doi": doi,
                    "firstname": firstname,
                    "lastname": lastname,
                    "expected": expected,
                    "actual": decision.order,
                    "confidence": decision.confidence,
                    "reason_codes": decision.reason_codes,
                }
            )
    total = len(mentor_challenge_cases())
    return {
        "mentor_total": total,
        "mentor_correct": total - len(errors),
        "mentor_errors": len(errors),
        "mentor_error_rows": errors,
    }


def run_profile(
    records: List[Dict[str, Any]],
    mentor_records: List[Dict[str, Any]],
    name: str,
    config: AblationConfig,
    use_orcid: bool,
    legacy_without_dong: bool,
    output_dir: Path,
) -> Dict[str, Any]:
    name_records = make_name_records(records, use_orcid=use_orcid)
    proxy_labels = [infer_proxy_order(record) for record in records]

    with legacy_pinyin_without_dong(legacy_without_dong):
        set_ablation_config(config)
        try:
            local_decisions = batch_identify_surname_position_v8(
                name_records,
                source="CROSSREF",
                enable_person_consistency=False,
                enable_pub_consistency=False,
            )
            cfg = get_config("CROSSREF")

            person_decisions = clone_decisions(local_decisions)
            if config.enable_person_consistency and not config.disable_batch_consistency:
                person_decisions = adjust_by_person(name_records, person_decisions, cfg)

            final_decisions = clone_decisions(person_decisions)
            pub_corrections = []
            if config.enable_pub_consistency and not config.disable_batch_consistency:
                pub_corrections = _publication_candidate_group_corrections(
                    name_records,
                    final_decisions,
                    cfg,
                )
                for correction in pub_corrections:
                    final_decisions[correction.record_id] = correction.after
            mentor_decisions = (
                batch_identify_surname_position_v8(
                    make_name_records(mentor_records, use_orcid=use_orcid),
                    source="CROSSREF",
                    enable_person_consistency=config.enable_person_consistency,
                    enable_pub_consistency=config.enable_pub_consistency,
                )
                if mentor_records
                else {}
            )
        finally:
            reset_ablation_config()
    mentor_summary = (
        mentor_challenge_summary(mentor_records, mentor_decisions)
        if mentor_records and mentor_decisions
        else {"mentor_total": 0, "mentor_correct": 0, "mentor_errors": 0, "mentor_error_rows": []}
    )

    skipped = [idx for idx, label in enumerate(proxy_labels) if label is None]
    errors: List[Dict[str, Any]] = []
    non_given_rows: List[Dict[str, Any]] = []
    strong_rows: List[Dict[str, Any]] = []
    person_change_rows: List[Dict[str, Any]] = []
    publication_change_rows: List[Dict[str, Any]] = []

    order_counts = Counter(decision.order for decision in final_decisions.values())
    for idx, record in enumerate(records):
        record_key = str(idx)
        decision = final_decisions[record_key]
        proxy_label = proxy_labels[idx]
        if proxy_label and decision.order != proxy_label:
            errors.append(row_for_record(idx, record, decision, proxy_label))
        if decision.order != "given_first":
            non_given_rows.append(row_for_record(idx, record, decision, proxy_label))
        if has_strong_rescue(decision):
            strong_rows.append(row_for_record(idx, record, decision, proxy_label))
        if decisions_differ(local_decisions[record_key], person_decisions[record_key]):
            person_change_rows.append(
                transition_row(
                    idx,
                    record,
                    local_decisions[record_key],
                    person_decisions[record_key],
                    proxy_label,
                    "person_consistency",
                )
            )
        if decisions_differ(person_decisions[record_key], final_decisions[record_key]):
            publication_change_rows.append(
                transition_row(
                    idx,
                    record,
                    person_decisions[record_key],
                    final_decisions[record_key],
                    proxy_label,
                    "publication_candidate_group",
                )
            )

    profile_dir = output_dir / name
    profile_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(profile_dir / "proxy_errors.jsonl", errors)
    write_jsonl(
        profile_dir / "proxy_skipped_records.jsonl",
        [
            {
                "record_id": idx,
                "skip_reason": proxy_skip_reason(records[idx]),
                "doi": records[idx].get("doi") or records[idx].get("article_id"),
                "firstname": records[idx].get("firstname"),
                "lastname": records[idx].get("lastname"),
                "original_name": records[idx].get("original_name"),
                "orcid": records[idx].get("orcid"),
            }
            for idx in skipped
        ],
    )
    write_jsonl(profile_dir / "non_given_first_records.jsonl", non_given_rows)
    write_reason_counts(
        profile_dir / "non_given_first_reason_counts.csv",
        reason_counter(final_decisions[str(row["record_id"])] for row in non_given_rows),
        len(non_given_rows),
    )
    write_jsonl(profile_dir / "person_consistency_changes.jsonl", person_change_rows)
    write_csv(
        profile_dir / "person_consistency_changes.csv",
        person_change_rows,
        fieldnames=[
            "record_id",
            "doi",
            "canonical_publication_id",
            "firstname",
            "lastname",
            "original_name",
            "person_id",
            "orcid",
            "affiliation_country",
            "proxy_label",
            "is_proxy_labeled",
            "before_proxy_correct",
            "after_proxy_correct",
            "proxy_error_delta",
            "before_predicted",
            "before_confidence",
            "before_reason_codes",
            "after_predicted",
            "after_confidence",
            "after_reason_codes",
        ],
    )
    write_jsonl(profile_dir / "publication_candidate_group_changes.jsonl", publication_change_rows)
    write_csv(
        profile_dir / "publication_candidate_group_changes.csv",
        publication_change_rows,
        fieldnames=[
            "record_id",
            "doi",
            "canonical_publication_id",
            "firstname",
            "lastname",
            "original_name",
            "person_id",
            "orcid",
            "affiliation_country",
            "proxy_label",
            "is_proxy_labeled",
            "before_proxy_correct",
            "after_proxy_correct",
            "proxy_error_delta",
            "candidate_strength",
            "publication_context_flags",
            "before_predicted",
            "before_confidence",
            "before_reason_codes",
            "after_predicted",
            "after_confidence",
            "after_reason_codes",
        ],
    )
    publication_audit_rows = [
        {
            "record_id": correction.record_id,
            "doi": correction.publication_id,
            "canonical_publication_id": canonical_publication_id(correction.publication_id),
            "firstname": records[int(correction.record_id)].get("firstname"),
            "lastname": records[int(correction.record_id)].get("lastname"),
            "person_id": records[int(correction.record_id)].get("person_id"),
            "orcid": records[int(correction.record_id)].get("orcid"),
            "affiliation": records[int(correction.record_id)].get("affiliation"),
            "affiliation_country": affiliation_country(records[int(correction.record_id)].get("affiliation")),
            "proxy_label": proxy_labels[int(correction.record_id)],
            "is_proxy_labeled": proxy_labels[int(correction.record_id)] is not None,
            "before_proxy_correct": (
                correction.before.order == proxy_labels[int(correction.record_id)]
                if proxy_labels[int(correction.record_id)]
                else None
            ),
            "after_proxy_correct": (
                correction.after.order == proxy_labels[int(correction.record_id)]
                if proxy_labels[int(correction.record_id)]
                else None
            ),
            "proxy_error_delta": (
                int(correction.after.order != proxy_labels[int(correction.record_id)])
                - int(correction.before.order != proxy_labels[int(correction.record_id)])
                if proxy_labels[int(correction.record_id)]
                else 0
            ),
            "candidate_strength": correction.candidate_strength,
            "candidate_count": correction.candidate_count,
            "complete_count": correction.complete_count,
            "candidate_share": correction.candidate_share,
            "strong_candidate_count": correction.strong_candidate_count,
            "weighted_candidate_strength_sum": correction.weighted_candidate_strength_sum,
            "publication_context_flags": publication_context_flags(correction.before.reason_codes),
            "suppressed": correction.suppressed,
            "suppression_reason": correction.suppression_reason,
            "before_predicted": correction.before.order,
            "before_confidence": correction.before.confidence,
            "before_reason_codes": correction.before.reason_codes,
            "after_predicted": correction.after.order,
            "after_confidence": correction.after.confidence,
            "after_reason_codes": correction.after.reason_codes,
        }
        for correction in pub_corrections
    ]
    write_jsonl(profile_dir / "publication_candidate_group_audit.jsonl", publication_audit_rows)
    write_csv(
        profile_dir / "publication_candidate_group_audit.csv",
        publication_audit_rows,
        fieldnames=[
            "record_id",
            "doi",
            "canonical_publication_id",
            "firstname",
            "lastname",
            "person_id",
            "orcid",
            "affiliation",
            "affiliation_country",
            "proxy_label",
            "is_proxy_labeled",
            "before_proxy_correct",
            "after_proxy_correct",
            "proxy_error_delta",
            "candidate_strength",
            "candidate_count",
            "complete_count",
            "candidate_share",
            "strong_candidate_count",
            "weighted_candidate_strength_sum",
            "publication_context_flags",
            "suppressed",
            "suppression_reason",
            "before_predicted",
            "before_confidence",
            "before_reason_codes",
            "after_predicted",
            "after_confidence",
            "after_reason_codes",
        ],
    )

    stage_summaries = [
        profile_counts(records, local_decisions, proxy_labels, "local"),
        profile_counts(records, person_decisions, proxy_labels, "after_person"),
        profile_counts(records, final_decisions, proxy_labels, "after_publication"),
    ]
    canonical_error_groups: Dict[str, Dict[str, Any]] = {}
    for idx, proxy_label in enumerate(proxy_labels):
        if not proxy_label or final_decisions[str(idx)].order == proxy_label:
            continue
        doi = records[idx].get("doi") or records[idx].get("article_id")
        canonical_id = canonical_publication_id(doi)
        bucket = canonical_error_groups.setdefault(
            canonical_id,
            {
                "canonical_publication_id": canonical_id,
                "dois": [],
                "record_ids": [],
                "proxy_error_count": 0,
            },
        )
        if doi and doi not in bucket["dois"]:
            bucket["dois"].append(doi)
        bucket["record_ids"].append(idx)
        bucket["proxy_error_count"] += 1
    write_jsonl(
        profile_dir / "canonical_publication_proxy_error_groups.jsonl",
        canonical_error_groups.values(),
    )
    write_jsonl(profile_dir / "mentor_challenge_errors.jsonl", mentor_summary["mentor_error_rows"])
    with (profile_dir / "stage_summaries.json").open("w", encoding="utf-8") as fh:
        json.dump(stage_summaries, fh, indent=2, ensure_ascii=False)
    write_csv(
        profile_dir / "stage_metrics.csv",
        stage_summaries,
        fieldnames=[
            "stage",
            "n_records",
            "proxy_labeled",
            "order_counts",
            "proxy_errors",
            "canonical_publication_proxy_error_groups",
            "proxy_accuracy",
            "non_given_first_count",
            "strong_rescue_count",
            "pub_override_count",
        ],
    )

    if strong_rows:
        write_jsonl(profile_dir / "strong_rescue_details.jsonl", strong_rows)
        write_csv(
            profile_dir / "strong_rescue_details.csv",
            [
                {
                    **row,
                    "reason_codes": "; ".join(row["reason_codes"]),
                }
                for row in strong_rows
            ],
        )
        grouped: Dict[tuple, Dict[str, Any]] = {}
        for row in strong_rows:
            key = (row.get("firstname") or "", row.get("lastname") or "")
            bucket = grouped.setdefault(
                key,
                {
                    "firstname": key[0],
                    "lastname": key[1],
                    "count": 0,
                    "record_ids": [],
                    "dois": [],
                    "example_reasons": row["reason_codes"],
                },
            )
            bucket["count"] += 1
            bucket["record_ids"].append(row["record_id"])
            doi = row.get("doi")
            if doi and doi not in bucket["dois"]:
                bucket["dois"].append(doi)
        write_csv(
            profile_dir / "strong_rescue_by_firstname_lastname.csv",
            [
                {
                    **bucket,
                    "record_ids": ";".join(str(item) for item in bucket["record_ids"]),
                    "dois": ";".join(bucket["dois"]),
                    "example_reasons": "; ".join(bucket["example_reasons"]),
                }
                for bucket in sorted(grouped.values(), key=lambda item: (-item["count"], item["firstname"], item["lastname"]))
            ],
        )

    proxy_labeled = len(records) - len(skipped)
    summary = {
        "config_name": name,
        "use_orcid_as_person_id": use_orcid,
        "legacy_pinyin_without_dong": legacy_without_dong,
        "n_records": len(records),
        "proxy_labeled": proxy_labeled,
        "skipped": len(skipped),
        "skipped_reasons": dict(Counter(proxy_skip_reason(records[idx]) for idx in skipped)),
        "order_counts": dict(order_counts),
        "proxy_errors": len(errors),
        "record_level_proxy_errors": len(errors),
        "local_proxy_errors": stage_summaries[0]["proxy_errors"],
        "after_person_proxy_errors": stage_summaries[1]["proxy_errors"],
        "after_publication_proxy_errors": stage_summaries[2]["proxy_errors"],
        "mentor_errors": mentor_summary["mentor_errors"],
        "mentor_correct": mentor_summary["mentor_correct"],
        "mentor_total": mentor_summary["mentor_total"],
        "canonical_publication_proxy_error_groups": len(canonical_error_groups),
        "proxy_accuracy": (proxy_labeled - len(errors)) / proxy_labeled if proxy_labeled else 0.0,
        "unknown_count": order_counts.get("unknown", 0),
        "family_first_count": order_counts.get("family_first", 0),
        "non_given_first_count": len(non_given_rows),
        "strong_rescue_count": len(strong_rows),
        "pub_override_count": sum(1 for decision in final_decisions.values() if has_pub_override(decision)),
        "person_consistency_change_count": len(person_change_rows),
        "publication_candidate_group_change_count": len(publication_change_rows),
        "publication_candidate_group_applied_count": sum(1 for correction in pub_corrections if not correction.suppressed),
        "publication_candidate_group_suppressed_count": sum(1 for correction in pub_corrections if correction.suppressed),
        "publication_proxy_error_delta": stage_summaries[2]["proxy_errors"] - stage_summaries[1]["proxy_errors"],
    }
    with (profile_dir / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    return summary


def write_n_explanation(output_dir: Path, records: List[Dict[str, Any]], dataset_path: Path) -> Dict[str, Any]:
    proxy_labels = [infer_proxy_order(record) for record in records]
    skipped = [idx for idx, label in enumerate(proxy_labels) if label is None]
    skipped_reasons = Counter(proxy_skip_reason(records[idx]) for idx in skipped)
    explanation = {
        "dataset_path": str(dataset_path),
        "dataset_sha256": sha256_file(dataset_path),
        "n_input_records": len(records),
        "n_proxy_labeled_records": len(records) - len(skipped),
        "n_skipped_by_proxy_label": len(skipped),
        "skipped_reasons": dict(skipped_reasons),
        "interpretation": (
            "301586 is the frozen input record count. 301146 is the older "
            "benchmark-compatible proxy-labeled count after excluding 440 "
            "records whose split fields are duplicate or not token-aligned."
        ),
    }
    with (output_dir / "n_explanation.json").open("w", encoding="utf-8") as fh:
        json.dump(explanation, fh, indent=2, ensure_ascii=False)
    return explanation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "runs" / "strong_rescue_policy_grid_20260514",
    )
    args = parser.parse_args()

    dataset_path = args.dataset or locate_default_dataset()
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(dataset_path)
    mentor_records = load_mentor_records()

    n_explanation = write_n_explanation(output_dir, records, dataset_path)
    def grid_config(
        *,
        enable_strong_rescue: bool,
        require_cn_context: bool = True,
        enable_publication_correction: bool,
        min_count: int = 8,
        min_share: float = 0.80,
        min_strong_count: int = 2,
        min_strength_sum: float = 8.0,
        enable_guard: bool = True,
        enable_pub_consistency: bool = True,
    ) -> AblationConfig:
        return AblationConfig(
            enable_strong_dual_single_rescue=enable_strong_rescue,
            strong_dual_single_rescue_ratio=23.0,
            strong_dual_single_rescue_given_min_share=2.0,
            strong_dual_single_rescue_family_max_share=0.1,
            strong_dual_single_rescue_require_cn_context=require_cn_context,
            enable_pub_consistency=enable_pub_consistency,
            enable_publication_candidate_group_correction=enable_publication_correction,
            publication_candidate_group_min_count=min_count,
            publication_candidate_group_min_share=min_share,
            publication_candidate_group_min_strong_count=min_strong_count,
            publication_candidate_group_min_strength_sum=min_strength_sum,
            enable_publication_external_split_confidence_guard=enable_guard,
        )

    profiles = [
        (
            "A_strong_off_publication_off",
            grid_config(
                enable_strong_rescue=False,
                enable_publication_correction=False,
                enable_pub_consistency=False,
            ),
            True,
            False,
        ),
        (
            "B_strong_off_publication_current",
            grid_config(
                enable_strong_rescue=False,
                enable_publication_correction=True,
                min_count=4,
                min_share=0.40,
                min_strong_count=0,
                min_strength_sum=0.0,
                enable_guard=False,
            ),
            True,
            False,
        ),
        (
            "C_strong_off_publication_strict",
            grid_config(
                enable_strong_rescue=False,
                enable_publication_correction=True,
            ),
            True,
            False,
        ),
        (
            "D_strong_on_no_context_publication_off",
            grid_config(
                enable_strong_rescue=True,
                require_cn_context=False,
                enable_publication_correction=False,
                enable_pub_consistency=False,
            ),
            True,
            False,
        ),
        (
            "E_strong_on_doi_context_publication_off",
            grid_config(
                enable_strong_rescue=True,
                require_cn_context=True,
                enable_publication_correction=False,
                enable_pub_consistency=False,
            ),
            True,
            False,
        ),
        (
            "F_recall_experimental_doi_context_strict",
            grid_config(
                enable_strong_rescue=True,
                require_cn_context=True,
                enable_publication_correction=True,
            ),
            True,
            False,
        ),
        (
            "G_previous_139_old",
            grid_config(
                enable_strong_rescue=False,
                enable_publication_correction=True,
                min_count=4,
                min_share=0.40,
                min_strong_count=0,
                min_strength_sum=0.0,
                enable_guard=False,
            ),
            False,
            True,
        ),
    ]
    summaries = [
        run_profile(records, mentor_records, name, config, use_orcid, legacy_without_dong, output_dir)
        for name, config, use_orcid, legacy_without_dong in profiles
    ]

    manifest = {
        "dataset": n_explanation,
        "mentor_dataset": {
            "path": str(PROJECT_ROOT / "runs" / "advisor_doi_20260507" / "advisor_doi_crossref_api_authors.json"),
            "n_records": len(mentor_records),
        },
        "profiles": summaries,
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    write_csv(output_dir / "metrics.csv", summaries)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
