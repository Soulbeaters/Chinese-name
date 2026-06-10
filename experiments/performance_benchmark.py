# -*- coding: utf-8 -*-
"""
性能基准测试 / Performance Benchmarking

对比带/不带事件追踪的性能差异
Compare performance with/without event tracking instrumentation

作者: Ma Jiaxin
日期: 2025-12-19
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.surname_identifier_v8 import NameRecord, identify_surname_position_v8
from src.config_v8 import set_ablation_config, reset_ablation_config, AblationConfig
from experiments.event_collection import batch_identify_with_event_tracking


def load_records(dataset_path: str) -> List[NameRecord]:
    """
    加载数据集记录 / Load dataset records

    Args:
        dataset_path: 数据集路径

    Returns:
        记录列表
    """
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    for item in data:
        record_id = item.get('record_id', item.get('id', str(len(records))))
        source = item.get('source', 'unknown')
        name_raw = item.get('name', item.get('name_raw', ''))
        affiliation = item.get('affiliation', item.get('affiliation_raw'))

        person_id = item.get('person_id')
        pub_id = item.get('publication_id', item.get('doi'))

        rec = NameRecord(
            record_id=record_id,
            source=source,
            person_id=person_id,
            publication_id=pub_id,
            name_raw=name_raw,
            affiliation_raw=affiliation if affiliation else None
        )
        records.append(rec)

    return records


def benchmark_without_instrumentation(
    records: List[NameRecord],
    config: AblationConfig,
    n_runs: int = 3
) -> Tuple[float, float, int, int]:
    """
    基准测试（无事件追踪）
    Benchmark without event tracking

    使用简单循环调用，不创建事件对象
    Simple loop without creating event objects

    Args:
        records: 记录列表
        config: 消融配置
        n_runs: 运行次数

    Returns:
        (平均时间, 标准差, 成功数, 失败数)
    """
    set_ablation_config(config)

    # Warmup run (不计时)
    warmup_success = 0
    warmup_fail = 0
    for rec in records[:min(100, len(records))]:
        try:
            order, confidence, reason = identify_surname_position_v8(
                original_name=rec.name_raw,
                affiliation=rec.affiliation_raw,
                source=rec.source,
                person_id=rec.person_id,
                publication_id=rec.publication_id
            )
            warmup_success += 1
        except Exception as e:
            warmup_fail += 1

    # Actual benchmark runs
    times = []
    total_success = 0
    total_fail = 0

    for run_idx in range(n_runs):
        start_time = time.perf_counter()

        success_count = 0
        fail_count = 0

        for rec in records:
            try:
                order, confidence, reason = identify_surname_position_v8(
                    original_name=rec.name_raw,
                    affiliation=rec.affiliation_raw,
                    source=rec.source,
                    person_id=rec.person_id,
                    publication_id=rec.publication_id
                )
                success_count += 1
            except Exception as e:
                fail_count += 1

        elapsed = time.perf_counter() - start_time
        times.append(elapsed)

        total_success += success_count
        total_fail += fail_count

    reset_ablation_config()

    avg_time = sum(times) / len(times)
    std_time = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5

    # 返回平均成功/失败数
    avg_success = total_success // n_runs
    avg_fail = total_fail // n_runs

    return avg_time, std_time, avg_success, avg_fail


def benchmark_with_instrumentation(
    records: List[NameRecord],
    config: AblationConfig,
    n_runs: int = 3
) -> Tuple[float, float, int, int]:
    """
    基准测试（带事件追踪）
    Benchmark with event tracking

    Args:
        records: 记录列表
        config: 消融配置
        n_runs: 运行次数

    Returns:
        (平均时间, 标准差, 成功数, 失败数)
    """
    set_ablation_config(config)

    # Warmup run (不计时)
    try:
        batch_identify_with_event_tracking(
            records[:min(100, len(records))],
            enable_person_consistency=config.enable_person_consistency,
            enable_pub_consistency=config.enable_pub_consistency
        )
    except Exception:
        pass

    # Actual benchmark runs
    times = []
    total_success = 0
    total_fail = 0

    for _ in range(n_runs):
        start_time = time.perf_counter()

        try:
            decisions, aggregator = batch_identify_with_event_tracking(
                records,
                enable_person_consistency=config.enable_person_consistency,
                enable_pub_consistency=config.enable_pub_consistency
            )
            success_count = len(decisions)
            fail_count = len(records) - len(decisions)
        except Exception as e:
            success_count = 0
            fail_count = len(records)

        elapsed = time.perf_counter() - start_time
        times.append(elapsed)

        total_success += success_count
        total_fail += fail_count

    reset_ablation_config()

    avg_time = sum(times) / len(times)
    std_time = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5

    # 返回平均成功/失败数
    avg_success = total_success // n_runs
    avg_fail = total_fail // n_runs

    return avg_time, std_time, avg_success, avg_fail


def run_performance_benchmark(
    dataset_path: str,
    output_dir: str,
    n_runs: int = 3
):
    """
    运行性能基准测试 / Run performance benchmark

    Args:
        dataset_path: 数据集路径
        output_dir: 输出目录
        n_runs: 每个配置运行次数
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Performance Benchmark: Instrumentation Overhead")
    print("=" * 80)

    # 加载数据
    print(f"\nLoading dataset: {dataset_path}")
    records = load_records(dataset_path)
    print(f"  Loaded {len(records)} records")

    # 基准配置
    baseline_config = AblationConfig(
        disable_source_prior=False,
        disable_western_exclusion=False,
        disable_batch_consistency=False,
        enable_person_consistency=True,
        enable_pub_consistency=True
    )

    # ========== 无事件追踪 ==========
    print(f"\n[1/2] Benchmarking WITHOUT instrumentation ({n_runs} runs)...")
    avg_time_no_instr, std_time_no_instr, success_no_instr, fail_no_instr = benchmark_without_instrumentation(
        records, baseline_config, n_runs
    )

    throughput_no_instr = len(records) / avg_time_no_instr
    fail_rate_no_instr = fail_no_instr / len(records) * 100

    print(f"  Time: {avg_time_no_instr:.3f} ± {std_time_no_instr:.3f} seconds")
    print(f"  Throughput: {throughput_no_instr:.1f} names/sec")
    print(f"  Success: {success_no_instr}/{len(records)} ({100 * success_no_instr / len(records):.2f}%)")
    print(f"  Failures: {fail_no_instr}/{len(records)} ({fail_rate_no_instr:.2f}%)")

    # ========== 带事件追踪 ==========
    print(f"\n[2/2] Benchmarking WITH instrumentation ({n_runs} runs)...")
    avg_time_with_instr, std_time_with_instr, success_with_instr, fail_with_instr = benchmark_with_instrumentation(
        records, baseline_config, n_runs
    )

    throughput_with_instr = len(records) / avg_time_with_instr
    fail_rate_with_instr = fail_with_instr / len(records) * 100

    print(f"  Time: {avg_time_with_instr:.3f} ± {std_time_with_instr:.3f} seconds")
    print(f"  Throughput: {throughput_with_instr:.1f} names/sec")
    print(f"  Success: {success_with_instr}/{len(records)} ({100 * success_with_instr / len(records):.2f}%)")
    print(f"  Failures: {fail_with_instr}/{len(records)} ({fail_rate_with_instr:.2f}%)")

    # ========== 防假数据校验 / Anti-fake Data Validation ==========
    validation_failed = False
    validation_errors = []

    # Check 1: success_count must be > 0
    if success_no_instr == 0:
        validation_errors.append("CRITICAL: WITHOUT instrumentation success_count=0 (all records failed)")
        validation_failed = True

    if success_with_instr == 0:
        validation_errors.append("CRITICAL: WITH instrumentation success_count=0 (all records failed)")
        validation_failed = True

    # Check 2: fail_rate must be <= 1%
    if fail_rate_no_instr > 1.0:
        validation_errors.append(f"CRITICAL: WITHOUT instrumentation fail_rate={fail_rate_no_instr:.2f}% (>1%)")
        validation_failed = True

    if fail_rate_with_instr > 1.0:
        validation_errors.append(f"CRITICAL: WITH instrumentation fail_rate={fail_rate_with_instr:.2f}% (>1%)")
        validation_failed = True

    # ========== 计算开销 ==========
    if not validation_failed and avg_time_no_instr > 0:
        overhead_percent = (avg_time_with_instr - avg_time_no_instr) / avg_time_no_instr * 100
        slowdown_factor = avg_time_with_instr / avg_time_no_instr
    else:
        overhead_percent = float('nan')
        slowdown_factor = float('nan')

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Dataset: {Path(dataset_path).name}")
    print(f"Records: {len(records)}")
    print(f"Runs per config: {n_runs}")
    print()
    print(f"WITHOUT instrumentation:")
    print(f"  Time: {avg_time_no_instr:.3f} ± {std_time_no_instr:.3f} sec")
    print(f"  Throughput: {throughput_no_instr:.1f} names/sec")
    print(f"  Success/Fail: {success_no_instr}/{fail_no_instr}")
    print()
    print(f"WITH instrumentation:")
    print(f"  Time: {avg_time_with_instr:.3f} ± {std_time_with_instr:.3f} sec")
    print(f"  Throughput: {throughput_with_instr:.1f} names/sec")
    print(f"  Success/Fail: {success_with_instr}/{fail_with_instr}")
    print()

    if not validation_failed:
        print(f"Overhead: {overhead_percent:.2f}%")
        print(f"Slowdown factor: {slowdown_factor:.2f}x")
        print()
        print("[VALIDATION PASSED] Data quality checks OK")
    else:
        print("Overhead: N/A (validation failed)")
        print("Slowdown factor: N/A (validation failed)")
        print()
        print("[VALIDATION FAILED] Data quality checks FAILED:")
        for error in validation_errors:
            print(f"  - {error}")

    # ========== 保存结果 ==========
    results = {
        "dataset": str(dataset_path),
        "n_records": len(records),
        "n_runs": n_runs,
        "validation": {
            "passed": not validation_failed,
            "errors": validation_errors
        },
        "without_instrumentation": {
            "avg_time_sec": avg_time_no_instr,
            "std_time_sec": std_time_no_instr,
            "throughput_names_per_sec": throughput_no_instr,
            "success_count": success_no_instr,
            "fail_count": fail_no_instr,
            "fail_rate_percent": fail_rate_no_instr
        },
        "with_instrumentation": {
            "avg_time_sec": avg_time_with_instr,
            "std_time_sec": std_time_with_instr,
            "throughput_names_per_sec": throughput_with_instr,
            "success_count": success_with_instr,
            "fail_count": fail_with_instr,
            "fail_rate_percent": fail_rate_with_instr
        },
        "overhead": {
            "percent": overhead_percent,
            "slowdown_factor": slowdown_factor
        }
    }

    with open(output_path / "performance_benchmark.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 生成Markdown报告
    with open(output_path / "performance_benchmark.md", 'w', encoding='utf-8') as f:
        f.write("# Performance Benchmark: Instrumentation Overhead\n\n")

        # Validation status header
        if validation_failed:
            f.write("## ⚠️ VALIDATION FAILURE ⚠️\n\n")
            f.write("**This benchmark failed data quality checks. Results are NOT reliable for publication.**\n\n")
            f.write("### Validation Errors:\n\n")
            for error in validation_errors:
                f.write(f"- {error}\n")
            f.write("\n")
        else:
            f.write("## ✅ VALIDATION PASSED\n\n")
            f.write("**All data quality checks passed. Results are reliable.**\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Dataset**: {Path(dataset_path).name}\n")
        f.write(f"- **Records**: {len(records):,}\n")
        f.write(f"- **Runs per config**: {n_runs}\n\n")

        f.write("## Results\n\n")
        f.write("| Configuration | Time (sec) | Throughput (names/sec) | Success/Fail |\n")
        f.write("|--------------|------------|------------------------|-------------|\n")
        f.write(f"| WITHOUT instrumentation | {avg_time_no_instr:.3f} ± {std_time_no_instr:.3f} | {throughput_no_instr:.1f} | {success_no_instr}/{fail_no_instr} ({fail_rate_no_instr:.2f}% fail) |\n")
        f.write(f"| WITH instrumentation | {avg_time_with_instr:.3f} ± {std_time_with_instr:.3f} | {throughput_with_instr:.1f} | {success_with_instr}/{fail_with_instr} ({fail_rate_with_instr:.2f}% fail) |\n\n")

        if not validation_failed:
            f.write("## Overhead\n\n")
            f.write(f"- **Overhead**: {overhead_percent:.2f}%\n")
            f.write(f"- **Slowdown factor**: {slowdown_factor:.2f}x\n\n")

            f.write("## Interpretation\n\n")
            if overhead_percent < 10:
                f.write("The instrumentation overhead is **negligible** (<10%), indicating that event tracking has minimal performance impact.\n")
            elif overhead_percent < 50:
                f.write("The instrumentation overhead is **moderate** (10-50%), which is acceptable for experimental analysis.\n")
            else:
                f.write("The instrumentation overhead is **significant** (>50%). Consider optimizing event tracking if this becomes a bottleneck.\n")
        else:
            f.write("## Overhead\n\n")
            f.write("**Cannot compute overhead due to validation failures.**\n\n")

        f.write("\n## Data Quality Validation\n\n")
        f.write("### Validation Criteria:\n\n")
        f.write("1. Success count must be > 0 (no complete failure)\n")
        f.write("2. Failure rate must be ≤ 1% (allow minimal errors)\n\n")
        f.write(f"### Validation Result: {'❌ FAILED' if validation_failed else '✅ PASSED'}\n\n")

    print(f"\nResults saved to: {output_path}")
    print(f"  - performance_benchmark.json")
    print(f"  - performance_benchmark.md")

    # Return validation status for exit code
    return not validation_failed


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark performance overhead of event tracking instrumentation"
    )
    parser.add_argument("--dataset", required=True, help="Path to dataset JSON file")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per config (default: 3)")

    args = parser.parse_args()

    validation_passed = run_performance_benchmark(
        args.dataset,
        args.output,
        args.runs
    )

    # Exit with non-zero if validation failed
    if not validation_passed:
        print("\n[ERROR] Benchmark validation failed. Exiting with code 1.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Benchmark validation passed. Exiting with code 0.")
        sys.exit(0)


if __name__ == "__main__":
    main()
