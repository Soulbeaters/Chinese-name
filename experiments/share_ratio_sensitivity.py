# -*- coding: utf-8 -*-
"""
Sensitivity analysis for the share-ratio threshold used in the v8 surname rule.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_v8 import AblationConfig, reset_ablation_config, set_ablation_config
from src.surname_identifier_v8 import NameRecord, batch_identify_surname_position_v8


DEFAULT_DATASET = Path(r"C:\Users\mjx\repo_backups\strategy_30k_eval_20260416\ground_truth_30k_seed42.json")
DEFAULT_BASELINE_THRESHOLD = 1.0


def format_threshold(value: float) -> str:
    return f"{value:.2f}"


def load_dataset(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def infer_proxy_order(record: Dict) -> str:
    lastname = (record.get("lastname") or "").strip()
    original_name = (record.get("original_name") or "").strip()
    return "family_first" if original_name.startswith(lastname) else "given_first"


def to_name_records(records: List[Dict]) -> List[NameRecord]:
    converted = []
    for idx, rec in enumerate(records):
        converted.append(
            NameRecord(
                record_id=str(idx),
                name_raw=rec.get("original_name", ""),
                firstname_raw=rec.get("firstname"),
                lastname_raw=rec.get("lastname"),
                affiliation_raw=rec.get("affiliation"),
                source=rec.get("source", "CROSSREF"),
                person_id=rec.get("person_id"),
                publication_id=rec.get("doi"),
            )
        )
    return converted


def evaluate_predictions(
    records: List[Dict],
    decisions: Dict[str, object],
    subset_ids: set[str] | None = None,
) -> Dict[str, float]:
    correct = 0
    incorrect = 0
    unknown = 0
    total = 0

    for idx, rec in enumerate(records):
        record_id = str(idx)
        if subset_ids is not None and record_id not in subset_ids:
            continue

        if "lastname" not in rec or "firstname" not in rec:
            continue

        total += 1
        gt = infer_proxy_order(rec)
        pred = decisions[record_id].order

        if pred == "unknown":
            unknown += 1
        elif pred == gt:
            correct += 1
        else:
            incorrect += 1

    if total == 0:
        return {
            "n": 0,
            "accuracy": 0.0,
            "unknown_rate": 0.0,
            "error_rate": 0.0,
        }

    return {
        "n": total,
        "accuracy": correct / total,
        "unknown_rate": unknown / total,
        "error_rate": incorrect / total,
    }


def get_frequency_subset_ids(decisions: Dict[str, object]) -> set[str]:
    return {
        rid
        for rid, decision in decisions.items()
        if any(
            code.startswith("CN_SURNAME_DOUBLE_FREQ_") or code == "CN_SURNAME_DOUBLE_DEFAULT_FAM"
            for code in decision.reason_codes
        )
    }


def run_threshold(records: List[Dict], name_records: List[NameRecord], threshold: float) -> Tuple[Dict[str, float], Dict[str, object]]:
    set_ablation_config(
        AblationConfig(
            surname_freq_strategy="share_ratio",
            surname_share_ratio_threshold=threshold,
        )
    )
    try:
        decisions = batch_identify_surname_position_v8(name_records)
        metrics = evaluate_predictions(records, decisions)
        return metrics, decisions
    finally:
        reset_ablation_config()


def choose_best(results: Dict[str, Dict[str, Dict[str, float]]]) -> str:
    ranked = sorted(
        results.items(),
        key=lambda item: (
            -item[1]["frequency_ambiguity"]["accuracy"],
            -item[1]["overall"]["accuracy"],
            item[1]["overall"]["unknown_rate"],
        ),
    )
    return ranked[0][0]


def write_markdown(results: Dict[str, Dict[str, Dict[str, float]]], best_threshold: str, output_path: Path) -> None:
    lines = [
        "# Share-ratio threshold sensitivity",
        "",
        f"Best threshold under the preset ranking rule: **{best_threshold}**",
        "",
        "| Threshold | Overall accuracy | Overall UNKNOWN | Freq-subset n | Freq-subset accuracy |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for threshold, metrics in results.items():
        lines.append(
            "| "
            f"{threshold} | "
            f"{metrics['overall']['accuracy']:.4f} | "
            f"{metrics['overall']['unknown_rate']:.4f} | "
            f"{metrics['frequency_ambiguity']['n']} | "
            f"{metrics['frequency_ambiguity']['accuracy']:.4f} |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run share-ratio threshold sensitivity analysis.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--thresholds", nargs="+", type=float, default=[1.0, 1.5, 2.0])
    parser.add_argument("--output-dir", type=Path, default=Path(r"C:\Users\mjx\repo_backups") / f"share_ratio_sensitivity_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = load_dataset(args.dataset)
    name_records = to_name_records(records)

    baseline_metrics, baseline_decisions = run_threshold(records, name_records, DEFAULT_BASELINE_THRESHOLD)
    frequency_subset_ids = get_frequency_subset_ids(baseline_decisions)

    baseline_key = format_threshold(DEFAULT_BASELINE_THRESHOLD)
    results: Dict[str, Dict[str, Dict[str, float]]] = {
        baseline_key: {
            "overall": baseline_metrics,
            "frequency_ambiguity": evaluate_predictions(records, baseline_decisions, frequency_subset_ids),
        }
    }

    for threshold in args.thresholds:
        key = format_threshold(threshold)
        if key in results:
            continue
        metrics, decisions = run_threshold(records, name_records, threshold)
        results[key] = {
            "overall": metrics,
            "frequency_ambiguity": evaluate_predictions(records, decisions, frequency_subset_ids),
        }

    ordered_results = {key: results[key] for key in sorted(results, key=lambda value: float(value))}
    best_threshold = choose_best(ordered_results)

    (args.output_dir / "share_ratio_sensitivity.json").write_text(
        json.dumps(
            {
                "dataset": str(args.dataset),
                "best_threshold": best_threshold,
                "results": ordered_results,
                "selection_rule": [
                    "frequency_ambiguity.accuracy",
                    "overall.accuracy",
                    "overall.unknown_rate",
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_markdown(ordered_results, best_threshold, args.output_dir / "share_ratio_sensitivity.md")

    print(json.dumps({"best_threshold": best_threshold, "results": ordered_results}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
