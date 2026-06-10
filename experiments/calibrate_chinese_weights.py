# -*- coding: utf-8 -*-
"""
Calibrate Chinese-mode scoring weights for v8.0 with a reproducible search loop.

This script does not change the production defaults. It temporarily overrides
selected weights/profile thresholds, evaluates them on a benchmark-compatible
labeling rule, and reports the best configuration under an explicit objective.

Current default label mode matches the existing benchmark pipeline:
    family_first iff original_name.startswith(lastname)
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import src.config_v8 as config_v8
from src.config_v8 import AblationConfig, get_config, reset_ablation_config, set_ablation_config
from src.surname_identifier_v8 import (
    NameRecord,
    batch_identify_surname_position_v8,
    detect_mode,
    preprocess_name,
)


DEFAULT_DATASET = Path(r"C:\Users\mjx\repo_backups\strategy_30k_eval_20260416\ground_truth_30k_seed42.json")
DEFAULT_OUTPUT_ROOT = Path(r"C:\Users\mjx\repo_backups")
VALID_LABELS = {"family_first", "given_first"}


def parse_float_list(raw: str) -> List[float]:
    return [float(part.strip()) for part in raw.split(",") if part.strip()]


def load_records(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def infer_benchmark_label(record: Dict) -> str | None:
    lastname = (record.get("lastname") or "").strip()
    original_name = (record.get("original_name") or "").strip()
    if not lastname or not original_name:
        return None
    return "family_first" if original_name.startswith(lastname) else "given_first"


def infer_label(record: Dict, label_mode: str) -> str | None:
    if label_mode == "benchmark_compatible":
        return infer_benchmark_label(record)

    if label_mode == "true_position":
        label = record.get("true_position")
        if label in VALID_LABELS:
            return label
        return None

    raise ValueError(f"Unsupported label_mode: {label_mode}")


def to_name_records(records: List[Dict], profile: str) -> List[NameRecord]:
    converted: List[NameRecord] = []
    for idx, rec in enumerate(records):
        converted.append(
            NameRecord(
                record_id=str(idx),
                name_raw=rec.get("original_name", ""),
                firstname_raw=rec.get("firstname"),
                lastname_raw=rec.get("lastname"),
                affiliation_raw=rec.get("affiliation"),
                source=profile,
                person_id=rec.get("person_id") or rec.get("orcid"),
                publication_id=rec.get("doi") or rec.get("article_id"),
            )
        )
    return converted


def get_profile_config_object(profile: str):
    normalized = (profile or "DEFAULT").strip()
    if normalized in config_v8.SOURCE_CONFIGS:
        return config_v8.SOURCE_CONFIGS[normalized]
    upper = normalized.upper()
    if upper in config_v8.SOURCE_CONFIGS:
        return config_v8.SOURCE_CONFIGS[upper]
    if normalized.lower() == "default":
        return config_v8.DEFAULT_CONFIG
    return config_v8.DEFAULT_CONFIG


@contextmanager
def temporary_calibration(
    profile: str,
    freq_weight: float,
    single_weight: float,
    affiliation_weight: float,
    threshold_cn_unknown: float,
    use_batch_consistency: bool,
):
    old_weights = {
        "CN_SURNAME_DOUBLE_FREQ": config_v8.CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"],
        "FIRST_SINGLE_SYLLABLE": config_v8.CHINESE_FEATURE_WEIGHTS["FIRST_SINGLE_SYLLABLE"],
        "LAST_SINGLE_SYLLABLE": config_v8.CHINESE_FEATURE_WEIGHTS["LAST_SINGLE_SYLLABLE"],
        "CN_AFFILIATION": config_v8.CHINESE_FEATURE_WEIGHTS["CN_AFFILIATION"],
    }
    cfg_obj = get_profile_config_object(profile)
    old_threshold = cfg_obj.threshold_cn_unknown
    old_ablation = config_v8.get_ablation_config()

    config_v8.CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"] = freq_weight
    config_v8.CHINESE_FEATURE_WEIGHTS["FIRST_SINGLE_SYLLABLE"] = single_weight
    config_v8.CHINESE_FEATURE_WEIGHTS["LAST_SINGLE_SYLLABLE"] = single_weight
    config_v8.CHINESE_FEATURE_WEIGHTS["CN_AFFILIATION"] = affiliation_weight
    cfg_obj.threshold_cn_unknown = threshold_cn_unknown

    set_ablation_config(
        AblationConfig(
            disable_source_prior=old_ablation.disable_source_prior,
            disable_western_exclusion=old_ablation.disable_western_exclusion,
            disable_batch_consistency=not use_batch_consistency,
            surname_freq_strategy=old_ablation.surname_freq_strategy,
            surname_share_ratio_threshold=old_ablation.surname_share_ratio_threshold,
            enable_person_consistency=use_batch_consistency and old_ablation.enable_person_consistency,
            enable_pub_consistency=use_batch_consistency and old_ablation.enable_pub_consistency,
        )
    )

    try:
        yield
    finally:
        for key, value in old_weights.items():
            config_v8.CHINESE_FEATURE_WEIGHTS[key] = value
        cfg_obj.threshold_cn_unknown = old_threshold
        set_ablation_config(old_ablation)


def build_subset_indices(records: List[Dict], profile: str, label_mode: str, subset_mode: str) -> List[int]:
    cfg = get_config(profile)
    subset: List[int] = []
    for idx, rec in enumerate(records):
        if infer_label(rec, label_mode) not in VALID_LABELS:
            continue
        if subset_mode == "all_labeled":
            subset.append(idx)
            continue
        nr = NameRecord(
            record_id=str(idx),
            name_raw=rec.get("original_name", ""),
            firstname_raw=rec.get("firstname"),
            lastname_raw=rec.get("lastname"),
            affiliation_raw=rec.get("affiliation"),
            source=profile,
        )
        parsed = preprocess_name(nr.name_raw)
        mode = detect_mode(nr, parsed, cfg)
        if subset_mode == "chinese_mode" and mode == "CHINESE":
            subset.append(idx)
        elif subset_mode == "non_western" and mode in {"CHINESE", "MIXED"}:
            subset.append(idx)
    return subset


def stratified_split(records: List[Dict], label_mode: str, seed: int, test_ratio: float) -> Tuple[List[Dict], List[Dict]]:
    grouped: Dict[str, List[Dict]] = {"family_first": [], "given_first": []}
    unlabeled: List[Dict] = []
    for rec in records:
        label = infer_label(rec, label_mode)
        if label in VALID_LABELS:
            grouped[label].append(rec)
        else:
            unlabeled.append(rec)

    rng = random.Random(seed)
    train: List[Dict] = []
    test: List[Dict] = []

    for label, bucket in grouped.items():
        rng.shuffle(bucket)
        cut = int(round(len(bucket) * (1.0 - test_ratio)))
        cut = max(1, min(len(bucket) - 1, cut)) if len(bucket) > 1 else len(bucket)
        train.extend(bucket[:cut])
        test.extend(bucket[cut:])

    rng.shuffle(unlabeled)
    cut_unlabeled = int(round(len(unlabeled) * (1.0 - test_ratio)))
    train.extend(unlabeled[:cut_unlabeled])
    test.extend(unlabeled[cut_unlabeled:])

    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


def compute_metrics(records: List[Dict], decisions: Dict[str, object], subset_indices: Iterable[int], label_mode: str) -> Dict[str, float]:
    idx_set = set(subset_indices)
    counts = {
        "n": 0,
        "correct": 0,
        "unknown": 0,
        "tp_ff": 0,
        "tp_gf": 0,
        "true_ff": 0,
        "true_gf": 0,
    }

    for idx in idx_set:
        if idx >= len(records):
            continue
        label = infer_label(records[idx], label_mode)
        if label not in VALID_LABELS:
            continue
        counts["n"] += 1
        if label == "family_first":
            counts["true_ff"] += 1
        else:
            counts["true_gf"] += 1

        pred = decisions[str(idx)].order
        if pred == "unknown":
            counts["unknown"] += 1
            continue
        if pred == label:
            counts["correct"] += 1
            if label == "family_first":
                counts["tp_ff"] += 1
            else:
                counts["tp_gf"] += 1

    n = counts["n"]
    accuracy = counts["correct"] / n if n else 0.0
    unknown_rate = counts["unknown"] / n if n else 0.0
    error_rate = 1.0 - accuracy - unknown_rate if n else 0.0
    recall_ff = counts["tp_ff"] / counts["true_ff"] if counts["true_ff"] else 0.0
    recall_gf = counts["tp_gf"] / counts["true_gf"] if counts["true_gf"] else 0.0
    balanced_accuracy = (recall_ff + recall_gf) / 2.0 if counts["true_ff"] and counts["true_gf"] else 0.0

    return {
        **counts,
        "accuracy": accuracy,
        "unknown_rate": unknown_rate,
        "error_rate": error_rate,
        "recall_family_first": recall_ff,
        "recall_given_first": recall_gf,
        "balanced_accuracy": balanced_accuracy,
    }


def evaluate_candidate(
    records: List[Dict],
    name_records: List[NameRecord],
    profile: str,
    label_mode: str,
    search_subset_indices: List[int],
    params: Dict[str, float],
    use_batch_consistency: bool,
) -> Dict[str, Dict[str, float]]:
    with temporary_calibration(
        profile=profile,
        freq_weight=params["freq_weight"],
        single_weight=params["single_weight"],
        affiliation_weight=params["affiliation_weight"],
        threshold_cn_unknown=params["threshold_cn_unknown"],
        use_batch_consistency=use_batch_consistency,
    ):
        decisions = batch_identify_surname_position_v8(name_records, source=profile)

    all_indices = list(range(len(records)))
    return {
        "overall": compute_metrics(records, decisions, all_indices, label_mode),
        "search_subset": compute_metrics(records, decisions, search_subset_indices, label_mode),
    }


def rank_tuple(metrics: Dict[str, Dict[str, float]]) -> Tuple[float, float, float, float]:
    subset = metrics["search_subset"]
    overall = metrics["overall"]
    return (
        subset["balanced_accuracy"],
        subset["accuracy"],
        overall["accuracy"],
        -subset["unknown_rate"],
    )


def coordinate_search(
    records: List[Dict],
    name_records: List[NameRecord],
    profile: str,
    label_mode: str,
    search_subset_indices: List[int],
    grids: Dict[str, List[float]],
    start_params: Dict[str, float],
    max_rounds: int,
    use_batch_consistency: bool,
) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]], List[Dict]]:
    current = dict(start_params)
    best_metrics = evaluate_candidate(
        records, name_records, profile, label_mode, search_subset_indices, current, use_batch_consistency
    )
    history: List[Dict] = [{
        "stage": "baseline",
        "params": dict(current),
        "metrics": best_metrics,
        "rank": rank_tuple(best_metrics),
    }]

    for round_idx in range(max_rounds):
        changed = False
        for param_name, values in grids.items():
            local_best_value = current[param_name]
            local_best_metrics = best_metrics
            local_best_rank = rank_tuple(best_metrics)

            for value in values:
                candidate = dict(current)
                candidate[param_name] = value
                metrics = evaluate_candidate(
                    records,
                    name_records,
                    profile,
                    label_mode,
                    search_subset_indices,
                    candidate,
                    use_batch_consistency,
                )
                rank = rank_tuple(metrics)
                history.append({
                    "stage": f"round_{round_idx + 1}",
                    "param": param_name,
                    "trial_value": value,
                    "params": candidate,
                    "metrics": metrics,
                    "rank": rank,
                })
                if rank > local_best_rank:
                    local_best_value = value
                    local_best_metrics = metrics
                    local_best_rank = rank

            if local_best_value != current[param_name]:
                current[param_name] = local_best_value
                best_metrics = local_best_metrics
                changed = True

        if not changed:
            break

    return current, best_metrics, history


def write_report(
    output_dir: Path,
    dataset: Path,
    profile: str,
    label_mode: str,
    subset_mode: str,
    search_use_batch_consistency: bool,
    train_size: int,
    test_size: int,
    train_subset_size: int,
    test_subset_size: int,
    baseline_params: Dict[str, float],
    best_params: Dict[str, float],
    train_baseline: Dict[str, Dict[str, float]],
    train_best: Dict[str, Dict[str, float]],
    test_baseline: Dict[str, Dict[str, float]],
    test_best_isolated: Dict[str, Dict[str, float]],
    test_best_full: Dict[str, Dict[str, float]],
    history: List[Dict],
) -> None:
    payload = {
        "dataset": str(dataset),
        "profile": profile,
        "label_mode": label_mode,
        "subset_mode": subset_mode,
        "search_use_batch_consistency": search_use_batch_consistency,
        "split": {
            "train_size": train_size,
            "test_size": test_size,
            "train_subset_size": train_subset_size,
            "test_subset_size": test_subset_size,
        },
        "baseline_params": baseline_params,
        "best_params": best_params,
        "train_baseline": train_baseline,
        "train_best": train_best,
        "test_baseline": test_baseline,
        "test_best_isolated": test_best_isolated,
        "test_best_full": test_best_full,
        "history": history,
    }
    (output_dir / "calibration_results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    subset_name = "Chinese-mode subset" if subset_mode == "chinese_mode" else subset_mode
    lines = [
        "# Chinese-weight calibration report",
        "",
        f"- Dataset: `{dataset}`",
        f"- Profile: `{profile}`",
        f"- Label mode: `{label_mode}`",
        f"- Search objective subset: `{subset_name}`",
        f"- Search with batch consistency: `{search_use_batch_consistency}`",
        "",
        "## Best parameters",
        "",
        f"- `CN_SURNAME_DOUBLE_FREQ`: **{best_params['freq_weight']:.3f}**",
        f"- `FIRST/LAST_SINGLE_SYLLABLE`: **{best_params['single_weight']:.3f}**",
        f"- `CN_AFFILIATION`: **{best_params['affiliation_weight']:.3f}**",
        f"- `threshold_cn_unknown`: **{best_params['threshold_cn_unknown']:.3f}**",
        "",
        "## Test comparison",
        "",
        "| Setting | Search-subset balanced acc. | Search-subset acc. | Overall acc. | Overall UNKNOWN |",
        "| --- | ---: | ---: | ---: | ---: |",
        (
            f"| Baseline | {test_baseline['search_subset']['balanced_accuracy']:.4f} | "
            f"{test_baseline['search_subset']['accuracy']:.4f} | "
            f"{test_baseline['overall']['accuracy']:.4f} | "
            f"{test_baseline['overall']['unknown_rate']:.4f} |"
        ),
        (
            f"| Best (isolated search setting) | {test_best_isolated['search_subset']['balanced_accuracy']:.4f} | "
            f"{test_best_isolated['search_subset']['accuracy']:.4f} | "
            f"{test_best_isolated['overall']['accuracy']:.4f} | "
            f"{test_best_isolated['overall']['unknown_rate']:.4f} |"
        ),
        (
            f"| Best (full system validation) | {test_best_full['search_subset']['balanced_accuracy']:.4f} | "
            f"{test_best_full['search_subset']['accuracy']:.4f} | "
            f"{test_best_full['overall']['accuracy']:.4f} | "
            f"{test_best_full['overall']['unknown_rate']:.4f} |"
        ),
        "",
        "## Interpretation",
        "",
        "- The search objective is explicit: maximize balanced accuracy on the chosen subset, then subset accuracy, then overall accuracy, and finally prefer lower UNKNOWN on the subset.",
        "- This is calibration against the current benchmark-compatible label rule, not a universal theoretical optimum.",
        "- If you need dissertation-level formalism, the next step is to pair this empirical calibration with a probabilistic log-odds derivation and a cleaner gold label source.",
        "",
    ]
    (output_dir / "calibration_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate Chinese-mode scoring weights.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--profile", type=str, default="CROSSREF")
    parser.add_argument(
        "--label-mode",
        choices=["benchmark_compatible", "true_position"],
        default="benchmark_compatible",
        help="benchmark_compatible matches the current run_bench rule",
    )
    parser.add_argument(
        "--subset-mode",
        choices=["chinese_mode", "non_western", "all_labeled"],
        default="chinese_mode",
    )
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-rounds", type=int, default=2)
    parser.add_argument("--freq-grid", type=str, default="1.0,1.2,1.5,1.8,2.0")
    parser.add_argument("--single-grid", type=str, default="0.0,0.2,0.4,0.6")
    parser.add_argument("--affil-grid", type=str, default="0.0,0.2,0.5,0.8")
    parser.add_argument("--threshold-grid", type=str, default="0.2,0.3,0.4,0.5")
    parser.add_argument(
        "--search-use-batch-consistency",
        action="store_true",
        help="By default the search isolates local scoring by disabling batch consistency.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    output_dir = args.output_dir or (
        DEFAULT_OUTPUT_ROOT / f"weight_calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(args.dataset)
    train_records, test_records = stratified_split(records, args.label_mode, args.seed, args.test_ratio)
    train_name_records = to_name_records(train_records, args.profile)
    test_name_records = to_name_records(test_records, args.profile)

    train_subset_indices = build_subset_indices(train_records, args.profile, args.label_mode, args.subset_mode)
    test_subset_indices = build_subset_indices(test_records, args.profile, args.label_mode, args.subset_mode)

    baseline_params = {
        "freq_weight": config_v8.CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"],
        "single_weight": config_v8.CHINESE_FEATURE_WEIGHTS["FIRST_SINGLE_SYLLABLE"],
        "affiliation_weight": config_v8.CHINESE_FEATURE_WEIGHTS["CN_AFFILIATION"],
        "threshold_cn_unknown": get_profile_config_object(args.profile).threshold_cn_unknown,
    }

    grids = {
        "freq_weight": parse_float_list(args.freq_grid),
        "single_weight": parse_float_list(args.single_grid),
        "affiliation_weight": parse_float_list(args.affil_grid),
        "threshold_cn_unknown": parse_float_list(args.threshold_grid),
    }

    train_baseline = evaluate_candidate(
        train_records,
        train_name_records,
        args.profile,
        args.label_mode,
        train_subset_indices,
        baseline_params,
        use_batch_consistency=args.search_use_batch_consistency,
    )

    best_params, train_best, history = coordinate_search(
        train_records,
        train_name_records,
        args.profile,
        args.label_mode,
        train_subset_indices,
        grids,
        baseline_params,
        args.max_rounds,
        use_batch_consistency=args.search_use_batch_consistency,
    )

    test_baseline = evaluate_candidate(
        test_records,
        test_name_records,
        args.profile,
        args.label_mode,
        test_subset_indices,
        baseline_params,
        use_batch_consistency=args.search_use_batch_consistency,
    )
    test_best_isolated = evaluate_candidate(
        test_records,
        test_name_records,
        args.profile,
        args.label_mode,
        test_subset_indices,
        best_params,
        use_batch_consistency=args.search_use_batch_consistency,
    )
    test_best_full = evaluate_candidate(
        test_records,
        test_name_records,
        args.profile,
        args.label_mode,
        test_subset_indices,
        best_params,
        use_batch_consistency=True,
    )

    write_report(
        output_dir=output_dir,
        dataset=args.dataset,
        profile=args.profile,
        label_mode=args.label_mode,
        subset_mode=args.subset_mode,
        search_use_batch_consistency=args.search_use_batch_consistency,
        train_size=len(train_records),
        test_size=len(test_records),
        train_subset_size=len(train_subset_indices),
        test_subset_size=len(test_subset_indices),
        baseline_params=baseline_params,
        best_params=best_params,
        train_baseline=train_baseline,
        train_best=train_best,
        test_baseline=test_baseline,
        test_best_isolated=test_best_isolated,
        test_best_full=test_best_full,
        history=history,
    )

    summary = {
        "output_dir": str(output_dir),
        "baseline_params": baseline_params,
        "best_params": best_params,
        "train_best_rank": rank_tuple(train_best),
        "test_baseline": {
            "subset_balanced_accuracy": test_baseline["search_subset"]["balanced_accuracy"],
            "subset_accuracy": test_baseline["search_subset"]["accuracy"],
            "overall_accuracy": test_baseline["overall"]["accuracy"],
            "overall_unknown_rate": test_baseline["overall"]["unknown_rate"],
        },
        "test_best_full": {
            "subset_balanced_accuracy": test_best_full["search_subset"]["balanced_accuracy"],
            "subset_accuracy": test_best_full["search_subset"]["accuracy"],
            "overall_accuracy": test_best_full["overall"]["accuracy"],
            "overall_unknown_rate": test_best_full["overall"]["unknown_rate"],
        },
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
