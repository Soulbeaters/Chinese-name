# -*- coding: utf-8 -*-
"""Sweep publication-correction middle grid with strong rescue fixed off."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.strong_rescue_frozen_benchmark import (
    canonical_publication_id,
    clone_decisions,
    csv_value,
    infer_proxy_order,
    legacy_pinyin_without_dong,
    load_mentor_records,
    load_records,
    locate_default_dataset,
    make_name_records,
    mentor_challenge_cases,
    publication_context_flags,
    sha256_file,
    write_csv,
    write_jsonl,
)
from src.config_v8 import AblationConfig, get_config, reset_ablation_config, set_ablation_config
from src.surname_identifier_v8 import (
    NameDecision,
    _publication_candidate_group_corrections,
    adjust_by_person,
    batch_identify_surname_position_v8,
)


def publication_config(
    *,
    enabled: bool,
    min_count: int = 8,
    min_share: float = 0.80,
    min_strong_count: int = 2,
    min_strength_sum: float = 8.0,
    guard: bool = False,
) -> AblationConfig:
    return AblationConfig(
        enable_strong_dual_single_rescue=False,
        enable_publication_candidate_group_correction=enabled,
        publication_candidate_group_min_count=min_count,
        publication_candidate_group_min_share=min_share,
        publication_candidate_group_min_strong_count=min_strong_count,
        publication_candidate_group_min_strength_sum=min_strength_sum,
        enable_publication_external_split_confidence_guard=guard,
    )


def strong_config(*, require_cn_context: bool) -> AblationConfig:
    return AblationConfig(
        enable_strong_dual_single_rescue=True,
        strong_dual_single_rescue_require_cn_context=require_cn_context,
        enable_publication_candidate_group_correction=False,
    )


def build_middle_profiles() -> List[Dict[str, Any]]:
    profiles = [
        {"name": "A_publication_off", "config": publication_config(enabled=False)},
        {
            "name": "B_publication_current",
            "config": publication_config(
                enabled=True,
                min_count=4,
                min_share=0.40,
                min_strong_count=0,
                min_strength_sum=0.0,
            ),
        },
    ]
    for name, min_count, min_share in [
        ("P1_count4_share060", 4, 0.60),
        ("P2_count4_share070", 4, 0.70),
        ("P3_count5_share060", 5, 0.60),
        ("P4_count5_share070", 5, 0.70),
        ("P5_count5_share080", 5, 0.80),
        ("P6_count6_share070", 6, 0.70),
        ("P7_count6_share080", 6, 0.80),
        ("P8_count7_share070", 7, 0.70),
        ("P9_count7_share080", 7, 0.80),
    ]:
        profiles.append(
            {
                "name": name,
                "config": publication_config(
                    enabled=True,
                    min_count=min_count,
                    min_share=min_share,
                    min_strong_count=0,
                    min_strength_sum=0.0,
                ),
            }
        )
    for name, min_count, min_share, min_strong_count, min_strength_sum in [
        ("S1_count4_share060_strong1_sum4", 4, 0.60, 1, 4.0),
        ("S2_count5_share060_strong1_sum5", 5, 0.60, 1, 5.0),
        ("S3_count5_share070_strong1_sum5", 5, 0.70, 1, 5.0),
        ("S4_count6_share070_strong1_sum6", 6, 0.70, 1, 6.0),
        ("S5_count6_share070_strong2_sum6", 6, 0.70, 2, 6.0),
        ("S6_count7_share070_strong2_sum7", 7, 0.70, 2, 7.0),
    ]:
        profiles.append(
            {
                "name": name,
                "config": publication_config(
                    enabled=True,
                    min_count=min_count,
                    min_share=min_share,
                    min_strong_count=min_strong_count,
                    min_strength_sum=min_strength_sum,
                ),
            }
        )
    return profiles


def prepare_person_decisions(
    records: List[Dict[str, Any]],
    *,
    use_orcid: bool = True,
    legacy_without_dong: bool = False,
    config: Optional[AblationConfig] = None,
) -> tuple[List[Any], Dict[str, NameDecision], Dict[str, NameDecision]]:
    name_records = make_name_records(records, use_orcid=use_orcid)
    with legacy_pinyin_without_dong(legacy_without_dong):
        set_ablation_config(config or publication_config(enabled=False))
        try:
            local = batch_identify_surname_position_v8(
                name_records,
                source="CROSSREF",
                enable_person_consistency=False,
                enable_pub_consistency=False,
            )
            person = clone_decisions(local)
            person = adjust_by_person(name_records, person, get_config("CROSSREF"))
        finally:
            reset_ablation_config()
    return name_records, local, person


def apply_publication_grid(
    name_records: List[Any],
    person_decisions: Dict[str, NameDecision],
    config: AblationConfig,
) -> tuple[Dict[str, NameDecision], List[Any]]:
    final = clone_decisions(person_decisions)
    set_ablation_config(config)
    try:
        corrections = _publication_candidate_group_corrections(
            name_records,
            final,
            get_config("CROSSREF"),
        )
        for correction in corrections:
            final[correction.record_id] = correction.after
    finally:
        reset_ablation_config()
    return final, corrections


def proxy_metrics(
    records: List[Dict[str, Any]],
    decisions: Dict[str, NameDecision],
    proxy_labels: List[Optional[str]],
) -> Dict[str, Any]:
    proxy_labeled = sum(1 for label in proxy_labels if label)
    proxy_errors = 0
    canonical_errors = set()
    order_counts = Counter(decision.order for decision in decisions.values())
    for idx, label in enumerate(proxy_labels):
        if not label:
            continue
        if decisions[str(idx)].order != label:
            proxy_errors += 1
            canonical_errors.add(
                canonical_publication_id(records[idx].get("doi") or records[idx].get("article_id"))
            )
    canonical_errors.discard("")
    return {
        "proxy_labeled": proxy_labeled,
        "proxy_errors": proxy_errors,
        "proxy_accuracy": (proxy_labeled - proxy_errors) / proxy_labeled if proxy_labeled else 0.0,
        "canonical_publication_proxy_error_groups": len(canonical_errors),
        "unknown_count": order_counts.get("unknown", 0),
        "family_first_count": order_counts.get("family_first", 0),
        "order_counts": dict(order_counts),
    }


def mentor_predictions(
    records: List[Dict[str, Any]],
    decisions: Dict[str, NameDecision],
) -> Dict[tuple, Dict[str, Any]]:
    by_key = {
        (
            (record.get("doi") or record.get("article_id") or "").lower(),
            record.get("firstname") or "",
            record.get("lastname") or "",
        ): decisions[str(idx)]
        for idx, record in enumerate(records)
    }
    output: Dict[tuple, Dict[str, Any]] = {}
    for case_id, (doi, firstname, lastname, gold_order) in enumerate(mentor_challenge_cases(), 1):
        key = (doi.lower(), firstname, lastname)
        decision = by_key.get(key)
        output[key] = {
            "case_id": case_id,
            "doi": doi,
            "canonical_publication_id": canonical_publication_id(doi),
            "firstname": firstname,
            "lastname": lastname,
            "gold_order": gold_order,
            "prediction": decision.order if decision else None,
            "confidence": decision.confidence if decision else None,
            "reason": "; ".join(decision.reason_codes) if decision else "MISSING",
            "correct": bool(decision and decision.order == gold_order),
        }
    return output


def mentor_summary(predictions: Dict[tuple, Dict[str, Any]]) -> Dict[str, Any]:
    total = len(predictions)
    correct = sum(1 for row in predictions.values() if row["correct"])
    return {
        "mentor_total": total,
        "mentor_correct": correct,
        "mentor_errors": total - correct,
    }


def correction_audit_rows(
    records: List[Dict[str, Any]],
    proxy_labels: List[Optional[str]],
    corrections: List[Any],
) -> List[Dict[str, Any]]:
    rows = []
    for correction in corrections:
        idx = int(correction.record_id)
        record = records[idx]
        proxy_label = proxy_labels[idx]
        doi = record.get("doi") or record.get("article_id")
        before_correct = correction.before.order == proxy_label if proxy_label else None
        after_correct = correction.after.order == proxy_label if proxy_label else None
        rows.append(
            {
                "record_id": correction.record_id,
                "doi": doi,
                "canonical_publication_id": canonical_publication_id(doi),
                "firstname": record.get("firstname"),
                "lastname": record.get("lastname"),
                "orcid": record.get("orcid"),
                "proxy_label": proxy_label,
                "is_proxy_labeled": proxy_label is not None,
                "before_proxy_correct": before_correct,
                "after_proxy_correct": after_correct,
                "proxy_error_delta": (
                    int(not after_correct) - int(not before_correct)
                    if proxy_label
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
        )
    return rows


def mentor_case_label(row: Dict[str, Any]) -> str:
    return (
        f"{row['case_id']}:{row['doi']}:{row['firstname']}/{row['lastname']}"
    )


def mentor_cases_fixed_from_baseline(
    baseline: Dict[tuple, Dict[str, Any]],
    current: Dict[tuple, Dict[str, Any]],
) -> List[str]:
    fixed = [
        mentor_case_label(row)
        for key, row in current.items()
        if (not baseline[key]["correct"]) and row["correct"]
    ]
    fixed.sort(key=lambda value: int(value.split(":", 1)[0]))
    return fixed


def mentor_cases_wrong(current: Dict[tuple, Dict[str, Any]]) -> List[str]:
    wrong = [mentor_case_label(row) for row in current.values() if not row["correct"]]
    wrong.sort(key=lambda value: int(value.split(":", 1)[0]))
    return wrong


def canonical_family_rows(
    audit_rows: List[Dict[str, Any]],
    fixed_mentor_cases_by_canonical_id: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in audit_rows:
        cid = row["canonical_publication_id"]
        bucket = grouped.setdefault(
            cid,
            {
                "canonical_publication_id": cid,
                "dois": set(),
                "record_ids": [],
                "publication_change_count": 0,
                "proxy_error_delta_sum": 0,
                "proxy_error_delta_positive_count": 0,
                "fixes_mentor_case": cid in fixed_mentor_cases_by_canonical_id,
                "mentor_cases_fixed": fixed_mentor_cases_by_canonical_id.get(cid, []),
            },
        )
        bucket["dois"].add(row["doi"])
        bucket["record_ids"].append(row["record_id"])
        bucket["publication_change_count"] += 1
        delta = int(row["proxy_error_delta"])
        bucket["proxy_error_delta_sum"] += delta
        if delta > 0:
            bucket["proxy_error_delta_positive_count"] += 1
    rows = []
    for bucket in grouped.values():
        rows.append(
            {
                **bucket,
                "dois": ";".join(sorted(doi for doi in bucket["dois"] if doi)),
                "record_ids": ";".join(str(item) for item in bucket["record_ids"]),
                "mentor_cases_fixed": ";".join(bucket["mentor_cases_fixed"]),
            }
        )
    rows.sort(key=lambda row: (-row["proxy_error_delta_positive_count"], row["canonical_publication_id"]))
    return rows


def run_grid(dataset_path: Path, output_dir: Path) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(dataset_path)
    mentor_records = load_mentor_records()
    proxy_labels = [infer_proxy_order(record) for record in records]

    name_records, local_decisions, person_decisions = prepare_person_decisions(records)
    mentor_name_records, mentor_local, mentor_person = prepare_person_decisions(mentor_records)
    baseline_final = clone_decisions(person_decisions)
    baseline_mentor = mentor_predictions(mentor_records, mentor_person)

    profiles = build_middle_profiles()
    summaries = []
    profile_decisions: Dict[str, Dict[str, NameDecision]] = {
        "A_publication_off": baseline_final,
    }
    profile_mentor: Dict[str, Dict[tuple, Dict[str, Any]]] = {
        "A_publication_off": baseline_mentor,
    }
    audit_by_profile: Dict[str, List[Dict[str, Any]]] = {}

    local_metrics = proxy_metrics(records, local_decisions, proxy_labels)
    person_metrics = proxy_metrics(records, person_decisions, proxy_labels)

    for profile in profiles:
        name = profile["name"]
        config = profile["config"]
        if name == "A_publication_off":
            final_decisions = clone_decisions(person_decisions)
            corrections = []
            mentor_final = clone_decisions(mentor_person)
            mentor_corrections = []
        else:
            final_decisions, corrections = apply_publication_grid(
                name_records,
                person_decisions,
                config,
            )
            mentor_final, mentor_corrections = apply_publication_grid(
                mentor_name_records,
                mentor_person,
                config,
            )
        profile_decisions[name] = final_decisions
        profile_mentor[name] = mentor_predictions(mentor_records, mentor_final)
        final_metrics = proxy_metrics(records, final_decisions, proxy_labels)
        mentor_stats = mentor_summary(profile_mentor[name])
        fixed_mentor_cases = mentor_cases_fixed_from_baseline(baseline_mentor, profile_mentor[name])
        wrong_mentor_cases = mentor_cases_wrong(profile_mentor[name])
        fixed_mentor_cases_by_canonical_id: Dict[str, List[str]] = defaultdict(list)
        for label in fixed_mentor_cases:
            _, doi, _ = label.split(":", 2)
            fixed_mentor_cases_by_canonical_id[canonical_publication_id(doi)].append(label)
        audit_rows = correction_audit_rows(records, proxy_labels, corrections)
        audit_by_profile[name] = audit_rows
        family_rows = canonical_family_rows(audit_rows, fixed_mentor_cases_by_canonical_id)
        profile_dir = output_dir / name
        profile_dir.mkdir(parents=True, exist_ok=True)
        write_csv(profile_dir / "publication_candidate_group_audit.csv", audit_rows)
        write_jsonl(profile_dir / "publication_candidate_group_audit.jsonl", audit_rows)
        write_csv(profile_dir / "canonical_publication_family_audit.csv", family_rows)
        write_jsonl(profile_dir / "canonical_publication_family_audit.jsonl", family_rows)
        write_jsonl(
            profile_dir / "mentor_challenge_errors.jsonl",
            [row for row in profile_mentor[name].values() if not row["correct"]],
        )
        stage_rows = [
            {"stage": "local", **local_metrics},
            {"stage": "after_person", **person_metrics},
            {"stage": "after_publication", **final_metrics},
        ]
        write_csv(profile_dir / "stage_metrics.csv", stage_rows)

        summaries.append(
            {
                "config_name": name,
                "min_count": config.publication_candidate_group_min_count,
                "min_share": config.publication_candidate_group_min_share,
                "min_strong_count": config.publication_candidate_group_min_strong_count,
                "min_strength_sum": config.publication_candidate_group_min_strength_sum,
                "proxy_errors": final_metrics["proxy_errors"],
                "local_proxy_errors": local_metrics["proxy_errors"],
                "after_person_proxy_errors": person_metrics["proxy_errors"],
                "after_publication_proxy_errors": final_metrics["proxy_errors"],
                "publication_proxy_error_delta": final_metrics["proxy_errors"] - person_metrics["proxy_errors"],
                "mentor_correct": mentor_stats["mentor_correct"],
                "mentor_total": mentor_stats["mentor_total"],
                "mentor_errors": mentor_stats["mentor_errors"],
                "mentor_cases_fixed": ";".join(fixed_mentor_cases),
                "mentor_cases_wrong": ";".join(wrong_mentor_cases),
                "publication_change_count": sum(1 for row in audit_rows if not row["suppressed"]),
                "publication_audit_count": len(audit_rows),
                "publication_suppressed_count": sum(1 for row in audit_rows if row["suppressed"]),
                "publication_proxy_error_canonical_groups": len(
                    {
                        row["canonical_publication_id"]
                        for row in audit_rows
                        if int(row["proxy_error_delta"]) > 0 and row["canonical_publication_id"]
                    }
                ),
                "pub_override_count": sum(
                    1 for decision in final_decisions.values()
                    if "PUB_PATTERN_OVERRIDE" in decision.reason_codes
                ),
                "canonical_publication_proxy_error_groups": final_metrics[
                    "canonical_publication_proxy_error_groups"
                ],
                "unknown_count": final_metrics["unknown_count"],
                "family_first_count": final_metrics["family_first_count"],
            }
        )

    attribution_profiles = {
        "A": ("A_publication_off", publication_config(enabled=False), True, False, False),
        "B": (
            "B_publication_current",
            publication_config(enabled=True, min_count=4, min_share=0.40, min_strong_count=0, min_strength_sum=0.0),
            True,
            False,
            True,
        ),
        "D": ("D_strong_on_no_context_publication_off", strong_config(require_cn_context=False), True, False, False),
        "E": ("E_strong_on_doi_context_publication_off", strong_config(require_cn_context=True), True, False, False),
        "G": (
            "G_previous_139_old",
            publication_config(enabled=True, min_count=4, min_share=0.40, min_strong_count=0, min_strength_sum=0.0),
            False,
            True,
            True,
        ),
    }
    attr_predictions: Dict[str, Dict[tuple, Dict[str, Any]]] = {}
    for label, (_, config, use_orcid, legacy_without_dong, enable_pub) in attribution_profiles.items():
        mentor_records_for_profile = make_name_records(mentor_records, use_orcid=use_orcid)
        with legacy_pinyin_without_dong(legacy_without_dong):
            set_ablation_config(config)
            try:
                decisions = batch_identify_surname_position_v8(
                    mentor_records_for_profile,
                    source="CROSSREF",
                    enable_person_consistency=True,
                    enable_pub_consistency=enable_pub,
                )
            finally:
                reset_ablation_config()
        attr_predictions[label] = mentor_predictions(mentor_records, decisions)

    attribution_rows = []
    for case_id, (doi, firstname, lastname, gold_order) in enumerate(mentor_challenge_cases(), 1):
        key = (doi.lower(), firstname, lastname)
        row = {
            "case_id": case_id,
            "doi": doi,
            "canonical_publication_id": canonical_publication_id(doi),
            "firstname": firstname,
            "lastname": lastname,
            "gold_order": gold_order,
        }
        for label in ["A", "B", "D", "E", "G"]:
            pred = attr_predictions[label][key]
            row[f"{label}_prediction"] = pred["prediction"]
            row[f"{label}_confidence"] = pred["confidence"]
            row[f"{label}_reason"] = pred["reason"]
            row[f"{label}_correct"] = pred["correct"]
        row["fixed_by_publication_current"] = (not row["A_correct"]) and row["B_correct"]
        row["fixed_by_strong_rescue"] = (not row["A_correct"]) and (row["D_correct"] or row["E_correct"])
        row["still_wrong_in_all_configs"] = not any(row[f"{label}_correct"] for label in ["A", "B", "D", "E", "G"])
        attribution_rows.append(row)
    write_csv(output_dir / "mentor_case_attribution.csv", attribution_rows)

    fixed_by_publication_canonical: Dict[str, List[str]] = defaultdict(list)
    for row in attribution_rows:
        if row["fixed_by_publication_current"]:
            fixed_by_publication_canonical[row["canonical_publication_id"]].append(
                mentor_case_label(row)
            )
    current_audit = audit_by_profile.get("B_publication_current", [])
    current_family_rows = canonical_family_rows(current_audit, fixed_by_publication_canonical)
    write_csv(output_dir / "publication_current_canonical_family_audit.csv", current_family_rows)
    write_jsonl(output_dir / "publication_current_canonical_family_audit.jsonl", current_family_rows)

    write_csv(output_dir / "publication_grid_metrics.csv", summaries)
    manifest = {
        "dataset_path": str(dataset_path),
        "dataset_sha256": sha256_file(dataset_path),
        "n_records": len(records),
        "n_proxy_labeled": sum(1 for label in proxy_labels if label),
        "profiles": summaries,
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "runs" / "publication_middle_grid_20260515",
    )
    args = parser.parse_args()
    dataset_path = args.dataset or locate_default_dataset()
    manifest = run_grid(dataset_path, args.output)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
