# -*- coding: utf-8 -*-
"""
消融Sanity Check样本生成 / Ablation Sanity Check Sample Generation

为每个模块生成并排对比样本，证明消融开关确实生效
Generates side-by-side comparison samples for each module to prove ablation switches work

作者: Ma Jiaxin
日期: 2025-12-19
"""

import sys
import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.surname_identifier_v8 import NameRecord
from src.config_v8 import AblationConfig, set_ablation_config, reset_ablation_config
from experiments.event_collection import batch_identify_with_event_tracking


@dataclass
class SanitySample:
    """Sanity check样本"""
    record_id: str
    name_raw: str
    affiliation: str = ""
    ground_truth: str = ""  # family_first | given_first

    # Baseline结果
    baseline_order: str = ""
    baseline_confidence: float = 0.0
    baseline_reasons: str = ""
    baseline_margin: float = 0.0

    # Ablation结果
    ablation_order: str = ""
    ablation_confidence: float = 0.0
    ablation_reasons: str = ""
    ablation_margin: float = 0.0

    # 差异标记
    order_changed: bool = False
    module_name: str = ""


def select_samples_for_module(
    all_records: List[NameRecord],
    ground_truth: Dict[str, str],
    triggered_ids: List[str],
    module_name: str,
    baseline_aggregator,
    n_samples: int = 30
) -> Tuple[List[NameRecord], Dict[str, str]]:
    """
    为某个模块选择样本 (智能采样)
    Select samples for a module (smart sampling)

    优先级 / Priority:
    1. Fired + Margin Changed: 模块触发且分数差值发生变化
    2. Effective: 模块改变了最终order (order flip或unknown→known)
    3. Fired only: 模块触发但未改变结果
    4. Challenge set fallback: 如果上述样本不足,使用挑战集

    Args:
        all_records: 所有记录
        ground_truth: Ground truth
        triggered_ids: 触发该模块的record_id列表
        module_name: 模块名
        baseline_aggregator: Baseline事件聚合器 (用于判断fired/effective)
        n_samples: 目标样本数

    Returns:
        (选中的记录列表, 采样统计字典)
    """
    record_dict = {rec.record_id: rec for rec in all_records}

    # 分类triggered records
    high_priority_ids = []  # fired + margin changed OR effective
    medium_priority_ids = []  # fired only
    low_priority_ids = []  # evaluated only

    # 构建事件字典
    event_dict = {e.record_id: e for e in baseline_aggregator.events}

    for rid in triggered_ids:
        if rid not in event_dict:
            continue

        event = event_dict[rid]

        # 判断是否effective (order changed)
        is_effective = (event.initial_order != event.final_order)

        # 判断是否margin changed (需要对比ablation结果,暂时用score_margin作为proxy)
        has_margin = abs(event.score_margin) > 0.1

        if is_effective or has_margin:
            high_priority_ids.append(rid)
        elif is_module_fired(event, module_name):
            medium_priority_ids.append(rid)
        else:
            low_priority_ids.append(rid)

    # 采样策略
    selected_ids = []
    sampling_stats = {
        "high_priority_available": len(high_priority_ids),
        "medium_priority_available": len(medium_priority_ids),
        "low_priority_available": len(low_priority_ids),
        "total_triggered": len(triggered_ids),
        "high_priority_selected": 0,
        "medium_priority_selected": 0,
        "low_priority_selected": 0,
        "challenge_set_selected": 0
    }

    # 1. 优先选择high priority
    if len(high_priority_ids) >= n_samples:
        selected_ids = random.sample(high_priority_ids, n_samples)
        sampling_stats["high_priority_selected"] = n_samples
    else:
        selected_ids.extend(high_priority_ids)
        sampling_stats["high_priority_selected"] = len(high_priority_ids)
        remaining = n_samples - len(selected_ids)

        # 2. 补充medium priority
        if remaining > 0 and len(medium_priority_ids) > 0:
            to_add = min(remaining, len(medium_priority_ids))
            selected_ids.extend(random.sample(medium_priority_ids, to_add))
            sampling_stats["medium_priority_selected"] = to_add
            remaining -= to_add

        # 3. 补充low priority
        if remaining > 0 and len(low_priority_ids) > 0:
            to_add = min(remaining, len(low_priority_ids))
            selected_ids.extend(random.sample(low_priority_ids, to_add))
            sampling_stats["low_priority_selected"] = to_add
            remaining -= to_add

        # 4. Challenge set fallback (从all_records中选择未触发的)
        if remaining > 0:
            other_ids = [rec.record_id for rec in all_records if rec.record_id not in triggered_ids]
            if len(other_ids) > 0:
                to_add = min(remaining, len(other_ids))
                selected_ids.extend(random.sample(other_ids, to_add))
                sampling_stats["challenge_set_selected"] = to_add

    # 转换为NameRecord对象
    selected_records = [record_dict[rid] for rid in selected_ids if rid in record_dict]

    return selected_records, sampling_stats


def is_module_fired(event, module_name: str) -> bool:
    """判断模块是否fired (产生非默认结果)"""
    module_fired_map = {
        "source_prior": event.source_prior_applied,
        "western_exclusion": event.western_exclusion_fired,
        "batch_consistency": event.batch_consistency_override,
        "person_consistency": event.person_consistency_override,
        "pub_consistency": event.pub_consistency_override,
    }
    return module_fired_map.get(module_name, False)


def generate_sanity_samples(
    all_records: List[NameRecord],
    ground_truth: Dict[str, str],
    triggered_subsets: Dict[str, List[str]],
    ablation_configs: Dict[str, AblationConfig],
    experiment_results: Dict[str, Dict],
    output_dir: str,
    n_samples_per_module: int = 30
):
    """
    生成所有模块的sanity check样本 (智能采样 + 中性措辞)
    Generate sanity check samples for all modules (smart sampling + neutral wording)

    采样策略 / Sampling Strategy:
    - 优先选择"fired + margin changed"或"effective"的样本
    - 如果不足，回退到challenge set
    - 报告措辞：描述"观察到的现象"而非"证明了改变"

    Args:
        all_records: 所有记录
        ground_truth: Ground truth
        triggered_subsets: 触发子集字典
        ablation_configs: 消融配置字典
        experiment_results: 实验结果字典 (包含aggregator)
        output_dir: 输出目录
        n_samples_per_module: 每个模块的样本数
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    record_dict = {rec.record_id: rec for rec in all_records}
    baseline_config = ablation_configs.get("baseline", AblationConfig())
    baseline_aggregator = experiment_results.get("baseline", {}).get("aggregator")

    # 模块到消融配置的映射（与ablation.yaml中的键一致）
    module_to_ablation = {
        "source_prior": "ablation_no_source_prior",
        "western_exclusion": "ablation_no_western_exclusion",
        "batch_consistency": "ablation_no_batch_consistency",
        "person_consistency": "ablation_no_person_consistency",
        "pub_consistency": "ablation_no_pub_consistency",
    }

    all_samples = []

    for module, ablation_name in module_to_ablation.items():
        print(f"\nGenerating sanity samples for: {module}")

        triggered_ids = triggered_subsets.get(module, [])
        print(f"  Triggered records: {len(triggered_ids)}")

        # 选择样本 (智能采样)
        sample_records, sampling_stats = select_samples_for_module(
            all_records, ground_truth, triggered_ids, module, baseline_aggregator, n_samples_per_module
        )
        print(f"  Selected {len(sample_records)} samples:")
        print(f"    High-priority (fired+margin/effective): {sampling_stats['high_priority_selected']}")
        print(f"    Medium-priority (fired only): {sampling_stats['medium_priority_selected']}")
        print(f"    Low-priority (evaluated only): {sampling_stats['low_priority_selected']}")
        print(f"    Challenge set fallback: {sampling_stats['challenge_set_selected']}")

        # Baseline运行
        set_ablation_config(baseline_config)
        baseline_decisions, baseline_agg = batch_identify_with_event_tracking(sample_records)
        reset_ablation_config()

        # Ablation运行
        ablation_config = ablation_configs.get(ablation_name)
        if ablation_config is None:
            print(f"  WARNING: Ablation config {ablation_name} not found")
            continue

        set_ablation_config(ablation_config)
        ablation_decisions, ablation_agg = batch_identify_with_event_tracking(sample_records)
        reset_ablation_config()

        # 对比结果
        module_samples = []
        for rec in sample_records:
            rid = rec.record_id
            gt = ground_truth.get(rid, "unknown")

            baseline_dec = baseline_decisions.get(rid)
            ablation_dec = ablation_decisions.get(rid)

            if baseline_dec is None or ablation_dec is None:
                continue

            # 查找事件获取margin
            baseline_event = [e for e in baseline_agg.events if e.record_id == rid]
            ablation_event = [e for e in ablation_agg.events if e.record_id == rid]

            baseline_margin = baseline_event[0].score_margin if baseline_event else 0.0
            ablation_margin = ablation_event[0].score_margin if ablation_event else 0.0

            sample = SanitySample(
                record_id=rid,
                name_raw=rec.name_raw,
                affiliation=rec.affiliation_raw or "",
                ground_truth=gt,
                baseline_order=baseline_dec.order,
                baseline_confidence=baseline_dec.confidence,
                baseline_reasons=", ".join(baseline_dec.reason_codes[:5]),  # 前5个
                baseline_margin=baseline_margin,
                ablation_order=ablation_dec.order,
                ablation_confidence=ablation_dec.confidence,
                ablation_reasons=", ".join(ablation_dec.reason_codes[:5]),
                ablation_margin=ablation_margin,
                order_changed=(baseline_dec.order != ablation_dec.order),
                module_name=module
            )

            module_samples.append(sample)

        all_samples.extend(module_samples)
        print(f"  Generated {len(module_samples)} sanity samples")

        # 统计order变化
        changed_count = sum(1 for s in module_samples if s.order_changed)
        print(f"  Order changed: {changed_count}/{len(module_samples)}")

    # 保存所有样本到JSONL
    with open(output_path / "ablation_sanity_samples.jsonl", 'w', encoding='utf-8') as f:
        for sample in all_samples:
            f.write(json.dumps(asdict(sample), ensure_ascii=False) + '\n')

    # 生成Markdown报告
    generate_sanity_md(all_samples, output_path / "ablation_sanity_samples.md")

    print(f"\nSanity samples generation complete. Total samples: {len(all_samples)}")
    print(f"Saved to: {output_dir}")


def generate_sanity_md(samples: List[SanitySample], filepath: str):
    """生成Markdown报告"""
    # 按模块分组
    samples_by_module = {}
    for sample in samples:
        module = sample.module_name
        if module not in samples_by_module:
            samples_by_module[module] = []
        samples_by_module[module].append(sample)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# 消融Sanity Check样本 / Ablation Sanity Check Samples\n\n")
        f.write("本报告展示了每个模块的代表性样本,描述在该数据集上观察到的现象。\n")
        f.write("This report shows representative samples for each module, describing the phenomena observed on this dataset.\n\n")

        for module, module_samples in samples_by_module.items():
            f.write(f"## {module.replace('_', ' ').title()}\n\n")

            # 统计
            total = len(module_samples)
            changed = sum(1 for s in module_samples if s.order_changed)
            fired = sum(1 for s in module_samples if s.order_changed)  # Simplified: using order_changed as proxy for fired
            effective = changed  # Order changed means effective

            f.write(f"**采样情况 / Sampling Summary**:\n")
            f.write(f"- 总样本数 / Total Samples: {total}\n")
            f.write(f"- Fired样本 / Fired Samples: {fired} ({100*fired/total:.1f}%)\n")
            f.write(f"- Effective样本 / Effective Samples: {effective} ({100*effective/total:.1f}%)\n\n")

            f.write(f"**在该数据集上的观察 / Observations on This Dataset**:\n")
            if changed > 0:
                f.write(f"- 在{changed}个样本({100*changed/total:.1f}%)上观察到order改变\n")
                f.write(f"- Observed order changes in {changed} samples ({100*changed/total:.1f}%)\n\n")
            else:
                f.write(f"- 在该数据集上未观察到order改变 (可能因为模块未触发或触发率极低)\n")
                f.write(f"- No order changes observed on this dataset (possibly due to low trigger rate or module not firing)\n\n")

            # 展示3-5个代表样本（优先选择order改变的）
            representative = [s for s in module_samples if s.order_changed][:3]
            if len(representative) < 3:
                # 补充未改变的
                unchanged = [s for s in module_samples if not s.order_changed]
                representative.extend(unchanged[:3 - len(representative)])

            for i, sample in enumerate(representative, 1):
                f.write(f"### 样本 {i}\n\n")
                f.write(f"**姓名**: {sample.name_raw}\n")
                if sample.affiliation:
                    f.write(f"**机构**: {sample.affiliation[:100]}...\n")
                f.write(f"**Ground Truth**: {sample.ground_truth}\n\n")

                f.write("| 配置 | Order | Confidence | Margin | Reasons |\n")
                f.write("|------|-------|------------|--------|----------|\n")
                f.write(f"| Baseline | {sample.baseline_order} | {sample.baseline_confidence:.3f} | "
                        f"{sample.baseline_margin:+.3f} | {sample.baseline_reasons} |\n")
                f.write(f"| Ablation | {sample.ablation_order} | {sample.ablation_confidence:.3f} | "
                        f"{sample.ablation_margin:+.3f} | {sample.ablation_reasons} |\n")

                if sample.order_changed:
                    f.write("\n**观察**: 该样本上观察到order改变 (Baseline→Ablation)\n")
                    f.write("**Observation**: Order change observed on this sample (Baseline→Ablation)\n\n")
                else:
                    f.write("\n**观察**: 该样本上未观察到order改变\n")
                    f.write("**Observation**: No order change observed on this sample\n\n")

            f.write("---\n\n")
