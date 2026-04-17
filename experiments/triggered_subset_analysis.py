# -*- coding: utf-8 -*-
"""
触发子集消融分析 / Triggered Subset Ablation Analysis

为每个模块生成触发子集，并在子集上进行消融对比
用于证明每个模块确实生效
Generates triggered subsets for each module and performs ablation comparison

作者: Ma Jiaxin
日期: 2025-12-19
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
from dataclasses import dataclass

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.surname_frequency import (
    get_surname_frequency_rank,
    get_surname_frequency_share,
)
from src.surname_identifier_v8 import NameRecord, preprocess_name
from src.config_v8 import AblationConfig, set_ablation_config, reset_ablation_config
from experiments.event_collection import batch_identify_with_event_tracking
from experiments.performance_metrics import PerformanceMonitor


@dataclass
class SubsetMetrics:
    """子集指标 / Subset metrics"""
    subset_size: int
    accuracy: float
    unknown_rate: float
    error_rate: float
    correct: int
    incorrect: int
    unknown: int


def evaluate_on_subset(
    records: List[NameRecord],
    ground_truth: Dict[str, str],
    config: AblationConfig
) -> SubsetMetrics:
    """
    在子集上评估算法
    Evaluate algorithm on subset

    Args:
        records: 记录列表
        ground_truth: Ground truth字典 {record_id: "family_first"|"given_first"}
        config: 消融配置

    Returns:
        SubsetMetrics对象
    """
    set_ablation_config(config)

    # 批量识别
    decisions, _ = batch_identify_with_event_tracking(
        records,
        enable_person_consistency=config.enable_person_consistency,
        enable_pub_consistency=config.enable_pub_consistency
    )

    # 计算指标
    correct = 0
    incorrect = 0
    unknown = 0

    for rec in records:
        rid = rec.record_id
        if rid not in ground_truth or rid not in decisions:
            continue

        gt = ground_truth[rid]
        pred = decisions[rid].order

        if pred == "unknown":
            unknown += 1
        elif pred == gt:
            correct += 1
        else:
            incorrect += 1

    total = correct + incorrect + unknown
    if total == 0:
        return SubsetMetrics(0, 0.0, 0.0, 0.0, 0, 0, 0)

    accuracy = correct / total if total > 0 else 0.0
    unknown_rate = unknown / total if total > 0 else 0.0
    error_rate = incorrect / total if total > 0 else 0.0

    reset_ablation_config()

    return SubsetMetrics(
        subset_size=total,
        accuracy=accuracy,
        unknown_rate=unknown_rate,
        error_rate=error_rate,
        correct=correct,
        incorrect=incorrect,
        unknown=unknown
    )


def _is_frequency_subset_decision(reason_codes: List[str]) -> bool:
    """Baseline frequency-ambiguity subset used for rank/share comparison."""
    return any(
        code.startswith("CN_SURNAME_DOUBLE_FREQ_") or code == "CN_SURNAME_DOUBLE_DEFAULT_FAM"
        for code in reason_codes
    )


def _missing_frequency_info_rate(records: List[NameRecord], strategy: str) -> float:
    """
    Estimate how often a double-surname record lacks usable frequency evidence.

    - rank_gap: missing if either candidate surname falls back to rank 999
    - share_ratio: missing if either candidate surname has zero aggregated share
    """
    missing = 0
    eligible = 0

    for rec in records:
        parsed = preprocess_name(rec.name_raw)
        if parsed.first_idx < 0 or parsed.last_idx < 0:
            continue

        first_token = parsed.tokens[parsed.first_idx].ascii
        last_token = parsed.tokens[parsed.last_idx].ascii
        eligible += 1

        if strategy == "share_ratio":
            first_value = get_surname_frequency_share(first_token)
            last_value = get_surname_frequency_share(last_token)
            if first_value == 0.0 or last_value == 0.0:
                missing += 1
        else:
            first_value = get_surname_frequency_rank(first_token)
            last_value = get_surname_frequency_rank(last_token)
            if first_value == 999 or last_value == 999:
                missing += 1

    return missing / eligible if eligible else 0.0


def generate_triggered_subsets(
    all_records: List[NameRecord],
    ground_truth: Dict[str, str],
    baseline_config: AblationConfig
) -> Dict[str, List[str]]:
    """
    为每个模块生成触发子集
    Generate triggered subsets for each module

    Args:
        all_records: 所有记录
        ground_truth: Ground truth
        baseline_config: Baseline配置

    Returns:
        Dict[module_name, List[record_id]]
    """
    print("Generating triggered subsets...")

    # 使用baseline配置运行一次，收集触发信息
    set_ablation_config(baseline_config)
    decisions, aggregator = batch_identify_with_event_tracking(all_records)
    reset_ablation_config()

    frequency_subset_ids = [
        rid for rid, decision in decisions.items()
        if _is_frequency_subset_decision(decision.reason_codes)
    ]

    # 获取各模块触发的record_id
    subsets = {
        "source_prior": aggregator.get_triggered_record_ids("source_prior_applied"),
        "western_exclusion": aggregator.get_triggered_record_ids("western_exclusion_fired"),
        "batch_consistency": aggregator.get_triggered_record_ids("batch_consistency_override"),
        "person_consistency": aggregator.get_triggered_record_ids("person_consistency_override"),
        "pub_consistency": aggregator.get_triggered_record_ids("pub_consistency_override"),
        "frequency_ambiguity": frequency_subset_ids,
    }

    print(f"Triggered subset sizes:")
    for module, ids in subsets.items():
        print(f"  {module}: {len(ids)}")

    return subsets


def run_triggered_subset_ablation(
    all_records: List[NameRecord],
    ground_truth: Dict[str, str],
    ablation_configs: Dict[str, AblationConfig],
    output_dir: str
):
    """
    运行触发子集消融分析
    Run triggered subset ablation analysis

    Args:
        all_records: 所有记录
        ground_truth: Ground truth
        ablation_configs: 消融配置字典
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 创建record字典
    record_dict = {rec.record_id: rec for rec in all_records}

    # Baseline配置
    baseline_config = ablation_configs.get("baseline", AblationConfig())

    # 1. 生成触发子集
    triggered_subsets = generate_triggered_subsets(all_records, ground_truth, baseline_config)

    # 保存触发子集的record_id
    subset_ids_dir = output_path / "triggered_subset_ids"
    subset_ids_dir.mkdir(exist_ok=True)

    for module, ids in triggered_subsets.items():
        with open(subset_ids_dir / f"{module}_ids.txt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(ids))

    # 2. 定义模块到配置的映射（与ablation.yaml中的键一致）
    module_to_ablation = {
        "source_prior": "ablation_no_source_prior",
        "western_exclusion": "ablation_no_western_exclusion",
        "batch_consistency": "ablation_no_batch_consistency",
        "person_consistency": "ablation_no_person_consistency",
        "pub_consistency": "ablation_no_pub_consistency",
        "frequency_ambiguity": "ablation_share_ratio",
    }

    # 3. 对每个模块运行子集对比
    results = {}

    for module, ablation_name in module_to_ablation.items():
        print(f"\nAnalyzing module: {module}")

        subset_ids = triggered_subsets.get(module, [])
        if len(subset_ids) == 0:
            print(f"  WARNING: {module} triggered 0 records, skipping...")
            results[module] = {
                "subset_size": 0,
                "baseline": None,
                "ablation": None,
                "delta_accuracy": 0.0,
                "delta_unknown": 0.0
            }
            continue

        # 获取子集记录
        subset_records = [record_dict[rid] for rid in subset_ids if rid in record_dict]

        print(f"  Subset size: {len(subset_records)}")

        # Baseline
        print(f"  Running baseline on subset...")
        baseline_metrics = evaluate_on_subset(subset_records, ground_truth, baseline_config)

        # Ablation
        ablation_config = ablation_configs.get(ablation_name)
        if ablation_config is None:
            print(f"  WARNING: Ablation config {ablation_name} not found")
            continue

        print(f"  Running ablation ({ablation_name}) on subset...")
        ablation_metrics = evaluate_on_subset(subset_records, ground_truth, ablation_config)

        # 对比
        delta_acc = ablation_metrics.accuracy - baseline_metrics.accuracy
        delta_unk = ablation_metrics.unknown_rate - baseline_metrics.unknown_rate

        results[module] = {
            "subset_size": len(subset_records),
            "baseline": {
                "accuracy": baseline_metrics.accuracy,
                "unknown_rate": baseline_metrics.unknown_rate,
                "error_rate": baseline_metrics.error_rate,
                "correct": baseline_metrics.correct,
                "incorrect": baseline_metrics.incorrect,
                "unknown": baseline_metrics.unknown
            },
            "ablation": {
                "accuracy": ablation_metrics.accuracy,
                "unknown_rate": ablation_metrics.unknown_rate,
                "error_rate": ablation_metrics.error_rate,
                "correct": ablation_metrics.correct,
                "incorrect": ablation_metrics.incorrect,
                "unknown": ablation_metrics.unknown
            },
            "delta_accuracy": delta_acc,
            "delta_unknown": delta_unk,
            "ablation_config_name": ablation_name
        }

        if module == "frequency_ambiguity":
            results[module]["baseline"]["missing_frequency_info_rate"] = _missing_frequency_info_rate(
                subset_records,
                "rank_gap",
            )
            results[module]["ablation"]["missing_frequency_info_rate"] = _missing_frequency_info_rate(
                subset_records,
                "share_ratio",
            )
            results[module]["delta_missing_frequency_info"] = (
                results[module]["ablation"]["missing_frequency_info_rate"]
                - results[module]["baseline"]["missing_frequency_info_rate"]
            )

        print(f"  Baseline: Acc={baseline_metrics.accuracy:.4f}, Unk={baseline_metrics.unknown_rate:.4f}")
        print(f"  Ablation: Acc={ablation_metrics.accuracy:.4f}, Unk={ablation_metrics.unknown_rate:.4f}")
        print(f"  Delta:    Acc={delta_acc:+.4f}, Unk={delta_unk:+.4f}")
        if module == "frequency_ambiguity":
            baseline_missing = results[module]["baseline"]["missing_frequency_info_rate"]
            ablation_missing = results[module]["ablation"]["missing_frequency_info_rate"]
            print(
                "  Missing freq info: "
                f"{baseline_missing:.4f} -> {ablation_missing:.4f} "
                f"({results[module]['delta_missing_frequency_info']:+.4f})"
            )

    # 4. 保存结果
    with open(output_path / "ablation_triggered_subsets.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 5. 生成Markdown报告
    generate_triggered_subset_md(results, output_path / "ablation_triggered_subsets.md")

    # 6. 生成LaTeX表格
    generate_triggered_subset_tex(results, output_path / "ablation_triggered_subsets.tex")

    print(f"\nTriggered subset analysis complete. Results saved to {output_dir}")


def generate_triggered_subset_md(results: Dict, filepath: str):
    """生成Markdown报告"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# 触发子集消融分析 / Triggered Subset Ablation Analysis\n\n")
        f.write("## 概述 / Overview\n\n")
        f.write("本分析仅在**每个模块触发的子集**上进行对比，避免全局指标掩盖局部效应。\n\n")

        for module, data in results.items():
            f.write(f"## {module.replace('_', ' ').title()}\n\n")

            subset_size = data.get("subset_size", 0)
            if subset_size == 0:
                f.write("⚠️ **该模块在数据集上触发次数为0，无法进行子集分析。**\n\n")
                continue

            baseline = data.get("baseline", {})
            ablation = data.get("ablation", {})
            delta_acc = data.get("delta_accuracy", 0.0)
            delta_unk = data.get("delta_unknown", 0.0)

            f.write(f"**触发子集规模**: {subset_size:,} 条记录\n\n")
            f.write("### 指标对比\n\n")
            f.write("| 配置 | 准确率 | Unknown率 | Error率 | 正确 | 错误 | Unknown |\n")
            f.write("|------|--------|-----------|---------|------|------|----------|\n")
            f.write(f"| Baseline | {baseline.get('accuracy', 0.0)*100:.2f}% | "
                    f"{baseline.get('unknown_rate', 0.0)*100:.2f}% | "
                    f"{baseline.get('error_rate', 0.0)*100:.2f}% | "
                    f"{baseline.get('correct', 0)} | "
                    f"{baseline.get('incorrect', 0)} | "
                    f"{baseline.get('unknown', 0)} |\n")
            f.write(f"| Ablation ({data.get('ablation_config_name', 'N/A')}) | "
                    f"{ablation.get('accuracy', 0.0)*100:.2f}% | "
                    f"{ablation.get('unknown_rate', 0.0)*100:.2f}% | "
                    f"{ablation.get('error_rate', 0.0)*100:.2f}% | "
                    f"{ablation.get('correct', 0)} | "
                    f"{ablation.get('incorrect', 0)} | "
                    f"{ablation.get('unknown', 0)} |\n")
            f.write(f"| **Δ (Ablation - Baseline)** | **{delta_acc*100:+.2f}%** | "
                    f"**{delta_unk*100:+.2f}%** | - | - | - | - |\n\n")

            # 结论
            f.write("### 结论 / Conclusion\n\n")
            if abs(delta_acc) < 0.001 and abs(delta_unk) < 0.001:
                f.write("在触发子集上，禁用该模块对准确率和Unknown率无显著影响（Δ < 0.1%）。\n")
                f.write("这可能意味着：\n")
                f.write("1. 该模块的效果被其他模块补偿\n")
                f.write("2. 触发条件与实际影响不完全一致\n")
                f.write("3. 子集规模较小，统计噪声较大\n\n")
            elif delta_acc < -0.01:
                f.write(f"✅ **禁用该模块导致准确率下降{-delta_acc*100:.2f}%**，证明该模块对准确率有正向贡献。\n\n")
            elif delta_unk > 0.01:
                f.write(f"✅ **禁用该模块导致Unknown率上升{delta_unk*100:.2f}%**，证明该模块有助于消除uncertainty。\n\n")
            else:
                f.write("⚠️ 禁用该模块后，指标变化不显著或与预期相反，需进一步分析。\n\n")


def generate_triggered_subset_tex(results: Dict, filepath: str):
    """生成LaTeX表格"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("% 触发子集消融分析表格 / Triggered Subset Ablation Analysis Table\n")
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write("\\caption{Triggered Subset Ablation Analysis Results}\n")
        f.write("\\label{tab:triggered_ablation}\n")
        f.write("\\begin{tabular}{lrccc}\n")
        f.write("\\hline\n")
        f.write("Module & Subset Size & Baseline Acc (\\%) & Ablation Acc (\\%) & $\\Delta$ Acc (\\%) \\\\\n")
        f.write("\\hline\n")

        for module, data in results.items():
            module_label = module.replace('_', ' ').title()
            subset_size = data.get("subset_size", 0)
            if subset_size == 0:
                f.write(f"{module_label} & 0 & - & - & - \\\\\n")
                continue

            baseline_acc = data.get("baseline", {}).get("accuracy", 0.0) * 100
            ablation_acc = data.get("ablation", {}).get("accuracy", 0.0) * 100
            delta_acc = data.get("delta_accuracy", 0.0) * 100

            f.write(f"{module_label} & {subset_size:,} & {baseline_acc:.2f} & "
                    f"{ablation_acc:.2f} & {delta_acc:+.2f} \\\\\n")

        f.write("\\hline\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
