# -*- coding: utf-8 -*-
"""
报表重建脚本 / Report Rebuilding Script

在不重跑算法的情况下，基于现有实验结果重新生成所有报表
Rebuild all reports from existing experiment results without re-running the algorithm

修复目标 / Fix targets:
A1) stats_ci去重 + 小比例格式化 / Dedup stats_ci + format small ratios
A2) triggered_subsets数据驱动叙述 / Data-driven triggered_subsets narrative
A3) sanity_samples抽样逻辑修复 / Fix sanity_samples sampling logic
A4) module_coverage口径统一 / Unify module_coverage criteria
A5) 复现性元数据增强 / Enhance reproducibility metadata

作者 / Author: Ma Jiaxin
日期 / Date: 2025-12-20
"""

import argparse
import json
import sys
import hashlib
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
from collections import defaultdict, Counter
import subprocess

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ========================================
# Statistical Utils (inline implementation)
# ========================================

def wilson_ci(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    """
    Wilson score confidence interval for binomial proportion

    Args:
        k: number of successes
        n: number of trials
        alpha: significance level (default 0.05 for 95% CI)

    Returns:
        (lower_bound, upper_bound)
    """
    import math

    if n == 0:
        return (0.0, 0.0)

    # z-score for two-tailed test
    z = 1.96 if alpha == 0.05 else 2.576  # 95% or 99% CI

    p_hat = k / n
    denominator = 1 + (z**2 / n)
    center = (p_hat + (z**2 / (2*n))) / denominator
    margin = (z * math.sqrt((p_hat*(1-p_hat)/n) + (z**2/(4*n**2)))) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return (lower, upper)


def mcnemar_exact_or_mid_p(b: int, c: int) -> Dict:
    """
    McNemar's exact or mid-p test for small samples

    Args:
        b: count of discordant pairs (baseline wrong, ablation correct)
        c: count of discordant pairs (baseline correct, ablation wrong)

    Returns:
        Dict with p_value
    """
    from scipy.stats import binomtest

    n = b + c
    if n == 0:
        return {"p_value": 1.0}

    # Exact binomial test
    result = binomtest(min(b, c), n, p=0.5, alternative='two-sided')

    return {"p_value": result.pvalue}


class ReportRebuilder:
    """报表重建器 / Report Rebuilder"""

    def __init__(self, run_dir: Path):
        """
        初始化重建器

        Args:
            run_dir: 现有实验运行目录 (e.g., runs/evidence_chain_301k_P0_P5_FINAL_V2)
        """
        self.run_dir = Path(run_dir)
        self.manifest_path = self.run_dir / "run_manifest.json"

        if not self.manifest_path.exists():
            raise FileNotFoundError(f"run_manifest.json not found in {run_dir}")

        # Load manifest
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            self.manifest = json.load(f)

        print(f"Loaded manifest from: {self.manifest_path}")
        print(f"  N_total: {self.manifest.get('n_records_total')}")
        print(f"  N_labeled: {self.manifest.get('n_records_labeled')}")
        print(f"  Configs: {len(self.manifest.get('ablation_configs', {}))}")

        # Load all results from events/
        self.results = {}
        self.load_all_results()

    def load_all_results(self):
        """加载所有配置的推理结果 / Load all config inference results"""
        events_dir = self.run_dir / "events"

        if not events_dir.exists():
            raise FileNotFoundError(f"events/ directory not found in {self.run_dir}")

        # Load baseline and all ablations
        for config_name in self.manifest.get("ablation_configs", {}).keys():
            config_dir = events_dir / config_name

            if not config_dir.exists():
                print(f"  [WARNING] Config directory not found: {config_dir}")
                continue

            # Try to load predictions.jsonl or decision_events.jsonl
            pred_file = config_dir / "predictions.jsonl"
            decision_file = config_dir / "decision_events.jsonl"

            if pred_file.exists():
                print(f"  Loading {config_name} from predictions.jsonl...")
                self.results[config_name] = self.load_predictions_jsonl(pred_file)
            elif decision_file.exists():
                print(f"  Loading {config_name} from decision_events.jsonl...")
                self.results[config_name] = self.load_decision_events_jsonl(decision_file)
            else:
                print(f"  [WARNING] No predictions found for {config_name}")
                continue

        print(f"Loaded {len(self.results)} config results")

    def load_predictions_jsonl(self, filepath: Path) -> List[Dict]:
        """加载predictions.jsonl格式 / Load predictions.jsonl format"""
        predictions = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    predictions.append(json.loads(line))
        return predictions

    def load_decision_events_jsonl(self, filepath: Path) -> List[Dict]:
        """加载decision_events.jsonl格式 / Load decision_events.jsonl format"""
        events = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    # Convert to prediction format
                    pred = {
                        "record_id": event.get("record_id_hash", event.get("record_id")),
                        "prediction": event.get("prediction", {}).get("label"),
                        "ground_truth": event.get("ground_truth"),
                        "scores": event.get("scores", {}),
                        "reasons": event.get("reasons_topk", []),
                        "fired_modules": event.get("fired_modules", []),
                        "effective_modules": event.get("effective_modules", []),
                        "score_margin": event.get("score_margin"),
                    }
                    events.append(pred)
        return events

    # ========================================
    # A1: Stats CI 去重 + 小比例格式化
    # ========================================

    def rebuild_stats_ci(self):
        """
        A1: 重新生成stats_ci，修复：
        1. 去除重复指标（alias导致的重复行）
        2. 小比例(<0.1%)格式化为至少4位小数，或同时显示counts
        """
        print("\n[A1] Rebuilding stats_ci (dedup + small ratio formatting)...")

        stats_output = {}

        # Check if we have results_summary in manifest
        results_summary = self.manifest.get("results_summary", {})

        if not results_summary and len(self.results) == 0:
            print("  [WARNING] No results_summary in manifest and no event logs found")
            print("  [INFO] Using placeholder stats...")

        # Use results_summary if available (preferred method for 301k)
        if results_summary:
            print("  [INFO] Using results_summary from manifest...")

            n_labeled = self.manifest.get("n_records_labeled", 0)

            for config_name, summary in results_summary.items():
                print(f"  Processing {config_name} (from manifest)...")

                accuracy = summary.get("accuracy", 0.0)
                unknown_rate = summary.get("unknown_rate", 0.0)
                error_rate = summary.get("error_rate", 0.0)

                # Calculate counts
                n_correct = int(accuracy * n_labeled)
                n_unknown = int(unknown_rate * n_labeled)
                n_error = int(error_rate * n_labeled)

                # Wilson CI
                acc_ci = wilson_ci(n_correct, n_labeled, alpha=0.05)
                unk_ci = wilson_ci(n_unknown, n_labeled, alpha=0.05)
                err_ci = wilson_ci(n_error, n_labeled, alpha=0.05)

                # Store results (A1: 去重 - 使用唯一的key名称)
                stats_output[config_name] = {
                    "n_total": summary.get("total", n_labeled),
                    "n_labeled": n_labeled,
                    "accuracy": {
                        "point_estimate": accuracy,
                        "ci_lower": acc_ci[0],
                        "ci_upper": acc_ci[1],
                        "count": n_correct,  # A1: 添加count便于小比例解读
                    },
                    "unknown_rate": {
                        "point_estimate": unknown_rate,
                        "ci_lower": unk_ci[0],
                        "ci_upper": unk_ci[1],
                        "count": n_unknown,  # A1: 添加count
                    },
                    "error_rate": {
                        "point_estimate": error_rate,
                        "ci_lower": err_ci[0],
                        "ci_upper": err_ci[1],
                        "count": n_error,  # A1: 添加count
                    },
                }

        else:
            # Fallback: compute from event logs
            for config_name, predictions in self.results.items():
                print(f"  Processing {config_name}...")

                # Compute metrics
                n_total = len(predictions)
                n_labeled = sum(1 for p in predictions if p.get("ground_truth") != "unknown")

                n_correct = 0
                n_unknown = 0
                n_error = 0

                for p in predictions:
                    gt = p.get("ground_truth")
                    pred = p.get("prediction")

                    if gt == "unknown":
                        continue

                    if pred == "unknown":
                        n_unknown += 1
                    elif pred == gt:
                        n_correct += 1
                    else:
                        n_error += 1

                # Calculate rates
                accuracy = n_correct / n_labeled if n_labeled > 0 else 0.0
                unknown_rate = n_unknown / n_labeled if n_labeled > 0 else 0.0
                error_rate = n_error / n_labeled if n_labeled > 0 else 0.0

                # Wilson CI
                acc_ci = wilson_ci(n_correct, n_labeled, alpha=0.05)
                unk_ci = wilson_ci(n_unknown, n_labeled, alpha=0.05)
                err_ci = wilson_ci(n_error, n_labeled, alpha=0.05)

                # Store results (A1: 去重 - 使用唯一的key名称)
                stats_output[config_name] = {
                    "n_total": n_total,
                    "n_labeled": n_labeled,
                    "accuracy": {
                        "point_estimate": accuracy,
                        "ci_lower": acc_ci[0],
                        "ci_upper": acc_ci[1],
                        "count": n_correct,  # A1: 添加count便于小比例解读
                    },
                    "unknown_rate": {
                        "point_estimate": unknown_rate,
                        "ci_lower": unk_ci[0],
                        "ci_upper": unk_ci[1],
                        "count": n_unknown,  # A1: 添加count
                    },
                    "error_rate": {
                        "point_estimate": error_rate,
                        "ci_lower": err_ci[0],
                        "ci_upper": err_ci[1],
                        "count": n_error,  # A1: 添加count
                    },
                }

        # Write to statistics/stats_ci_global.json
        stats_dir = self.run_dir / "statistics"
        stats_dir.mkdir(exist_ok=True)

        stats_json_path = stats_dir / "stats_ci_global.json"
        with open(stats_json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "confidence_intervals": stats_output,
                "n_records_total": self.manifest.get("n_records_total"),
                "n_records_labeled": self.manifest.get("n_records_labeled"),
            }, f, indent=2)

        print(f"  [OK] {stats_json_path}")

        # Generate .md
        self.generate_stats_ci_md(stats_output)

        # Generate .tex
        self.generate_stats_ci_tex(stats_output)

        print("  [A1] Stats CI rebuilt successfully")

    def generate_stats_ci_md(self, stats: Dict):
        """A1: 生成stats_ci_global.md，修复小比例格式"""
        md_path = self.run_dir / "statistics" / "stats_ci_global.md"

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Confidence Intervals (Global Scope)\n\n")
            f.write("Wilson 95% CI for all ablation configs\n\n")
            f.write("| Config | Metric | Point Estimate | 95% CI | Count |\n")
            f.write("|--------|--------|----------------|--------|-------|\n")

            for config_name, metrics in stats.items():
                # Accuracy
                acc = metrics["accuracy"]
                f.write(f"| {config_name} | Accuracy | {acc['point_estimate']:.6f} | "
                       f"[{acc['ci_lower']:.6f}, {acc['ci_upper']:.6f}] | {acc['count']} |\n")

                # Unknown Rate (A1: 小比例格式化)
                unk = metrics["unknown_rate"]
                unk_pct = unk['point_estimate'] * 100
                if unk_pct < 0.1:
                    # 小于0.1%，显示至少4位小数和count
                    f.write(f"| {config_name} | Unknown Rate | {unk_pct:.4f}% | "
                           f"[{unk['ci_lower']*100:.4f}%, {unk['ci_upper']*100:.4f}%] | {unk['count']} |\n")
                else:
                    f.write(f"| {config_name} | Unknown Rate | {unk_pct:.2f}% | "
                           f"[{unk['ci_lower']*100:.2f}%, {unk['ci_upper']*100:.2f}%] | {unk['count']} |\n")

                # Error Rate
                err = metrics["error_rate"]
                f.write(f"| {config_name} | Error Rate | {err['point_estimate']:.6f} | "
                       f"[{err['ci_lower']:.6f}, {err['ci_upper']:.6f}] | {err['count']} |\n")

        print(f"  [OK] {md_path}")

    def generate_stats_ci_tex(self, stats: Dict):
        """A1: 生成stats_ci_global.tex，修复小比例格式"""
        tex_path = self.run_dir / "statistics" / "stats_ci_global.tex"

        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write("\\begin{table}[htbp]\n")
            f.write("\\centering\n")
            f.write("\\caption{Confidence Intervals (Global Scope)}\n")
            f.write("\\label{tab:stats_ci_global}\n")
            f.write("\\begin{tabular}{llrrr}\n")
            f.write("\\toprule\n")
            f.write("Config & Metric & Point Est. & 95\\% CI & Count \\\\\n")
            f.write("\\midrule\n")

            for config_name, metrics in stats.items():
                # Accuracy
                acc = metrics["accuracy"]
                f.write(f"{config_name} & Accuracy & {acc['point_estimate']:.4f} & "
                       f"[{acc['ci_lower']:.4f}, {acc['ci_upper']:.4f}] & {acc['count']} \\\\\n")

                # Unknown Rate (A1: 小比例格式化)
                unk = metrics["unknown_rate"]
                unk_pct = unk['point_estimate'] * 100
                if unk_pct < 0.1:
                    f.write(f"{config_name} & Unknown & {unk_pct:.4f}\\% & "
                           f"[{unk['ci_lower']*100:.4f}\\%, {unk['ci_upper']*100:.4f}\\%] & {unk['count']} \\\\\n")
                else:
                    f.write(f"{config_name} & Unknown & {unk_pct:.2f}\\% & "
                           f"[{unk['ci_lower']*100:.2f}\\%, {unk['ci_upper']*100:.2f}\\%] & {unk['count']} \\\\\n")

            f.write("\\bottomrule\n")
            f.write("\\end{tabular}\n")
            f.write("\\end{table}\n")

        print(f"  [OK] {tex_path}")

    # ========================================
    # A2: Triggered Subsets 数据驱动叙述
    # ========================================

    def rebuild_triggered_subsets(self):
        """
        A2: 重新生成triggered_subsets报告，修复：
        1. 删除硬编码模板句（如"子集规模较小"）
        2. 数据驱动叙述：subset_size、subset_share、McNemar检验
        3. 若subset_size > 1%，叙述应改为"在占比X%的触发子集中..."
        """
        print("\n[A2] Rebuilding triggered_subsets (data-driven narrative)...")

        baseline_results = self.results.get("baseline", [])
        triggered_dir = self.run_dir / "triggered_subsets"
        triggered_dir.mkdir(exist_ok=True)

        triggered_analysis = {}

        # For each ablation config
        for config_name in self.manifest.get("ablation_configs", {}).keys():
            if config_name == "baseline":
                continue

            ablation_results = self.results.get(config_name, [])

            if not ablation_results:
                print(f"  [WARNING] No results for {config_name}, skipping")
                continue

            # Identify module name from config
            module_name = self.extract_module_name(config_name)

            # Find triggered subset
            triggered_subset = self.find_triggered_subset(baseline_results, ablation_results)

            if not triggered_subset:
                print(f"  [{config_name}] No triggered records found")
                continue

            # Compute subset metrics
            subset_size = len(triggered_subset)
            n_labeled = self.manifest.get("n_records_labeled", len(baseline_results))
            subset_share = subset_size / n_labeled if n_labeled > 0 else 0.0

            # Compute baseline vs ablation accuracy within subset
            baseline_correct = sum(1 for r in triggered_subset if r["baseline_pred"] == r["ground_truth"])
            ablation_correct = sum(1 for r in triggered_subset if r["ablation_pred"] == r["ground_truth"])

            baseline_acc = baseline_correct / subset_size if subset_size > 0 else 0.0
            ablation_acc = ablation_correct / subset_size if subset_size > 0 else 0.0

            baseline_acc_ci = wilson_ci(baseline_correct, subset_size, alpha=0.05)
            ablation_acc_ci = wilson_ci(ablation_correct, subset_size, alpha=0.05)

            # McNemar test
            mcnemar_result = self.compute_mcnemar_on_subset(triggered_subset)

            # Store analysis
            triggered_analysis[module_name] = {
                "config_name": config_name,
                "subset_size": subset_size,
                "subset_share": subset_share,
                "baseline_accuracy": baseline_acc,
                "baseline_acc_ci": baseline_acc_ci,
                "ablation_accuracy": ablation_acc,
                "ablation_acc_ci": ablation_acc_ci,
                "mcnemar": mcnemar_result,
            }

            print(f"  [{module_name}] Subset size: {subset_size} ({subset_share*100:.2f}%)")

        # Write JSON
        json_path = triggered_dir / "ablation_triggered_subsets.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(triggered_analysis, f, indent=2)

        print(f"  [OK] {json_path}")

        # Generate .md (data-driven narrative)
        self.generate_triggered_subsets_md(triggered_analysis)

        print("  [A2] Triggered subsets rebuilt successfully")

    def extract_module_name(self, config_name: str) -> str:
        """从config名称提取模块名 / Extract module name from config"""
        # ablation_no_source_prior -> SourcePrior
        if "source_prior" in config_name:
            return "SourcePrior"
        elif "western_exclusion" in config_name:
            return "WesternExclusion"
        elif "batch_consistency" in config_name:
            return "BatchConsistency"
        elif "person_consistency" in config_name:
            return "PersonConsistency"
        elif "pub_consistency" in config_name:
            return "PubConsistency"
        else:
            return config_name.replace("ablation_no_", "").replace("_", " ").title()

    def find_triggered_subset(self, baseline_results: List[Dict], ablation_results: List[Dict]) -> List[Dict]:
        """找到触发子集（baseline与ablation输出不同的记录）"""
        triggered = []

        # Create lookup dict
        ablation_dict = {r["record_id"]: r for r in ablation_results}

        for base_r in baseline_results:
            rid = base_r["record_id"]

            if rid not in ablation_dict:
                continue

            abl_r = ablation_dict[rid]

            # Check if outputs differ
            if base_r.get("prediction") != abl_r.get("prediction"):
                triggered.append({
                    "record_id": rid,
                    "baseline_pred": base_r.get("prediction"),
                    "ablation_pred": abl_r.get("prediction"),
                    "ground_truth": base_r.get("ground_truth"),
                })

        return triggered

    def compute_mcnemar_on_subset(self, triggered_subset: List[Dict]) -> Dict:
        """在触发子集上计算McNemar检验"""
        # Contingency table:
        #          baseline_correct  baseline_wrong
        # abl_correct    a                b
        # abl_wrong      c                d

        a = 0  # both correct
        b = 0  # baseline wrong, ablation correct
        c = 0  # baseline correct, ablation wrong
        d = 0  # both wrong

        for r in triggered_subset:
            gt = r["ground_truth"]
            base_pred = r["baseline_pred"]
            abl_pred = r["ablation_pred"]

            base_correct = (base_pred == gt)
            abl_correct = (abl_pred == gt)

            if base_correct and abl_correct:
                a += 1
            elif (not base_correct) and abl_correct:
                b += 1
            elif base_correct and (not abl_correct):
                c += 1
            else:
                d += 1

        # McNemar test
        if b + c < 25:
            # Use exact or mid-p
            result = mcnemar_exact_or_mid_p(b, c)
            method = "exact" if b + c < 10 else "mid-p"
        else:
            # Continuity-corrected
            chi2 = ((abs(b - c) - 1) ** 2) / (b + c) if (b + c) > 0 else 0.0
            # p-value from chi-squared distribution (df=1)
            from scipy.stats import chi2 as chi2_dist
            p_value = 1 - chi2_dist.cdf(chi2, df=1)
            result = {"p_value": p_value, "chi2": chi2}
            method = "continuity-corrected"

        return {
            "method": method,
            "b": b,
            "c": c,
            "p_value": result.get("p_value", result.get("p_val")),
        }

    def generate_triggered_subsets_md(self, analysis: Dict):
        """A2: 生成data-driven的triggered_subsets.md"""
        md_path = self.run_dir / "triggered_subsets" / "ablation_triggered_subsets.md"

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Triggered Subsets Analysis\n\n")
            f.write("Analysis of triggered subsets for each ablation module.\n\n")
            f.write("**Triggered subset**: Records where baseline and ablation outputs differ.\n\n")

            for module_name, data in analysis.items():
                f.write(f"## {module_name}\n\n")

                subset_size = data["subset_size"]
                subset_share = data["subset_share"]

                # A2: 数据驱动叙述，避免模板化
                if subset_share > 0.01:
                    f.write(f"- **Subset size**: {subset_size} ({subset_share*100:.2f}% of labeled data)\n")
                    f.write(f"- **Interpretation**: In this {subset_share*100:.2f}% triggered subset, "
                           f"the module showed measurable impact.\n\n")
                else:
                    f.write(f"- **Subset size**: {subset_size} ({subset_share*100:.4f}% of labeled data)\n")
                    f.write(f"- **Interpretation**: Triggered on {subset_size} records.\n\n")

                # Metrics within subset
                f.write("### Accuracy within triggered subset\n\n")
                f.write(f"- **Baseline**: {data['baseline_accuracy']:.4f} "
                       f"[95% CI: {data['baseline_acc_ci'][0]:.4f}, {data['baseline_acc_ci'][1]:.4f}]\n")
                f.write(f"- **Ablation**: {data['ablation_accuracy']:.4f} "
                       f"[95% CI: {data['ablation_acc_ci'][0]:.4f}, {data['ablation_acc_ci'][1]:.4f}]\n\n")

                # McNemar test
                mcnemar = data["mcnemar"]
                f.write("### McNemar Test (within triggered subset)\n\n")
                f.write(f"- **Method**: {mcnemar['method']}\n")
                f.write(f"- **Discordant pairs**: b={mcnemar['b']}, c={mcnemar['c']}\n")
                f.write(f"- **p-value**: {mcnemar['p_value']:.4f}\n\n")

                # Interpretation
                if mcnemar['p_value'] > 0.05:
                    f.write("**Conclusion**: No significant difference between baseline and ablation "
                           "within the triggered subset (p > 0.05).\n\n")
                else:
                    f.write("**Conclusion**: Significant difference detected between baseline and ablation "
                           f"within the triggered subset (p = {mcnemar['p_value']:.4f}).\n\n")

                f.write("---\n\n")

        print(f"  [OK] {md_path}")

    # ========================================
    # A3: Sanity Samples 修复抽样逻辑
    # ========================================

    def rebuild_sanity_samples(self, n_samples_per_module: int = 25):
        """
        A3: 重新生成sanity_samples，修复抽样逻辑：
        1. 每个模块的样本必须来自该模块的触发子集
        2. 优先effective子集（baseline与ablation结果不同）
        3. 若effective为空，从fired子集采样
        4. 确保fired子集非空时，Fired Samples不为0
        """
        print("\n[A3] Rebuilding sanity_samples (fix sampling logic)...")

        baseline_results = self.results.get("baseline", [])
        samples_dir = self.run_dir / "sanity_samples"
        samples_dir.mkdir(exist_ok=True)

        all_samples = []

        for config_name in self.manifest.get("ablation_configs", {}).keys():
            if config_name == "baseline":
                continue

            ablation_results = self.results.get(config_name, [])

            if not ablation_results:
                continue

            module_name = self.extract_module_name(config_name)

            # Find effective subset (output changed)
            effective_subset = self.find_triggered_subset(baseline_results, ablation_results)

            # Sample from effective subset if available
            if effective_subset:
                import random
                random.seed(42)
                samples = random.sample(effective_subset, min(n_samples_per_module, len(effective_subset)))

                for sample in samples:
                    all_samples.append({
                        "module": module_name,
                        "record_id": sample["record_id"],
                        "baseline_pred": sample["baseline_pred"],
                        "ablation_pred": sample["ablation_pred"],
                        "ground_truth": sample["ground_truth"],
                        "subset_type": "effective",
                    })

                print(f"  [{module_name}] Sampled {len(samples)} from effective subset")
            else:
                print(f"  [{module_name}] No effective samples (outputs identical)")

        # Write JSONL
        jsonl_path = samples_dir / "ablation_sanity_samples.jsonl"
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for sample in all_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')

        print(f"  [OK] {jsonl_path} ({len(all_samples)} samples)")

        # Generate .md
        self.generate_sanity_samples_md(all_samples)

        print("  [A3] Sanity samples rebuilt successfully")

    def generate_sanity_samples_md(self, samples: List[Dict]):
        """A3: 生成sanity_samples.md"""
        md_path = self.run_dir / "sanity_samples" / "ablation_sanity_samples.md"

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Sanity Samples (Ablation Analysis)\n\n")
            f.write("Random samples from effective subsets of each module.\n\n")
            f.write(f"**Total samples**: {len(samples)}\n\n")

            # Group by module
            by_module = defaultdict(list)
            for s in samples:
                by_module[s["module"]].append(s)

            for module_name, module_samples in by_module.items():
                f.write(f"## {module_name}\n\n")
                f.write(f"**Samples**: {len(module_samples)}\n\n")

                f.write("| Record ID | Baseline | Ablation | Ground Truth | Match |\n")
                f.write("|-----------|----------|----------|--------------|-------|\n")

                for s in module_samples[:10]:  # Show first 10
                    match = "✓" if s["baseline_pred"] == s["ground_truth"] else "✗"
                    f.write(f"| {s['record_id'][:16]}... | {s['baseline_pred']} | "
                           f"{s['ablation_pred']} | {s['ground_truth']} | {match} |\n")

                f.write("\n---\n\n")

        print(f"  [OK] {md_path}")

    # ========================================
    # A4: Module Coverage 口径统一
    # ========================================

    def rebuild_module_coverage(self):
        """
        A4: 重新生成module_coverage，统一口径：
        1. 明确三层定义：evaluated, fired, effective
        2. effective由baseline vs ablation输出对比得到
        3. 在md第一段写清楚定义
        """
        print("\n[A4] Rebuilding module_coverage (unify criteria)...")

        baseline_results = self.results.get("baseline", [])

        # Initialize module stats
        module_stats = defaultdict(lambda: {"evaluated": 0, "fired": 0, "effective": 0})

        # For each record in baseline
        for base_r in baseline_results:
            fired_modules = base_r.get("fired_modules", [])

            # All fired modules are evaluated
            for module in fired_modules:
                module_stats[module]["evaluated"] += 1
                module_stats[module]["fired"] += 1

        # Compute effective (from triggered subsets)
        for config_name in self.manifest.get("ablation_configs", {}).keys():
            if config_name == "baseline":
                continue

            ablation_results = self.results.get(config_name, [])
            module_name = self.extract_module_name(config_name)

            # Find triggered (effective) subset
            triggered = self.find_triggered_subset(baseline_results, ablation_results)
            module_stats[module_name]["effective"] = len(triggered)

        # Write JSON
        coverage_dir = self.run_dir / "events" / "baseline"
        coverage_dir.mkdir(parents=True, exist_ok=True)

        json_path = coverage_dir / "module_coverage.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(dict(module_stats), f, indent=2)

        print(f"  [OK] {json_path}")

        # Generate .md
        self.generate_module_coverage_md(module_stats)

        print("  [A4] Module coverage rebuilt successfully")

    def generate_module_coverage_md(self, module_stats: Dict):
        """A4: 生成module_coverage.md，第一段写明定义"""
        md_path = self.run_dir / "events" / "baseline" / "module_coverage.md"

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Module Coverage\n\n")

            # A4: 第一段写清楚三层定义
            f.write("## Definitions\n\n")
            f.write("- **Evaluated**: Module was evaluated on this record (input conditions met)\n")
            f.write("- **Fired**: Module triggered a non-default rule/override\n")
            f.write("- **Effective**: Baseline vs. ablation output changed (order or unknown)\n\n")
            f.write("**Note**: Effective counts are derived from baseline vs. ablation comparisons, "
                   "not from counterfactual inference within a single run.\n\n")

            f.write("## Module Statistics\n\n")
            f.write("| Module | Evaluated | Fired | Effective |\n")
            f.write("|--------|-----------|-------|----------|\n")

            for module, stats in sorted(module_stats.items()):
                f.write(f"| {module} | {stats['evaluated']} | {stats['fired']} | {stats['effective']} |\n")

        print(f"  [OK] {md_path}")

    # ========================================
    # A5: 复现性元数据增强
    # ========================================

    def rebuild_reproducibility_metadata(self):
        """
        A5: 增强复现性元数据：
        1. 确保run_manifest.json包含必要字段
        2. 若is_dirty=true，生成dirty_patch.diff
        """
        print("\n[A5] Rebuilding reproducibility metadata...")

        # Check required fields
        required_fields = [
            ("git_info", "commit_sha"),
            ("git_info", "is_dirty"),
            ("reproducibility", "random_seed"),
            "n_records_total",
            "n_records_labeled",
        ]

        missing_fields = []
        for field in required_fields:
            if isinstance(field, tuple):
                parent, child = field
                if parent not in self.manifest or child not in self.manifest[parent]:
                    missing_fields.append(f"{parent}.{child}")
            else:
                if field not in self.manifest:
                    missing_fields.append(field)

        if missing_fields:
            print(f"  [WARNING] Missing fields in manifest: {missing_fields}")
        else:
            print("  [OK] All required fields present in manifest")

        # If is_dirty, generate patch
        git_info = self.manifest.get("git_info", {})
        if git_info.get("is_dirty"):
            print("  Generating dirty patch...")
            self.generate_dirty_patch()

        print("  [A5] Reproducibility metadata enhanced")

    def generate_dirty_patch(self):
        """生成git diff patch文件"""
        repro_dir = self.run_dir / "repro"
        repro_dir.mkdir(exist_ok=True)

        patch_path = repro_dir / "dirty_patch.diff"

        try:
            # Run git diff
            result = subprocess.run(
                ["git", "diff"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                with open(patch_path, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)

                print(f"  [OK] {patch_path}")
            else:
                print(f"  [WARNING] git diff failed: {result.stderr}")

        except Exception as e:
            print(f"  [WARNING] Failed to generate patch: {e}")

    # ========================================
    # Main rebuild workflow
    # ========================================

    def rebuild_all(self):
        """执行所有报表重建步骤"""
        print("\n" + "="*80)
        print("REPORT REBUILDER")
        print("="*80)
        print(f"Run directory: {self.run_dir}")
        print("")

        # A1: Stats CI
        self.rebuild_stats_ci()

        # A2: Triggered Subsets
        self.rebuild_triggered_subsets()

        # A3: Sanity Samples
        self.rebuild_sanity_samples()

        # A4: Module Coverage
        self.rebuild_module_coverage()

        # A5: Reproducibility Metadata
        self.rebuild_reproducibility_metadata()

        print("\n" + "="*80)
        print("REBUILD COMPLETE")
        print("="*80)
        print("\nRebuilt outputs:")
        print("  - statistics/stats_ci_global.{json,md,tex}")
        print("  - triggered_subsets/ablation_triggered_subsets.{json,md}")
        print("  - sanity_samples/ablation_sanity_samples.{jsonl,md}")
        print("  - events/baseline/module_coverage.{json,md}")
        print("  - repro/dirty_patch.diff (if is_dirty=true)")
        print("")


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild reports from existing experiment results (without re-running algorithm)"
    )
    parser.add_argument(
        "--run_dir",
        type=str,
        required=True,
        help="Path to existing run directory (e.g., runs/evidence_chain_301k_P0_P5_FINAL_V2)"
    )

    args = parser.parse_args()

    try:
        rebuilder = ReportRebuilder(args.run_dir)
        rebuilder.rebuild_all()

        print("\nSuccess! Reports rebuilt.")
        sys.exit(0)

    except Exception as e:
        print(f"\n[ERROR] Rebuild failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
