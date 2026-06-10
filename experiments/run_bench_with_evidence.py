# -*- coding: utf-8 -*-
"""
带证据链的基准测试 / Benchmark with Evidence Chain

完整的论文审稿证据链实验
Complete paper review evidence chain experiment

作者: Ma Jiaxin
日期: 2025-12-19
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入所有需要的模块
from experiments.run_bench import (
    get_git_info,
    get_pip_freeze,
    load_ablation_configs,
    get_system_info
)
from experiments.dataset_analyzer import DatasetAnalyzer, generate_dataset_card
from experiments.event_collection import batch_identify_with_event_tracking
from experiments.triggered_subset_analysis import run_triggered_subset_ablation
from experiments.sanity_samples import generate_sanity_samples
from experiments.statistical_tests import generate_statistical_report
from experiments.validation_utils import (
    set_random_seeds,
    generate_extended_manifest,
    validate_n_consistency
)

from src.surname_identifier_v8 import NameRecord
from src.config_v8 import set_ablation_config, reset_ablation_config


def run_consistency_check(
    dataset_path: str,
    experiment_results: Dict[str, Dict],
    output_dir: str
) -> bool:
    """
    对比evidence chain实验与paper实验的指标一致性
    Compare metrics consistency between evidence chain and paper experiments

    Args:
        dataset_path: 数据集路径
        experiment_results: 证据链实验结果
        output_dir: 输出目录

    Returns:
        bool: 是否通过一致性检查
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 推断paper实验目录
    dataset_name = Path(dataset_path).stem
    paper_experiment_dir = Path("runs") / f"paper_{dataset_name}"
    paper_metrics_path = paper_experiment_dir / "results" / "metrics.json"

    if not paper_metrics_path.exists():
        print(f"  [WARNING] Paper experiment not found: {paper_experiment_dir}")
        print("  Skipping consistency check...")
        return True

    # 加载paper实验结果
    with open(paper_metrics_path, 'r', encoding='utf-8') as f:
        paper_metrics = json.load(f)

    # 提取平均值（找到带_mean后缀的条目）
    paper_results = {}
    for entry in paper_metrics:
        config_name = entry.get("config_name", "")
        if "_mean" in entry:  # 跳过mean summary行
            continue
        if "accuracy_mean" in entry:  # 这是平均值条目
            paper_results[config_name] = {
                "accuracy": entry["accuracy_mean"],
                "unknown_rate": entry["unknown_rate_mean"],
                "error_rate": entry["error_rate_mean"]
            }
            break  # 只需要第一个平均值

    # 如果没有mean，使用第一次运行的结果
    if not paper_results:
        for entry in paper_metrics:
            config_name = entry.get("config_name", "")
            if config_name and "repeat" in entry and entry["repeat"] == 0:
                paper_results[config_name] = {
                    "accuracy": entry["accuracy"],
                    "unknown_rate": entry["unknown_rate"],
                    "error_rate": entry["error_rate"]
                }

    # 对比结果
    TOLERANCE = 1e-3  # 允许0.1%的误差
    discrepancies = []
    all_passed = True

    # 配置名称映射（paper实验用v8.0_前缀，evidence_chain用不同前缀）
    config_mapping = {
        "v8.0_baseline": "baseline",
        "v8.0_no_source_prior": "ablation_no_source_prior",
        "v8.0_no_western_exclusion": "ablation_no_western_exclusion",
        "v8.0_no_batch_consistency": "ablation_no_batch_consistency",
        "v8.0_no_person_consistency": "ablation_no_person_consistency",
        "v8.0_no_pub_consistency": "ablation_no_pub_consistency"
    }

    for paper_config, evidence_config in config_mapping.items():
        if paper_config not in paper_results or evidence_config not in experiment_results:
            continue

        paper = paper_results[paper_config]
        evidence = experiment_results[evidence_config]

        # 检查三项指标
        metrics = ["accuracy", "unknown_rate", "error_rate"]
        for metric in metrics:
            paper_val = paper[metric]
            evidence_val = evidence[metric]
            diff = abs(paper_val - evidence_val)

            if diff > TOLERANCE:
                all_passed = False
                discrepancies.append({
                    "config": evidence_config,
                    "metric": metric,
                    "paper_value": paper_val,
                    "evidence_value": evidence_val,
                    "difference": diff,
                    "tolerance": TOLERANCE
                })

    # 生成报告
    report = {
        "dataset": dataset_path,
        "paper_experiment_dir": str(paper_experiment_dir),
        "tolerance": TOLERANCE,
        "passed": all_passed,
        "discrepancies": discrepancies
    }

    with open(output_path / "consistency_check.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 生成Markdown报告
    with open(output_path / "consistency_check.md", 'w', encoding='utf-8') as f:
        f.write("# Consistency Check Report\n\n")
        f.write(f"**Dataset**: {dataset_path}\n")
        f.write(f"**Paper Experiment**: {paper_experiment_dir}\n")
        f.write(f"**Tolerance**: {TOLERANCE} (0.1%)\n\n")

        if all_passed:
            f.write("## PASSED: All metrics match within tolerance!\n\n")
            print("  [PASS] Consistency check PASSED")
        else:
            f.write("## FAILED: Metrics discrepancies detected\n\n")
            f.write("### Discrepancies:\n\n")
            f.write("| Config | Metric | Paper | Evidence | Diff | Status |\n")
            f.write("|--------|--------|-------|----------|------|--------|\n")

            for disc in discrepancies:
                f.write(f"| {disc['config']} | {disc['metric']} | ")
                f.write(f"{disc['paper_value']:.4f} | {disc['evidence_value']:.4f} | ")
                f.write(f"{disc['difference']:.4f} | FAIL |\n")

            print(f"  [FAIL] Consistency check FAILED ({len(discrepancies)} discrepancies)")
            print("  Check consistency_check.md for details")

    return all_passed


def load_dataset(dataset_path: str) -> tuple[List[NameRecord], Dict[str, str]]:
    """
    加载数据集
    Load dataset

    Returns:
        (records, ground_truth)
    """
    print(f"Loading dataset: {dataset_path}")

    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    ground_truth = {}

    for i, item in enumerate(data):
        # 提取字段
        record_id = str(item.get('id', i))
        name_raw = item.get('name', item.get('author_name', item.get('original_name', '')))
        source = item.get('source', item.get('data_source', 'CROSSREF'))
        affiliation = item.get('affiliation', item.get('affiliation_raw', ''))
        person_id = item.get('person_id', item.get('author_id'))
        pub_id = item.get('publication_id', item.get('doi'))

        # Ground truth
        gt_order = item.get('name_order', item.get('order', item.get('ground_truth')))
        if gt_order:
            # 标准化
            if gt_order in ('family_first', 'surname_first', 1, '1'):
                ground_truth[record_id] = 'family_first'
            elif gt_order in ('given_first', 'givenname_first', -1, '-1'):
                ground_truth[record_id] = 'given_first'
        else:
            # 从lastname/firstname推断（与run_bench.py方法一致）
            lastname = item.get('lastname', item.get('family', ''))
            firstname = item.get('firstname', item.get('given', ''))
            original_name = name_raw

            if lastname and firstname and original_name:
                # 使用与paper实验一致的方法：检查original_name是否以lastname开头
                if original_name.strip().startswith(lastname):
                    ground_truth[record_id] = 'family_first'
                else:
                    ground_truth[record_id] = 'given_first'

        rec = NameRecord(
            record_id=record_id,
            source=source,
            person_id=person_id,
            publication_id=pub_id,
            name_raw=name_raw,
            affiliation_raw=affiliation if affiliation else None
        )
        records.append(rec)

    print(f"  Loaded {len(records)} records")
    print(f"  Ground truth: {len(ground_truth)} records")

    return records, ground_truth


def run_evidence_chain_experiment(
    dataset_path: str,
    ablation_config_path: str,
    output_dir: str
):
    """
    运行完整的证据链实验
    Run complete evidence chain experiment

    Args:
        dataset_path: 数据集路径
        ablation_config_path: 消融配置文件路径
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # ========== 第0步：元数据与随机种子 ==========
    print("\n" + "=" * 80)
    print("Evidence Chain Experiment")
    print("=" * 80)

    # 设置随机种子以确保可复现性
    set_random_seeds(42)
    print("  Random seeds set to 42")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    git_info = get_git_info()
    system_info = get_system_info()

    # ========== 第1步：加载数据 ==========
    print("\n[1/7] Loading dataset...")
    records, ground_truth = load_dataset(dataset_path)

    # 数据集分析
    analyzer = DatasetAnalyzer(dataset_path)
    stats = analyzer.analyze()

    # ========== 第2步：加载消融配置 ==========
    print("\n[2/7] Loading ablation configs...")
    configs_dict = load_ablation_configs(ablation_config_path)

    # 转换为AblationConfig对象
    from src.config_v8 import AblationConfig
    ablation_configs = {}
    for name, cfg_dict in configs_dict.items():
        ablation_configs[name] = AblationConfig(
            disable_source_prior=cfg_dict.get("disable_source_prior", False),
            disable_western_exclusion=cfg_dict.get("disable_western_exclusion", False),
            disable_batch_consistency=cfg_dict.get("disable_batch_consistency", False),
            surname_freq_strategy=cfg_dict.get("surname_freq_strategy", "share_ratio"),
            surname_share_ratio_threshold=cfg_dict.get("surname_share_ratio_threshold", 1.0),
            enable_person_consistency=cfg_dict.get("enable_person_consistency", True),
            enable_pub_consistency=cfg_dict.get("enable_pub_consistency", True),
        )

    print(f"  Loaded {len(ablation_configs)} configurations")

    # ========== 第3步：运行基准实验（带事件追踪）==========
    print("\n[3/7] Running baseline with event tracking...")

    experiment_results = {}

    for config_name, config in ablation_configs.items():
        print(f"\n  Running config: {config_name}")
        set_ablation_config(config)

        # 批量识别（带事件追踪）
        decisions, aggregator = batch_identify_with_event_tracking(
            records,
            enable_person_consistency=config.enable_person_consistency,
            enable_pub_consistency=config.enable_pub_consistency
        )

        reset_ablation_config()

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
        accuracy = correct / total if total > 0 else 0.0
        unknown_rate = unknown / total if total > 0 else 0.0
        error_rate = incorrect / total if total > 0 else 0.0

        print(f"    Accuracy: {accuracy*100:.2f}%, Unknown: {unknown_rate*100:.2f}%, Error: {error_rate*100:.2f}%")

        # 保存事件
        config_output_dir = output_path / "events" / config_name
        config_output_dir.mkdir(parents=True, exist_ok=True)
        aggregator.save_statistics(str(config_output_dir))

        # 保存结果
        experiment_results[config_name] = {
            "accuracy": accuracy,
            "unknown_rate": unknown_rate,
            "error_rate": error_rate,
            "correct": correct,
            "incorrect": incorrect,
            "unknown": unknown,
            "total": total,
            "decisions": {rid: dec.order for rid, dec in decisions.items()},
            "aggregator": aggregator
        }

    # ========== 第4步：触发子集消融分析 ==========
    print("\n[4/7] Running triggered subset ablation analysis...")

    run_triggered_subset_ablation(
        records,
        ground_truth,
        ablation_configs,
        str(output_path / "triggered_subsets")
    )

    # ========== 第5步：生成Sanity Check样本 ==========
    print("\n[5/7] Generating sanity check samples...")

    # 加载触发子集
    triggered_subsets = {}
    for module in ["source_prior", "western_exclusion", "batch_consistency", "person_consistency", "pub_consistency"]:
        ids_file = output_path / "triggered_subsets" / "triggered_subset_ids" / f"{module}_ids.txt"
        if ids_file.exists():
            with open(ids_file, 'r', encoding='utf-8') as f:
                triggered_subsets[module] = [line.strip() for line in f if line.strip()]

    generate_sanity_samples(
        records,
        ground_truth,
        triggered_subsets,
        ablation_configs,
        experiment_results,  # Pass experiment_results for smart sampling
        str(output_path / "sanity_samples")
    )

    # ========== 第6步：统计显著性分析 ==========
    print("\n[6/7] Running statistical significance tests...")

    # 提取dataset name和run_id
    dataset_name = Path(dataset_path).stem
    run_id = Path(output_dir).name

    # metrics.json路径 (for strict validation)
    # Note: metrics.json doesn't exist in evidence_chain runs, only in paper runs
    # But we pass results_path for potential future use
    results_metrics_path = output_path / "results" / "metrics.json"

    # (P0-P3收敛任务4+5): Global stats - 传递n_records_total确保metadata完整
    # Global stats - pass n_records_total to ensure complete metadata
    generate_statistical_report(
        results=experiment_results,
        ground_truth=ground_truth,
        output_dir=str(output_path / "statistics"),
        dataset_name=dataset_name,
        run_id=run_id,
        config_dict=configs_dict,  # Pass config dict for hash computation
        metrics_json_path=results_metrics_path if results_metrics_path.exists() else None,
        n_records_total=len(records)  # (P0-P3收敛任务4): 明确传递N_total
    )

    # Triggered subset stats (for fired and effective)
    print("\n  Generating triggered subset statistics...")
    from experiments.statistical_tests import generate_triggered_subset_stats

    baseline_aggregator = experiment_results.get("baseline", {}).get("aggregator")
    print(f"    baseline_aggregator exists: {baseline_aggregator is not None}")

    if baseline_aggregator:
        module_coverage = baseline_aggregator.get_module_coverage()
        print(f"    module_coverage keys: {list(module_coverage.get('modules', {}).keys())}")

        # 为每个模块生成fired和effective子集统计
        modules = ["source_prior", "western_exclusion", "batch_consistency",
                   "person_consistency", "pub_consistency"]

        for module_name in modules:
            print(f"    Processing module: {module_name}")
            # 获取ablation配置
            ablation_key = f"ablation_no_{module_name}"
            if ablation_key not in ablation_configs:
                continue

            baseline_config = ablation_configs["baseline"]
            ablation_config = ablation_configs[ablation_key]

            # Fired subset
            module_in_coverage = module_name in module_coverage.get("modules", {})
            has_fired_field = "fired" in module_coverage.get("modules", {}).get(module_name, {})
            print(f"      module_in_coverage: {module_in_coverage}, has_fired: {has_fired_field}")

            if module_in_coverage and has_fired_field:
                fired_count = module_coverage["modules"][module_name]["fired"]
                print(f"      fired_count: {fired_count}")
                # P3: Process even if fired_count == 0
                # 收集fired记录
                fired_records = []

                # For batch/person/pub_consistency: fired = all records (always evaluated)
                # For others: fired = specific condition
                if module_name in ["batch_consistency", "person_consistency", "pub_consistency"]:
                    # These modules are always evaluated on all records
                    fired_records = list(records)  # All records
                else:
                    # For other modules, collect based on specific events
                    for event in baseline_aggregator.events:
                        is_fired = False
                        if module_name == "source_prior" and event.source_prior_applied:
                            is_fired = True
                        elif module_name == "western_exclusion" and event.western_exclusion_fired:
                            is_fired = True

                        if is_fired:
                            # 找到对应的record
                            rec = next((r for r in records if r.record_id == event.record_id), None)
                            if rec:
                                fired_records.append(rec)

                # P3: Generate stats only for small subsets or N=0
                # Skip if N is too large (>5000, essentially same as global)
                n_fired = len(fired_records)
                total_records = len(records)

                if n_fired == 0 or (n_fired > 0 and n_fired < total_records * 0.5):
                    # Generate stats for N=0 or meaningful subsets (<50% of total)
                    print(f"      Generating fired stats for {module_name} (N={n_fired})...")
                    try:
                        generate_triggered_subset_stats(
                            subset_records=fired_records,
                            ground_truth=ground_truth,
                            baseline_config=baseline_config,
                            ablation_config=ablation_config,
                            output_dir=str(output_path / "statistics"),
                            module_name=module_name,
                            trigger_type="fired",
                            dataset_name=dataset_name,
                            run_id=run_id,
                            config_dict=configs_dict
                        )
                        print(f"      [OK] Fired stats generated for {module_name}")
                    except Exception as e:
                        print(f"      [ERROR] Error generating fired stats for {module_name}: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"      Skipping fired stats for {module_name} (N={n_fired}, too large or same as global)")

            # Effective subset
            has_effective_field = "effective" in module_coverage.get("modules", {}).get(module_name, {})
            if module_in_coverage and has_effective_field:
                effective_count = module_coverage["modules"][module_name]["effective"]
                print(f"      effective_count: {effective_count}")
                # P3: Process even if effective_count == 0
                # 收集effective记录
                effective_records = []
                for event in baseline_aggregator.events:
                    is_effective = False
                    if module_name == "source_prior" and getattr(event, 'source_prior_effective', False):
                        is_effective = True
                    elif module_name == "western_exclusion" and getattr(event, 'western_exclusion_effective', False):
                        is_effective = True
                    elif module_name == "batch_consistency" and event.batch_consistency_override:
                        is_effective = True
                    elif module_name == "person_consistency" and event.person_consistency_override:
                        is_effective = True
                    elif module_name == "pub_consistency" and event.pub_consistency_override:
                        is_effective = True

                    if is_effective:
                        # 找到对应的record
                        rec = next((r for r in records if r.record_id == event.record_id), None)
                        if rec:
                            effective_records.append(rec)

                # P3: Generate stats only for small subsets or N=0
                n_effective = len(effective_records)

                if n_effective == 0 or (n_effective > 0 and n_effective < total_records * 0.5):
                    print(f"      Generating effective stats for {module_name} (N={n_effective})...")
                    try:
                        generate_triggered_subset_stats(
                            subset_records=effective_records,
                            ground_truth=ground_truth,
                            baseline_config=baseline_config,
                            ablation_config=ablation_config,
                            output_dir=str(output_path / "statistics"),
                            module_name=module_name,
                            trigger_type="effective",
                            dataset_name=dataset_name,
                            run_id=run_id,
                            config_dict=configs_dict
                        )
                        print(f"      [OK] Effective stats generated for {module_name}")
                    except Exception as e:
                        print(f"      [ERROR] Error generating effective stats for {module_name}: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"      Skipping effective stats for {module_name} (N={n_effective}, too large or same as global)")

    # ========== 第7步：一致性检查 ==========
    print("\n[7/9] Running consistency check...")
    consistency_check_passed = run_consistency_check(
        dataset_path,
        experiment_results,
        str(output_path / "consistency_check")
    )

    # ========== 第8步：生成综合报告 ==========
    print("\n[8/9] Generating comprehensive report...")

    # 计算dataset SHA256
    import hashlib
    with open(dataset_path, 'rb') as f:
        dataset_sha256 = hashlib.sha256(f.read()).hexdigest()

    # Base manifest
    base_manifest = {
        "timestamp_utc": timestamp,
        "dataset": dataset_path,
        "dataset_size": len(records),
        "dataset_sha256": dataset_sha256,
        "ground_truth_size": len(ground_truth),
        "git_info": git_info,
        "system_info": system_info,
        "ablation_configs": {k: v.__dict__ for k, v in ablation_configs.items()},
        "results_summary": {
            k: {
                "accuracy": v["accuracy"],
                "unknown_rate": v["unknown_rate"],
                "error_rate": v["error_rate"],
                "total": v["total"]
            }
            for k, v in experiment_results.items()
        }
    }

    # Extend manifest with reproducibility info
    sampling_params = {
        "ground_truth_inference_method": "startswith",
        "unknown_handling": "excluded from k/n"
    }

    manifest = generate_extended_manifest(
        base_manifest=base_manifest,
        configs_dict=configs_dict,
        sampling_params=sampling_params,
        run_dir=str(output_path)  # P1-4: Pass run_dir for git patch file
    )

    with open(output_path / "run_manifest.json", 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # pip freeze
    pip_freeze = get_pip_freeze()
    with open(output_path / "env.txt", 'w', encoding='utf-8') as f:
        f.write('\n'.join(pip_freeze))

    # ========== 第9步：N一致性验证 ==========
    print("\n[9/9] Validating N consistency across all outputs...")

    # 加载stats_ci和module_coverage进行验证
    stats_ci_path = output_path / "statistics" / "stats_ci_global.json"
    baseline_aggregator = experiment_results.get("baseline", {}).get("aggregator")

    n_records_total = len(records)
    n_records_labeled = len(ground_truth)

    if stats_ci_path.exists():
        with open(stats_ci_path, 'r', encoding='utf-8') as f:
            stats_ci = json.load(f)

        # 获取baseline的module_coverage
        module_coverage = {}
        if baseline_aggregator:
            module_coverage = baseline_aggregator.get_module_coverage()

        try:
            validate_n_consistency(
                n_records_total=n_records_total,
                n_records_labeled=n_records_labeled,
                stats_ci=stats_ci,
                module_coverage=module_coverage,
                run_manifest=manifest,
                strict=True
            )
            print("  [PASS] N consistency validation passed")
        except ValueError as e:
            print("  [FAIL] N consistency validation failed:")
            print(str(e))
            raise
    else:
        print("  [WARNING] stats_ci_global.json not found, skipping validation")

    print("\n" + "=" * 80)
    print("Evidence Chain Experiment Complete!")
    print("=" * 80)
    print(f"\nResults saved to: {output_path}")
    print("\nGenerated files:")
    print("  - run_manifest.json: Experiment metadata")
    print("  - env.txt: Environment information")
    print("  - events/*/module_coverage.json: Module trigger statistics")
    print("  - events/*/module_coverage.md: Module trigger report (Markdown)")
    print("  - events/*/reason_counts.csv: Reason code frequencies")
    print("  - events/*/score_margin_stats.json: Score margin statistics")
    print("  - triggered_subsets/ablation_triggered_subsets.json: Triggered subset results")
    print("  - triggered_subsets/ablation_triggered_subsets.md: Triggered subset report")
    print("  - triggered_subsets/ablation_triggered_subsets.tex: Triggered subset table (LaTeX)")
    print("  - sanity_samples/ablation_sanity_samples.jsonl: Sanity check samples")
    print("  - sanity_samples/ablation_sanity_samples.md: Sanity check report")
    print("  - statistics/stats_ci_global.json: Statistical tests results (with metadata)")
    print("  - statistics/stats_ci_global.md: Statistical report (Markdown)")
    print("  - statistics/stats_ci_global.tex: Statistical table (LaTeX, booktabs)")


def main():
    parser = argparse.ArgumentParser(description="Run benchmark with full evidence chain")
    parser.add_argument("--dataset", required=True, help="Path to dataset JSON file")
    parser.add_argument("--config", required=True, help="Path to ablation config YAML file")
    parser.add_argument("--output", required=True, help="Output directory")

    args = parser.parse_args()

    run_evidence_chain_experiment(
        args.dataset,
        args.config,
        args.output
    )


if __name__ == "__main__":
    main()
