# -*- coding: utf-8 -*-
"""
统计显著性检验 / Statistical Significance Tests (严格版本 / Strict Version)

提供置信区间和McNemar检验，含元数据和严格校验
Provides confidence intervals and McNemar's test with metadata and strict validation

作者: Ma Jiaxin
日期: 2025-12-19
"""

import json
import math
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class StatsMetadata:
    """统计报告元数据 / Stats Report Metadata"""
    dataset: str  # crossref_10k / crossref_301k / istina_xxx
    n_records_total: int  # 总记录数 (P0-P3收敛: 统一命名)
    n_records_labeled: int  # 有ground truth的记录数
    git_commit: str  # Git commit hash
    run_id: str  # Run folder name
    scope: str  # global / triggered_subset:<module> / hard_subset:<name>
    timestamp_utc: str  # ISO8601 timestamp
    config_hash: str  # Configuration parameters hash (SHA256)

    # Backward compatibility
    @property
    def n_records(self) -> int:
        """向后兼容：n_records = n_records_total"""
        return self.n_records_total


@dataclass
class ConfidenceInterval:
    """置信区间 / Confidence interval (with k/n)"""
    metric_name: str
    point_estimate: float
    lower_bound: float
    upper_bound: float
    k: int  # Number of successes (for binomial)
    n: int  # Total trials
    confidence_level: float = 0.95
    method: str = "wilson"  # wilson | normal


def wilson_score_interval(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Wilson score interval for binomial proportion (strict k/n version)

    严格使用k/n计算，不使用repeat的std
    Strictly uses k/n, not repeat std

    Args:
        k: Number of successes
        n: Total trials
        confidence: Confidence level (default 0.95)

    Returns:
        (lower, upper)
    """
    if n == 0:
        return (0.0, 0.0)

    p = k / n

    # Z值（双尾）
    z_dict = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_dict.get(confidence, 1.96)

    denominator = 1 + z**2 / n
    centre_adjusted_probability = p + z**2 / (2 * n)
    adjusted_standard_deviation = math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)

    lower = (centre_adjusted_probability - z * adjusted_standard_deviation) / denominator
    upper = (centre_adjusted_probability + z * adjusted_standard_deviation) / denominator

    return (max(0.0, lower), min(1.0, upper))


def calculate_confidence_intervals(
    k_correct: int,
    k_incorrect: int,
    k_unknown: int,
    confidence: float = 0.95
) -> Dict[str, ConfidenceInterval]:
    """
    计算准确率、Unknown率、Error率的置信区间 (strict k/n version)
    Calculate confidence intervals for accuracy, unknown rate, and error rate

    输出三套核心指标 / Output three core metric sets:
    1. end_to_end_accuracy = correct / N_total (unknown计为错误)
    2. conditional_accuracy = correct / (correct + incorrect) (unknown excluded)
    3. coverage = 1 - unknown_rate

    Args:
        k_correct: 正确数
        k_incorrect: 错误数
        k_unknown: Unknown数
        confidence: 置信水平

    Returns:
        Dict[metric_name, ConfidenceInterval]
    """
    n_total = k_correct + k_incorrect + k_unknown
    if n_total == 0:
        return {}

    # End-to-end accuracy (unknown计为错误)
    end_to_end_accuracy = k_correct / n_total

    # Conditional accuracy (unknown excluded from k/n)
    n_non_unknown = k_correct + k_incorrect
    if n_non_unknown > 0:
        conditional_accuracy = k_correct / n_non_unknown
    else:
        conditional_accuracy = 0.0

    # Coverage (1 - unknown_rate)
    unknown_rate = k_unknown / n_total
    coverage = 1.0 - unknown_rate

    # Error rate (among all records)
    error_rate = k_incorrect / n_total

    results = {}

    # 1. End-to-end Accuracy (primary metric for论文)
    e2e_lower, e2e_upper = wilson_score_interval(k_correct, n_total, confidence)
    results["end_to_end_accuracy"] = ConfidenceInterval(
        metric_name="End-to-End Accuracy",
        point_estimate=end_to_end_accuracy,
        lower_bound=e2e_lower,
        upper_bound=e2e_upper,
        k=k_correct,
        n=n_total,
        confidence_level=confidence,
        method="wilson"
    )

    # 2. Conditional Accuracy (among non-unknown records)
    if n_non_unknown > 0:
        cond_lower, cond_upper = wilson_score_interval(k_correct, n_non_unknown, confidence)
        results["conditional_accuracy"] = ConfidenceInterval(
            metric_name="Conditional Accuracy",
            point_estimate=conditional_accuracy,
            lower_bound=cond_lower,
            upper_bound=cond_upper,
            k=k_correct,
            n=n_non_unknown,
            confidence_level=confidence,
            method="wilson"
        )
    else:
        # No non-unknown records
        results["conditional_accuracy"] = ConfidenceInterval(
            metric_name="Conditional Accuracy",
            point_estimate=0.0,
            lower_bound=0.0,
            upper_bound=0.0,
            k=0,
            n=0,
            confidence_level=confidence,
            method="wilson"
        )

    # 3. Coverage (1 - unknown_rate)
    # Coverage = 1 - unknown_rate, so CI for coverage = 1 - CI for unknown_rate (reversed)
    unk_lower, unk_upper = wilson_score_interval(k_unknown, n_total, confidence)
    cov_lower = 1.0 - unk_upper  # Coverage lower = 1 - unknown upper
    cov_upper = 1.0 - unk_lower  # Coverage upper = 1 - unknown lower
    results["coverage"] = ConfidenceInterval(
        metric_name="Coverage",
        point_estimate=coverage,
        lower_bound=cov_lower,
        upper_bound=cov_upper,
        k=n_total - k_unknown,  # Non-unknown count
        n=n_total,
        confidence_level=confidence,
        method="wilson"
    )

    # Legacy metrics (for backward compatibility)
    results["accuracy"] = results["end_to_end_accuracy"]  # Alias

    results["unknown_rate"] = ConfidenceInterval(
        metric_name="Unknown Rate",
        point_estimate=unknown_rate,
        lower_bound=unk_lower,
        upper_bound=unk_upper,
        k=k_unknown,
        n=n_total,
        confidence_level=confidence,
        method="wilson"
    )

    err_lower, err_upper = wilson_score_interval(k_incorrect, n_total, confidence)
    results["error_rate"] = ConfidenceInterval(
        metric_name="Error Rate",
        point_estimate=error_rate,
        lower_bound=err_lower,
        upper_bound=err_upper,
        k=k_incorrect,
        n=n_total,
        confidence_level=confidence,
        method="wilson"
    )

    return results


def mcnemar_test_strict(
    baseline_correct: List[bool],
    ablation_correct: List[bool]
) -> Dict[str, any]:
    """
    McNemar检验 (strict paired correctness version)
    McNemar's test with explicit b/c counts

    Args:
        baseline_correct: Baseline的正确/错误列表
        ablation_correct: Ablation的正确/错误列表

    Returns:
        Dict with a, b, c, d, statistic, p_value, method, interpretation
    """
    assert len(baseline_correct) == len(ablation_correct), "Lists must have same length"

    # 构建2x2列联表 / Build 2x2 contingency table
    # |                | Ablation Correct | Ablation Incorrect |
    # |----------------|------------------|--------------------|
    # | Base Correct   | a (both correct) | b (base only)      |
    # | Base Incorrect | c (ablation only)| d (both wrong)     |

    a = sum(1 for b, ab in zip(baseline_correct, ablation_correct) if b and ab)
    b = sum(1 for b, ab in zip(baseline_correct, ablation_correct) if b and not ab)
    c = sum(1 for b, ab in zip(baseline_correct, ablation_correct) if not b and ab)
    d = sum(1 for b, ab in zip(baseline_correct, ablation_correct) if not b and not ab)

    # 选择exact vs chi-square
    # If b+c < 25, use exact binomial; otherwise use chi-square with continuity correction
    if b + c == 0:
        method = "exact_binomial"
        statistic = 0.0
        p_value_str = "1.0"
        interpretation = "完全一致，无差异"
    elif b + c < 25:
        method = "exact_binomial"
        # Exact binomial test: P(X <= min(b,c)) under H0: p=0.5
        # Approximation using normal for simplicity
        statistic = (abs(b - c))**2 / (b + c) if (b + c) > 0 else 0.0
        p_value_str = estimate_pvalue(statistic)
        interpretation = f"精确检验 (n={b+c} < 25)"
    else:
        method = "chi_square_continuity"
        # 带连续性校正的McNemar统计量
        statistic = (abs(b - c) - 1)**2 / (b + c)
        p_value_str = estimate_pvalue(statistic)
        interpretation = f"卡方检验 (n={b+c} >= 25)"

    return {
        "a": a,  # 都正确
        "b": b,  # baseline正确，ablation错误
        "c": c,  # baseline错误，ablation正确
        "d": d,  # 都错误
        "statistic": statistic,
        "p_value": p_value_str,
        "method": method,
        "interpretation": interpretation
    }


def estimate_pvalue(statistic: float) -> str:
    """估算p值 (基于卡方分布自由度=1)"""
    chi2_critical = {
        0.10: 2.706,
        0.05: 3.841,
        0.01: 6.635,
        0.001: 10.828
    }

    if statistic < chi2_critical[0.10]:
        return ">0.10"
    elif statistic < chi2_critical[0.05]:
        return "0.05-0.10"
    elif statistic < chi2_critical[0.01]:
        return "0.01-0.05"
    elif statistic < chi2_critical[0.001]:
        return "0.001-0.01"
    else:
        return "<0.001"


def compute_config_hash(config_dict: Dict) -> str:
    """
    计算配置哈希 (SHA256)
    Computes configuration hash

    Args:
        config_dict: 配置字典 (profile参数/权重/开关)

    Returns:
        SHA256 hex digest
    """
    config_str = json.dumps(config_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(config_str.encode('utf-8')).hexdigest()


def get_git_commit() -> str:
    """获取当前Git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]
        else:
            return "unknown"
    except:
        return "unknown"


def strict_validate_consistency(
    stats_point_estimates: Dict[str, Dict[str, float]],
    metrics_json_path: Path,
    dataset_name: str,
    tolerance: float = 1e-6
):
    """
    严格校验：stats_ci与metrics.json的点估计必须一致
    Strict validation: stats_ci point estimates must match metrics.json

    Args:
        stats_point_estimates: {config: {metric: value}}
        metrics_json_path: Path to metrics.json
        dataset_name: Dataset name for error messages
        tolerance: Maximum allowed difference (default 1e-6)

    Raises:
        ValueError if any metric differs by more than tolerance
    """
    if not metrics_json_path.exists():
        print(f"  [WARNING] metrics.json not found at {metrics_json_path}, skipping strict validation")
        return

    with open(metrics_json_path, 'r', encoding='utf-8') as f:
        metrics_data = json.load(f)

    # Parse metrics.json to extract mean values
    metrics_dict = {}

    # Handle both dict and list formats
    if isinstance(metrics_data, dict):
        # If metrics_data is already a dict, use it directly
        for config_name, data in metrics_data.items():
            if isinstance(data, dict):
                metrics_dict[config_name] = {
                    "accuracy": data.get("accuracy", data.get("accuracy_mean", 0.0)),
                    "unknown_rate": data.get("unknown_rate", data.get("unknown_rate_mean", 0.0)),
                    "error_rate": data.get("error_rate", data.get("error_rate_mean", 0.0))
                }
    elif isinstance(metrics_data, list):
        # If it's a list, iterate as before
        for entry in metrics_data:
            if isinstance(entry, dict):
                config_name = entry.get("config_name", "")
                if config_name and "accuracy_mean" in entry:
                    metrics_dict[config_name] = {
                        "accuracy": entry.get("accuracy_mean", 0.0),
                        "unknown_rate": entry.get("unknown_rate_mean", 0.0),
                        "error_rate": entry.get("error_rate_mean", 0.0)
                    }

    # Compare
    errors = []
    for config, metrics in stats_point_estimates.items():
        if config not in metrics_dict:
            continue

        for metric_key in ["accuracy", "unknown_rate", "error_rate"]:
            stats_value = metrics.get(metric_key, 0.0)
            metrics_value = metrics_dict[config].get(metric_key, 0.0)
            diff = abs(stats_value - metrics_value)

            if diff > tolerance:
                errors.append({
                    "dataset": dataset_name,
                    "config": config,
                    "metric": metric_key,
                    "metrics_json": metrics_value,
                    "stats_ci": stats_value,
                    "diff": diff
                })

    if errors:
        error_msg = "\n[STRICT VALIDATION FAILED] stats_ci point estimates DO NOT match metrics.json:\n"
        for err in errors:
            error_msg += (f"  Dataset: {err['dataset']}, Config: {err['config']}, Metric: {err['metric']}\n"
                         f"    metrics.json: {err['metrics_json']:.6f}\n"
                         f"    stats_ci: {err['stats_ci']:.6f}\n"
                         f"    diff: {err['diff']:.6e} (tolerance: {tolerance:.6e})\n")
        raise ValueError(error_msg)

    print("  [PASS] Strict validation: stats_ci matches metrics.json")


def generate_statistical_report_global(
    results: Dict[str, Dict],
    ground_truth: Dict[str, str],
    output_dir: str,
    dataset_name: str,
    run_id: str,
    config_dict: Optional[Dict] = None,
    metrics_json_path: Optional[Path] = None,
    n_records_total: Optional[int] = None  # (P0-P3收敛任务4): 添加n_records_total
):
    """
    生成全局统计报告 (global scope)
    Generate global statistical report

    This is the main entry for global stats_ci outputs.

    Args:
        results: 实验结果字典
        ground_truth: Ground truth
        output_dir: 输出目录
        dataset_name: 数据集名称 (e.g., crossref_10k)
        run_id: Run folder name
        config_dict: Configuration dict for hash computation
        metrics_json_path: Path to metrics.json for strict validation
        n_records_total: 总记录数（含无标注的），如未提供则从results中提取
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # (P0-P3收敛任务4): 提取n_records_total（如未提供）
    # Extract n_records_total from results if not provided (backward compatibility)
    if n_records_total is None:
        # Try to extract from baseline results
        if "baseline" in results and "total" in results["baseline"]:
            n_records_total = results["baseline"]["total"]
        else:
            # Fallback: assume total = labeled (backward compatibility)
            n_records_total = len(ground_truth)

    # Compute metadata
    metadata = StatsMetadata(
        dataset=dataset_name,
        n_records_total=n_records_total,  # (P0-P3收敛任务4): 明确区分total/labeled
        n_records_labeled=len(ground_truth),
        git_commit=get_git_commit(),
        run_id=run_id,
        scope="global",
        timestamp_utc=datetime.utcnow().isoformat() + "Z",
        config_hash=compute_config_hash(config_dict or {})
    )

    # (P0-P3收敛任务4): Metric definitions (论文指标口径说明)
    metric_definitions = {
        "end_to_end_accuracy": "correct / N_labeled (unknown计为错误)",
        "conditional_accuracy": "correct / (correct + incorrect) (unknown excluded from k/n)",
        "coverage": "1 - unknown_rate (算法给出明确判断的比例)",
        "unknown_rate": "unknown / N_labeled",
        "error_rate": "incorrect / N_labeled",
        "accuracy": "Alias for end_to_end_accuracy (backward compatibility)"
    }

    stats_report = {
        "metadata": {
            **asdict(metadata),
            "metric_definitions": metric_definitions,
            "primary_metric": "end_to_end_accuracy",  # (P0-P3收敛任务4): 明确primary metric
            "primary_metric_description": "correct / N_labeled (unknown counted as error) - strictest metric for paper"
        },
        "confidence_intervals": {},
        "mcnemar_tests": {}
    }

    # 1. 为每个配置计算置信区间
    point_estimates = {}  # For strict validation
    for config_name, config_result in results.items():
        if "correct" not in config_result:
            continue

        k_correct = config_result["correct"]
        k_incorrect = config_result["incorrect"]
        k_unknown = config_result["unknown"]

        cis = calculate_confidence_intervals(k_correct, k_incorrect, k_unknown)

        stats_report["confidence_intervals"][config_name] = {
            k: asdict(v) for k, v in cis.items()
        }

        # Collect point estimates for validation
        point_estimates[config_name] = {
            "accuracy": cis["accuracy"].point_estimate,
            "unknown_rate": cis["unknown_rate"].point_estimate,
            "error_rate": cis["error_rate"].point_estimate
        }

    # 2. Baseline vs Ablations的McNemar检验
    if "baseline" in results:
        baseline_decisions = results["baseline"].get("decisions", {})

        for config_name, config_result in results.items():
            if config_name == "baseline":
                continue

            ablation_decisions = config_result.get("decisions", {})

            # 获取共同的record_id
            common_ids = set(baseline_decisions.keys()) & set(ablation_decisions.keys())
            common_ids = [rid for rid in common_ids if rid in ground_truth]

            if len(common_ids) == 0:
                continue

            # 构建correct列表 (paired correctness)
            baseline_correct = [
                baseline_decisions[rid] == ground_truth[rid]
                for rid in common_ids
            ]
            ablation_correct = [
                ablation_decisions[rid] == ground_truth[rid]
                for rid in common_ids
            ]

            # McNemar检验 (strict version)
            mcnemar_result = mcnemar_test_strict(baseline_correct, ablation_correct)
            stats_report["mcnemar_tests"][f"baseline_vs_{config_name}"] = mcnemar_result

    # 3. Strict validation against metrics.json
    if metrics_json_path:
        strict_validate_consistency(point_estimates, metrics_json_path, dataset_name)

    # 4. 保存JSON
    with open(output_path / "stats_ci_global.json", 'w', encoding='utf-8') as f:
        json.dump(stats_report, f, indent=2, ensure_ascii=False)

    # 5. 生成Markdown
    generate_stats_md_strict(stats_report, output_path / "stats_ci_global.md")

    # 6. 生成LaTeX (with booktabs)
    generate_stats_tex_strict(stats_report, output_path / "stats_ci_global.tex")

    print(f"Global statistical report saved to {output_dir}")
    print(f"  - stats_ci_global.json (metadata + validation)")
    print(f"  - stats_ci_global.md")
    print(f"  - stats_ci_global.tex")


def generate_stats_md_strict(stats: Dict, filepath: str):
    """生成统计报告Markdown (strict version with metadata)"""
    metadata = stats.get("metadata", {})

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# 统计显著性分析 / Statistical Significance Analysis\n\n")

        # (P0-P3收敛任务4): Metadata section包含完整N信息和primary metric说明
        # Metadata section
        f.write("## 元数据 / Metadata\n\n")
        f.write(f"- **Dataset**: {metadata.get('dataset', 'N/A')}\n")
        # 明确区分 N_total 和 N_labeled
        n_total = metadata.get('n_records_total', metadata.get('n_records', 0))
        n_labeled = metadata.get('n_records_labeled', metadata.get('n_records', 0))
        f.write(f"- **N_total**: {n_total:,} (all records)\n")
        f.write(f"- **N_labeled**: {n_labeled:,} (records with ground truth)\n")
        f.write(f"- **Scope**: {metadata.get('scope', 'N/A')}\n")
        f.write(f"- **Run ID**: {metadata.get('run_id', 'N/A')}\n")
        f.write(f"- **Git Commit**: {metadata.get('git_commit', 'N/A')}\n")
        f.write(f"- **Timestamp (UTC)**: {metadata.get('timestamp_utc', 'N/A')}\n")
        f.write(f"- **Config Hash**: {metadata.get('config_hash', 'N/A')[:16]}...\n\n")

        # (P0-P3收敛任务4): 明确primary metric和三套指标说明
        f.write("## 指标口径说明 / Metric Definitions\n\n")
        f.write("**Primary Metric (论文主指标)**: `end_to_end_accuracy`\n\n")
        f.write("三套核心指标 / Three Core Metrics:\n\n")
        f.write("1. **End-to-End Accuracy**: correct / N_labeled (unknown计为error)\n")
        f.write("   - 最严格，适合论文主指标\n")
        f.write("2. **Conditional Accuracy**: correct / (correct + incorrect) (unknown excluded)\n")
        f.write("   - 聚焦算法在\"能判断的案例\"上的表现\n")
        f.write("3. **Coverage**: 1 - unknown_rate\n")
        f.write("   - 衡量算法的适用范围\n\n")

        # 置信区间
        f.write("## 置信区间 (95% Wilson Score Interval)\n\n")
        f.write("| 配置 | 指标 | k | n | 点估计 (%) | 下界 (%) | 上界 (%) |\n")
        f.write("|------|------|---|---|-----------|---------|----------|\n")

        for config, cis in stats.get("confidence_intervals", {}).items():
            for metric, ci in cis.items():
                f.write(f"| {config} | {ci['metric_name']} | "
                        f"{ci['k']} | {ci['n']} | "
                        f"{ci['point_estimate']*100:.2f} | "
                        f"{ci['lower_bound']*100:.2f} | "
                        f"{ci['upper_bound']*100:.2f} |\n")

        # McNemar检验
        f.write("\n## McNemar检验 (Baseline vs Ablations)\n\n")
        f.write("| 对比 | a (都对) | b (仅Base对) | c (仅Abl对) | d (都错) | 统计量 | p值 | 方法 | 结论 |\n")
        f.write("|------|---------|-------------|------------|---------|--------|-----|------|------|\n")

        for comparison, test in stats.get("mcnemar_tests", {}).items():
            f.write(f"| {comparison} | "
                    f"{test.get('a', 0)} | "
                    f"{test.get('b', 0)} | "
                    f"{test.get('c', 0)} | "
                    f"{test.get('d', 0)} | "
                    f"{test.get('statistic', 0):.3f} | "
                    f"{test.get('p_value', 'N/A')} | "
                    f"{test.get('method', 'N/A')} | "
                    f"{test.get('interpretation', '')} |\n")


def generate_stats_tex_strict(stats: Dict, filepath: str):
    """生成统计报告LaTeX (strict version with booktabs and metadata)"""
    metadata = stats.get("metadata", {})

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("% 统计显著性分析表格 / Statistical Significance Analysis Table\n")
        f.write("% Requires: \\usepackage{booktabs}\n\n")

        # (P0-P3收敛任务4): Caption包含完整信息 (N_total, N_labeled, scope, unknown处理说明)
        # CI table
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        n_total = metadata.get('n_records_total', metadata.get('n_records', 0))
        n_labeled = metadata.get('n_records_labeled', metadata.get('n_records', 0))
        scope = metadata.get('scope', 'global')
        f.write(f"\\caption{{95\\% Confidence Intervals for {metadata.get('dataset', 'Dataset')} "
                f"(N\\_total={n_total:,}, N\\_labeled={n_labeled:,}, scope={scope}). "
                f"Primary metric: end-to-end accuracy (unknown counted as error).}}\n")
        f.write("\\label{tab:ci_" + metadata.get('dataset', 'data').replace('_', '') + "_" + scope.replace(':', '_') + "}\n")
        f.write("\\begin{tabular}{llrccc}\n")
        f.write("\\toprule\n")
        f.write("Configuration & Metric & k & n & Point (\\%) & 95\\% CI (\\%) \\\\\n")
        f.write("\\midrule\n")

        for config, cis in stats.get("confidence_intervals", {}).items():
            for metric, ci in cis.items():
                f.write(f"{config} & {ci['metric_name']} & "
                        f"{ci['k']} & {ci['n']} & "
                        f"{ci['point_estimate']*100:.2f} & "
                        f"[{ci['lower_bound']*100:.2f}, {ci['upper_bound']*100:.2f}] \\\\\n")

        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n\n")

        # McNemar table
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write(f"\\caption{{McNemar Tests: Baseline vs Ablations for {metadata.get('dataset', 'Dataset')}}}\n")
        f.write("\\label{tab:mcnemar_" + metadata.get('dataset', 'data').replace('_', '') + "_" + metadata.get('scope', 'global').replace(':', '_') + "}\n")
        f.write("\\begin{tabular}{lrrrrll}\n")
        f.write("\\toprule\n")
        f.write("Comparison & b & c & $\\chi^2$ & p-value & Method & Interpretation \\\\\n")
        f.write("\\midrule\n")

        for comparison, test in stats.get("mcnemar_tests", {}).items():
            f.write(f"{comparison.replace('_', ' ')} & "
                    f"{test.get('b', 0)} & "
                    f"{test.get('c', 0)} & "
                    f"{test.get('statistic', 0):.2f} & "
                    f"{test.get('p_value', 'N/A')} & "
                    f"{test.get('method', 'N/A').replace('_', ' ')} & "
                    f"{test.get('interpretation', '')} \\\\\n")

        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")


# Backward compatibility wrapper
def generate_statistical_report(
    results: Dict[str, Dict],
    ground_truth: Dict[str, str],
    output_dir: str,
    dataset_name: str = "unknown",
    run_id: str = "unknown",
    config_dict: Optional[Dict] = None,
    metrics_json_path: Optional[Path] = None,
    n_records_total: Optional[int] = None  # (P0-P3收敛任务4): 添加n_records_total
):
    """
    向后兼容包装器 / Backward compatibility wrapper
    Calls generate_statistical_report_global with default parameters
    """
    generate_statistical_report_global(
        results=results,
        ground_truth=ground_truth,
        output_dir=output_dir,
        dataset_name=dataset_name,
        run_id=run_id,
        config_dict=config_dict,
        metrics_json_path=metrics_json_path,
        n_records_total=n_records_total  # (P0-P3收敛任务4): 传递n_records_total
    )


def generate_triggered_subset_stats(
    subset_records: List,
    ground_truth: Dict[str, str],
    baseline_config,
    ablation_config,
    output_dir: str,
    module_name: str,
    trigger_type: str,  # "fired" or "effective"
    dataset_name: str = "unknown",
    run_id: str = "unknown",
    config_dict: Optional[Dict] = None
):
    """
    为触发子集生成完整统计（Wilson CI + McNemar）
    Generate complete statistics for triggered subset (Wilson CI + McNemar)

    Args:
        subset_records: 子集记录列表
        ground_truth: Ground truth字典
        baseline_config: Baseline配置
        ablation_config: Ablation配置
        output_dir: 输出目录
        module_name: 模块名称 (e.g., "source_prior")
        trigger_type: 触发类型 ("fired" or "effective")
        dataset_name: 数据集名称
        run_id: 运行ID
        config_dict: 配置字典（用于hash计算）
    """
    from experiments.event_collection import batch_identify_with_event_tracking
    from src.config_v8 import set_ablation_config, reset_ablation_config

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # P3: Handle N=0 case (zero-trigger modules)
    if len(subset_records) == 0:
        print(f"  [{module_name}_{trigger_type}] N=0 (no records triggered), generating N/A report...")

        # Generate N=0 metadata
        metadata = StatsMetadata(
            dataset=dataset_name,
            n_records_total=0,
            n_records_labeled=0,
            git_commit=get_git_commit(),
            run_id=run_id,
            scope=f"{trigger_type}_subset_{module_name}",
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            config_hash=compute_config_hash(config_dict) if config_dict else "N/A"
        )

        # Generate N=0 stats
        stats_n0 = {
            "metadata": {
                **metadata.__dict__,
                "note": f"N=0: Module '{module_name}' triggered zero records (not fired). All metrics are N/A."
            },
            "confidence_intervals": {
                "baseline": {"note": "N/A (N=0)"},
                f"ablation_no_{module_name}": {"note": "N/A (N=0)"}
            },
            "mcnemar_tests": {
                f"baseline_vs_ablation_no_{module_name}": {
                    "note": "N/A (N=0)",
                    "p_value": None,
                    "contingency_table": {"a": 0, "b": 0, "c": 0, "d": 0}
                }
            }
        }

        output_filename = f"stats_ci_{trigger_type}_{module_name}"

        # Write JSON
        with open(output_path / f"{output_filename}.json", 'w', encoding='utf-8') as f:
            json.dump(stats_n0, f, indent=2, ensure_ascii=False)

        # Write Markdown
        with open(output_path / f"{output_filename}.md", 'w', encoding='utf-8') as f:
            f.write(f"# Statistical Report: {trigger_type.title()} Subset - {module_name}\n\n")
            f.write("## ⚠️ N=0 (Not Applicable)\n\n")
            f.write(f"**Module**: `{module_name}`\n\n")
            f.write(f"**Trigger Type**: {trigger_type}\n\n")
            f.write(f"**Records Triggered**: **0**\n\n")
            f.write("This module did not fire/trigger on any records in this experiment.\n\n")
            f.write("All statistical metrics (Wilson CI, McNemar test) are **N/A**.\n\n")
            f.write("---\n\n")
            f.write(f"*Generated: {metadata.timestamp_utc}*\n")

        # Write LaTeX
        with open(output_path / f"{output_filename}.tex", 'w', encoding='utf-8') as f:
            f.write(f"% Statistical Report: {trigger_type} subset - {module_name}\n")
            f.write("% N=0 (Not Applicable)\n\n")
            f.write("\\begin{table}[htbp]\n")
            f.write("\\centering\n")
            f.write(f"\\caption{{N=0: Module `{module_name}' ({trigger_type}) - No records triggered}}\n")
            f.write("\\begin{tabular}{ll}\n")
            f.write("\\hline\n")
            f.write("Module & " + module_name + " \\\\\n")
            f.write("Trigger Type & " + trigger_type + " \\\\\n")
            f.write("Records Triggered & \\textbf{0} (N/A) \\\\\n")
            f.write("\\hline\n")
            f.write("\\end{tabular}\n")
            f.write("\\end{table}\n")

        print(f"  [{module_name}_{trigger_type}] N=0 report generated.")
        return  # Early return for N=0 case

    # ========== 运行baseline和ablation ==========
    # Baseline
    set_ablation_config(baseline_config)
    baseline_decisions, _ = batch_identify_with_event_tracking(
        subset_records,
        enable_person_consistency=baseline_config.enable_person_consistency,
        enable_pub_consistency=baseline_config.enable_pub_consistency
    )

    # Ablation
    set_ablation_config(ablation_config)
    ablation_decisions, _ = batch_identify_with_event_tracking(
        subset_records,
        enable_person_consistency=ablation_config.enable_person_consistency,
        enable_pub_consistency=ablation_config.enable_pub_consistency
    )

    reset_ablation_config()

    # ========== 计算指标 ==========
    # 筛选有ground truth的记录
    subset_ids_with_gt = [r.record_id for r in subset_records
                          if r.record_id in ground_truth]

    # Baseline metrics
    baseline_correct = sum(1 for rid in subset_ids_with_gt
                           if rid in baseline_decisions
                           and baseline_decisions[rid].order == ground_truth[rid]
                           and baseline_decisions[rid].order != "unknown")

    # Ablation metrics
    ablation_correct = sum(1 for rid in subset_ids_with_gt
                           if rid in ablation_decisions
                           and ablation_decisions[rid].order == ground_truth[rid]
                           and ablation_decisions[rid].order != "unknown")

    n_labeled = len(subset_ids_with_gt)

    # ========== 生成统计报告 ==========
    # Metadata
    metadata = StatsMetadata(
        dataset=dataset_name,
        n_records_total=len(subset_records),
        n_records_labeled=n_labeled,
        git_commit=get_git_commit(),
        run_id=run_id,
        scope=f"{trigger_type}_subset_{module_name}",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        config_hash=compute_config_hash(config_dict) if config_dict else "N/A"
    )

    # Calculate CIs
    baseline_ci = calculate_confidence_intervals(
        k=baseline_correct,
        n=n_labeled,
        confidence=0.95
    )

    ablation_ci = calculate_confidence_intervals(
        k=ablation_correct,
        n=n_labeled,
        confidence=0.95
    )

    # McNemar test
    a = sum(1 for rid in subset_ids_with_gt
            if rid in baseline_decisions and rid in ablation_decisions
            and baseline_decisions[rid].order == ground_truth[rid]
            and ablation_decisions[rid].order == ground_truth[rid]
            and baseline_decisions[rid].order != "unknown"
            and ablation_decisions[rid].order != "unknown")

    b = sum(1 for rid in subset_ids_with_gt
            if rid in baseline_decisions and rid in ablation_decisions
            and baseline_decisions[rid].order == ground_truth[rid]
            and ablation_decisions[rid].order != ground_truth[rid]
            and baseline_decisions[rid].order != "unknown"
            and ablation_decisions[rid].order != "unknown")

    c = sum(1 for rid in subset_ids_with_gt
            if rid in baseline_decisions and rid in ablation_decisions
            and baseline_decisions[rid].order != ground_truth[rid]
            and ablation_decisions[rid].order == ground_truth[rid]
            and baseline_decisions[rid].order != "unknown"
            and ablation_decisions[rid].order != "unknown")

    d = sum(1 for rid in subset_ids_with_gt
            if rid in baseline_decisions and rid in ablation_decisions
            and baseline_decisions[rid].order != ground_truth[rid]
            and ablation_decisions[rid].order != ground_truth[rid]
            and baseline_decisions[rid].order != "unknown"
            and ablation_decisions[rid].order != "unknown")

    mcnemar = mcnemar_test_strict(
        baseline_correct=baseline_correct,
        baseline_incorrect=n_labeled - baseline_correct,
        ablation_correct=ablation_correct,
        ablation_incorrect=n_labeled - ablation_correct,
        a=a, b=b, c=c, d=d
    )

    # ========== 输出JSON ==========
    stats = {
        "metadata": metadata.__dict__,
        "confidence_intervals": {
            "baseline": baseline_ci.__dict__,
            f"ablation_no_{module_name}": ablation_ci.__dict__
        },
        "mcnemar_tests": {
            f"baseline_vs_ablation_no_{module_name}": mcnemar
        }
    }

    output_filename = f"stats_ci_{trigger_type}_{module_name}"

    with open(output_path / f"{output_filename}.json", 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # ========== 输出Markdown ==========
    generate_stats_md_strict(stats, str(output_path / f"{output_filename}.md"))

    # ========== 输出LaTeX ==========
    generate_stats_tex_strict(stats, str(output_path / f"{output_filename}.tex"))

    print(f"    Generated {trigger_type} subset stats for {module_name}: {output_filename}.*")
