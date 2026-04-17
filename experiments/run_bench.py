# -*- coding: utf-8 -*-
"""
论文级可复现实验记录工具 / Paper-Level Reproducible Experiment Recording Tool

用于运行基准测试并记录完整的实验环境和结果
Runs benchmarks and records complete experimental environment and results

作者: Ma Jiaxin
日期: 2025-12-19
"""

import os
import sys
import json
import csv
import argparse
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import platform

# 添加项目根目录到路径 / Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目模块 / Import project modules
from src.surname_identifier_v8 import (
    identify_surname_position_v8,
    batch_identify_surname_position_v8,
    NameRecord
)
from src.config_v8 import (
    AblationConfig,
    set_ablation_config,
    reset_ablation_config,
    get_config
)
from experiments.performance_metrics import (
    measure_performance,
    get_system_info,
    PerformanceMonitor
)
from experiments.dataset_analyzer import DatasetAnalyzer, generate_dataset_card

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("Warning: PyYAML not installed. Ablation config loading disabled.")


def get_git_info() -> Dict[str, str]:
    """
    获取Git仓库信息 / Get Git repository information

    Returns:
        包含Git信息的字典 / Dictionary with Git information
    """
    git_info = {
        "commit_sha": "unknown",
        "commit_sha_short": "unknown",
        "branch": "unknown",
        "is_dirty": "unknown",
        "remote_url": "unknown"
    }

    try:
        # Commit SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False
        )
        if result.returncode == 0:
            git_info["commit_sha"] = result.stdout.strip()
            git_info["commit_sha_short"] = git_info["commit_sha"][:7]

        # Branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False
        )
        if result.returncode == 0:
            git_info["branch"] = result.stdout.strip()

        # Dirty status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False
        )
        if result.returncode == 0:
            git_info["is_dirty"] = "yes" if result.stdout.strip() else "no"

        # Remote URL
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False
        )
        if result.returncode == 0:
            git_info["remote_url"] = result.stdout.strip()

    except Exception as e:
        print(f"Warning: Failed to get git info: {e}")

    return git_info


def get_pip_freeze() -> List[str]:
    """
    获取pip freeze输出 / Get pip freeze output

    Returns:
        依赖包列表 / List of dependencies
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n')
    except Exception as e:
        print(f"Warning: Failed to get pip freeze: {e}")

    return ["pip freeze failed"]


def load_ablation_configs(yaml_path: str) -> Dict[str, Dict[str, Any]]:
    """
    从YAML文件加载消融实验配置 / Load ablation configs from YAML file

    Args:
        yaml_path: YAML配置文件路径 / YAML config file path

    Returns:
        配置字典 / Configuration dictionary
    """
    if not HAS_YAML:
        raise RuntimeError("PyYAML is required for ablation config loading")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        configs = yaml.safe_load(f)

    return configs


def load_dataset(file_path: str) -> List[Dict[str, Any]]:
    """
    加载数据集 / Load dataset

    支持JSON和JSONL格式 / Supports JSON and JSONL formats

    Args:
        file_path: 数据集文件路径 / Dataset file path

    Returns:
        记录列表 / List of records
    """
    path = Path(file_path)

    with open(path, 'r', encoding='utf-8') as f:
        if path.suffix == '.jsonl':
            records = [json.loads(line) for line in f if line.strip()]
        else:
            records = json.load(f)

    return records


def evaluate_algorithm(
    records: List[Dict[str, Any]],
    config_name: str = "baseline",
    warmup: bool = False
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    评估算法性能 / Evaluate algorithm performance

    Args:
        records: 数据记录列表 / List of data records
        config_name: 配置名称 / Configuration name
        warmup: 是否为预热运行 / Whether this is a warmup run

    Returns:
        (评估结果, 错误样本列表) / (evaluation results, error samples)
    """
    # 转换为NameRecord对象 / Convert to NameRecord objects
    name_records = []
    for i, rec in enumerate(records):
        name_records.append(NameRecord(
            record_id=str(i),
            name_raw=rec.get('original_name', ''),
            affiliation_raw=rec.get('affiliation'),
            source=rec.get('source', 'CROSSREF'),
            person_id=rec.get('person_id'),
            publication_id=rec.get('doi')
        ))

    # 性能监控 / Performance monitoring
    monitor = PerformanceMonitor()
    monitor.start()

    # 批量识别 / Batch identification
    decisions = batch_identify_surname_position_v8(name_records)

    # 停止监控 / Stop monitoring
    metrics = monitor.stop(n_records=len(records))

    # 计算准确率（如果有ground truth）/ Calculate accuracy (if ground truth exists)
    correct = 0
    total = 0
    unknown_count = 0
    error_samples = []

    for i, rec in enumerate(records):
        decision = decisions[str(i)]

        # 判断正确性 / Check correctness
        if 'lastname' in rec and 'firstname' in rec:
            total += 1

            # 推断ground truth
            lastname = rec['lastname']
            firstname = rec['firstname']
            original_name = rec.get('original_name', '')

            # 简单启发式：如果lastname出现在开头，则是family_first
            if original_name.strip().startswith(lastname):
                gt_order = "family_first"
            else:
                gt_order = "given_first"

            if decision.order == "unknown":
                unknown_count += 1
                # 记录unknown错误
                error_samples.append({
                    "record_id": i,
                    "original_name": original_name,
                    "predicted": "unknown",
                    "ground_truth": gt_order,
                    "confidence": decision.confidence,
                    "reason": ", ".join(decision.reason_codes),
                    "affiliation": rec.get('affiliation', ''),
                    "source": rec.get('source', '')
                })
            elif decision.order != gt_order:
                # 记录预测错误
                error_samples.append({
                    "record_id": i,
                    "original_name": original_name,
                    "predicted": decision.order,
                    "ground_truth": gt_order,
                    "confidence": decision.confidence,
                    "reason": ", ".join(decision.reason_codes),
                    "affiliation": rec.get('affiliation', ''),
                    "source": rec.get('source', '')
                })
            else:
                correct += 1

    accuracy = correct / total if total > 0 else 0.0
    unknown_rate = unknown_count / total if total > 0 else 0.0
    error_rate = 1.0 - accuracy if total > 0 else 0.0

    result = {
        "config_name": config_name,
        "n_records": len(records),
        "accuracy": accuracy,
        "unknown_rate": unknown_rate,
        "error_rate": error_rate,
        "wall_time_s": metrics.wall_time_s,
        "cpu_user_s": metrics.cpu_user_s,
        "cpu_sys_s": metrics.cpu_sys_s,
        "peak_rss_mb": metrics.peak_rss_mb,
        "names_per_sec": metrics.names_per_sec,
        "warmup": warmup
    }

    return result, error_samples


def run_benchmark(
    dataset_paths: List[str],
    ablation_config_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    n_repeats: int = 3,
    skip_warmup: bool = False
) -> str:
    """
    运行基准测试 / Run benchmark

    Args:
        dataset_paths: 数据集文件路径列表 / List of dataset file paths
        ablation_config_path: 消融实验配置文件路径 / Ablation config file path
        output_dir: 输出目录路径 / Output directory path
        n_repeats: 重复次数 / Number of repeats
        skip_warmup: 是否跳过预热 / Whether to skip warmup

    Returns:
        输出目录路径 / Output directory path
    """
    # 创建输出目录 / Create output directory (ISO 8601 format)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    git_info = get_git_info()
    git_sha = git_info["commit_sha_short"]

    if output_dir is None:
        output_dir = project_root / "runs" / f"{timestamp}__git-{git_sha}"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 创建子目录 / Create subdirectories
    (output_dir / "results").mkdir(exist_ok=True)
    (output_dir / "datasets").mkdir(exist_ok=True)
    (output_dir / "logs").mkdir(exist_ok=True)

    print(f"输出目录 / Output directory: {output_dir}")

    # 加载消融配置 / Load ablation configs
    ablation_configs = {}
    if ablation_config_path:
        ablation_configs = load_ablation_configs(ablation_config_path)
        print(f"加载了 {len(ablation_configs)} 个消融配置 / Loaded {len(ablation_configs)} ablation configs")
    else:
        # 使用默认baseline配置 / Use default baseline config
        ablation_configs = {
            "baseline": {
                "name": "v8.0_baseline",
                "description": "完整v8.0系统 / Full v8.0 system",
                "disable_source_prior": False,
                "disable_western_exclusion": False,
                "disable_batch_consistency": False,
                "surname_freq_strategy": "share_ratio",
                "enable_person_consistency": True,
                "enable_pub_consistency": True
            }
        }

    # 记录运行清单 / Record run manifest
    manifest = {
        "timestamp_utc": timestamp,
        "git_info": git_info,
        "command_line": " ".join(sys.argv),
        "python_version": sys.version.split()[0],
        "system_info": get_system_info(),
        "algorithm_version": "v8.0",
        "ablation_config_file": str(ablation_config_path) if ablation_config_path else None,
        "datasets": [str(p) for p in dataset_paths],
        "n_repeats": n_repeats
    }

    with open(output_dir / "run_manifest.json", 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 记录环境信息 / Record environment info
    pip_packages = get_pip_freeze()
    env_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "pip_freeze": pip_packages
    }

    with open(output_dir / "env.txt", 'w', encoding='utf-8') as f:
        f.write(f"Python Version: {sys.version}\n")
        f.write(f"Platform: {platform.platform()}\n\n")
        f.write("=" * 60 + "\n")
        f.write("Pip Freeze:\n")
        f.write("=" * 60 + "\n")
        for pkg in pip_packages:
            f.write(pkg + "\n")

    # 运行所有实验 / Run all experiments
    all_results = []

    for dataset_path in dataset_paths:
        dataset_path = Path(dataset_path)
        dataset_name = dataset_path.stem

        print(f"\n处理数据集 / Processing dataset: {dataset_name}")

        # 分析数据集 / Analyze dataset
        print("  分析数据集统计信息 / Analyzing dataset statistics...")
        analyzer = DatasetAnalyzer(str(dataset_path))
        stats = analyzer.analyze()

        # 保存统计信息 / Save statistics
        with open(output_dir / "datasets" / f"{dataset_name}.stats.json", 'w', encoding='utf-8') as f:
            json.dump(stats.to_dict(), f, indent=2, ensure_ascii=False)

        # 保存SHA256 / Save SHA256
        with open(output_dir / "datasets" / f"{dataset_name}.sha256", 'w') as f:
            f.write(stats.file_sha256)

        # 生成Dataset Card / Generate Dataset Card
        card_path = output_dir / "datasets" / f"{dataset_name}.dataset_card.md"
        generate_dataset_card(stats, str(card_path))

        # 加载数据 / Load data
        records = load_dataset(str(dataset_path))
        print(f"  加载了 {len(records)} 条记录 / Loaded {len(records)} records")

        # 遍历所有配置 / Iterate through all configs
        for config_key, config_dict in ablation_configs.items():
            print(f"\n  运行配置 / Running config: {config_dict['name']}")

            # 设置消融配置 / Set ablation config
            ablation_cfg = AblationConfig(
                disable_source_prior=config_dict.get('disable_source_prior', False),
                disable_western_exclusion=config_dict.get('disable_western_exclusion', False),
                disable_batch_consistency=config_dict.get('disable_batch_consistency', False),
                surname_freq_strategy=config_dict.get('surname_freq_strategy', 'share_ratio'),
                enable_person_consistency=config_dict.get('enable_person_consistency', True),
                enable_pub_consistency=config_dict.get('enable_pub_consistency', True)
            )
            set_ablation_config(ablation_cfg)

            # Warmup run (if not skipped) / 预热运行（如果未跳过）
            if not skip_warmup:
                print("    预热运行 / Warmup run...")
                _, _ = evaluate_algorithm(records, config_name=config_dict['name'], warmup=True)

            # 重复运行 / Repeated runs
            run_results = []
            all_errors_for_config = []
            for repeat_idx in range(n_repeats):
                print(f"    重复 {repeat_idx + 1}/{n_repeats} / Repeat {repeat_idx + 1}/{n_repeats}...")
                result, error_samples = evaluate_algorithm(records, config_name=config_dict['name'], warmup=False)
                result["dataset"] = dataset_name
                result["repeat"] = repeat_idx
                run_results.append(result)
                all_results.append(result)

                # 收集错误样本（只保留第一次运行的错误）
                if repeat_idx == 0:
                    all_errors_for_config.extend(error_samples)

            # 保存错误样本 / Save error samples (只保存前100个)
            if all_errors_for_config:
                errors_file = output_dir / "results" / f"errors_{dataset_name}_{config_dict['name']}.jsonl"
                with open(errors_file, 'w', encoding='utf-8') as f:
                    for error in all_errors_for_config[:100]:  # 最多保存100个错误样本
                        f.write(json.dumps(error, ensure_ascii=False) + '\n')

            # 计算平均值和标准差 / Calculate mean and std dev
            if run_results:
                import statistics
                metrics_to_avg = ['accuracy', 'unknown_rate', 'error_rate', 'wall_time_s', 'cpu_user_s', 'cpu_sys_s', 'peak_rss_mb', 'names_per_sec']
                avg_result = {
                    "config_name": config_dict['name'],
                    "dataset": dataset_name,
                    "n_records": run_results[0]['n_records']
                }

                for metric in metrics_to_avg:
                    values = [r[metric] for r in run_results]
                    avg_result[f"{metric}_mean"] = statistics.mean(values)
                    avg_result[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0

                all_results.append(avg_result)

    # 保存结果 / Save results
    print("\n保存结果 / Saving results...")

    # CSV格式 / CSV format
    csv_path = output_dir / "results" / "metrics.csv"
    if all_results:
        # 收集所有字段名 / Collect all field names
        all_fieldnames = set()
        for result in all_results:
            all_fieldnames.update(result.keys())
        fieldnames = sorted(all_fieldnames)

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_results)

    # JSON格式 / JSON format
    json_path = output_dir / "results" / "metrics.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n完成！结果保存在 / Done! Results saved in: {output_dir}")
    return str(output_dir)


def main():
    """主函数 / Main function"""
    parser = argparse.ArgumentParser(
        description="论文级可复现实验记录工具 / Paper-Level Reproducible Experiment Recording Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例 / Examples:
  # 运行单个数据集 / Run single dataset
  python -m experiments.run_bench --datasets data/crossref_authors.json

  # 运行多个数据集 / Run multiple datasets
  python -m experiments.run_bench --datasets data/crossref1.json data/crossref2.json

  # 使用消融配置 / Use ablation config
  python -m experiments.run_bench --config experiments/ablation.yaml --datasets data/crossref.json

  # 指定输出目录 / Specify output directory
  python -m experiments.run_bench --datasets data/crossref.json --output runs/my_experiment

  # 旧格式兼容 / Legacy format
  python experiments/run_bench.py data/crossref.json --ablation experiments/ablation.yaml
        """
    )

    # 支持新格式：--datasets
    parser.add_argument(
        '--datasets',
        nargs='+',
        type=str,
        default=None,
        help='数据集文件路径（支持多个）/ Dataset file paths (supports multiple)'
    )

    # 支持新格式：--config（同时保留--ablation作为别名）
    parser.add_argument(
        '--config',
        '--ablation',
        dest='config',
        type=str,
        default=None,
        help='消融实验配置文件路径（YAML格式）/ Ablation config file path (YAML format)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出目录路径（默认：runs/<timestamp>__git-<sha>）/ Output directory path'
    )

    parser.add_argument(
        '--repeats',
        type=int,
        default=3,
        help='重复运行次数（默认：3）/ Number of repeated runs (default: 3)'
    )

    parser.add_argument(
        '--skip-warmup',
        action='store_true',
        help='跳过预热运行 / Skip warmup run'
    )

    # 支持旧格式：位置参数datasets
    parser.add_argument(
        'legacy_datasets',
        nargs='*',
        help=argparse.SUPPRESS  # 隐藏此参数，仅用于兼容性
    )

    args = parser.parse_args()

    # 确定使用哪个datasets参数
    if args.datasets:
        dataset_paths = args.datasets
    elif args.legacy_datasets:
        dataset_paths = args.legacy_datasets
    else:
        parser.error("需要至少一个数据集文件 / At least one dataset file is required. Use --datasets or provide positional arguments.")

    # 运行基准测试 / Run benchmark
    run_benchmark(
        dataset_paths=dataset_paths,
        ablation_config_path=args.config,
        output_dir=args.output,
        n_repeats=args.repeats,
        skip_warmup=args.skip_warmup
    )


if __name__ == "__main__":
    main()
