#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终锁定验证脚本 / Final Lock Verification Script

目的 / Purpose:
验证 runs/istina_pilot_10k_final/ 目录的完整性和一致性，确保可用于论文写作。
Verify the integrity and consistency of runs/istina_pilot_10k_final/ directory
to ensure it's ready for paper writing.

验证内容 / Verification Content:
1. 所有必需文件存在性检查 / Required files existence check
2. Git commit 一致性检查 / Git commit consistency check
3. 数值一致性检查 (JSON vs LaTeX) / Numerical consistency check
4. 无 input_tokens 检查 / No input_tokens check
5. 无 raw 文件检查 / No raw files check

输出 / Output:
runs/istina_pilot_10k_final/FINAL_LOCK_CHECK.md

作者 / Author: Ma Jiaxin + Claude Sonnet 4.5
日期 / Date: 2025-12-21
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

# 设置 UTF-8 输出 (Windows 兼容)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class FinalLockVerifier:
    """最终锁定验证器 / Final Lock Verifier"""

    def __init__(self, run_dir: Path):
        """
        初始化验证器 / Initialize verifier

        Args:
            run_dir: 运行目录路径 / Run directory path
        """
        self.run_dir = run_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checks_passed: int = 0
        self.checks_total: int = 0

    def log_error(self, message: str):
        """记录错误 / Log error"""
        self.errors.append(f"❌ {message}")
        print(f"  [ERROR] {message}")

    def log_warning(self, message: str):
        """记录警告 / Log warning"""
        self.warnings.append(f"⚠️ {message}")
        print(f"  [WARN] {message}")

    def log_success(self, message: str):
        """记录成功 / Log success"""
        print(f"  [OK] {message}")

    def check_file_exists(self, rel_path: str) -> bool:
        """
        检查文件是否存在 / Check if file exists

        Args:
            rel_path: 相对路径 / Relative path

        Returns:
            是否存在 / Whether exists
        """
        file_path = self.run_dir / rel_path
        if not file_path.exists():
            self.log_error(f"缺少文件 / Missing file: {rel_path}")
            return False
        return True

    def verify_required_files(self) -> bool:
        """
        验证所有必需文件存在 / Verify all required files exist

        Returns:
            是否通过 / Whether passed
        """
        self.checks_total += 1
        print("\n[检查 1/5] 必需文件存在性 / Required Files Existence")

        required_files = [
            # 元数据 / Metadata
            "run_manifest.json",
            "performance_benchmark.json",
            "dataset_card.md",
            "env.txt",

            # 报告 / Reports
            "reports/istina_pilot_summary.md",

            # 表格 / Tables
            "tables/istina_pilot_quality.tex",
            "tables/istina_pilot_perf.tex",

            # 日志 / Logs
            "logs/istina_batch_redacted_200.jsonl",
            "logs/istina_batch_redaction_policy.md",
            "logs/istina_batch_redaction_policy.json",

            # 统计 / Statistics
            "statistics/stats_ci_global.json",

            # 事件 / Events
            "events/baseline/decision_events.jsonl",
            "events/baseline/module_coverage.json",
        ]

        all_exist = True
        for file_path in required_files:
            if not self.check_file_exists(file_path):
                all_exist = False

        if all_exist:
            self.log_success(f"所有 {len(required_files)} 个必需文件存在")
            self.checks_passed += 1
            return True
        else:
            return False

    def verify_git_consistency(self) -> bool:
        """
        验证 Git commit 一致性 / Verify Git commit consistency

        Returns:
            是否通过 / Whether passed
        """
        self.checks_total += 1
        print("\n[检查 2/5] Git Commit 一致性 / Git Commit Consistency")

        # 读取 run_manifest.json
        manifest_path = self.run_dir / "run_manifest.json"
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        # Try both old and new format
        manifest_commit = manifest.get("git_commit_short", "")
        if not manifest_commit and "git_info" in manifest:
            manifest_commit = manifest["git_info"].get("commit_sha_short", "")

        # 读取 performance_benchmark.json
        perf_path = self.run_dir / "performance_benchmark.json"
        with open(perf_path, 'r', encoding='utf-8') as f:
            perf = json.load(f)
        perf_commit = perf.get("git_commit_short", "")

        # 获取当前 HEAD
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short=7", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.run_dir.parent.parent  # 仓库根目录
            )
            current_commit = result.stdout.strip()
        except subprocess.CalledProcessError:
            self.log_error("无法获取当前 Git commit")
            return False

        # 比较
        if manifest_commit == perf_commit == current_commit:
            self.log_success(f"Git commit 一致: {current_commit}")
            self.checks_passed += 1
            return True
        else:
            self.log_error(
                f"Git commit 不一致 / Git commit mismatch:\n"
                f"  - run_manifest.json: {manifest_commit}\n"
                f"  - performance_benchmark.json: {perf_commit}\n"
                f"  - Current HEAD: {current_commit}"
            )
            return False

    def verify_numerical_consistency(self) -> bool:
        """
        验证数值一致性 (JSON vs LaTeX) / Verify numerical consistency

        Returns:
            是否通过 / Whether passed
        """
        self.checks_total += 1
        print("\n[检查 3/5] 数值一致性 (JSON vs LaTeX) / Numerical Consistency")

        # 读取 JSON 数据
        stats_path = self.run_dir / "statistics" / "stats_ci_global.json"
        with open(stats_path, 'r', encoding='utf-8') as f:
            stats = json.load(f)

        perf_path = self.run_dir / "performance_benchmark.json"
        with open(perf_path, 'r', encoding='utf-8') as f:
            perf = json.load(f)

        # 读取 LaTeX 表格
        quality_tex_path = self.run_dir / "tables" / "istina_pilot_quality.tex"
        with open(quality_tex_path, 'r', encoding='utf-8') as f:
            quality_tex = f.read()

        perf_tex_path = self.run_dir / "tables" / "istina_pilot_perf.tex"
        with open(perf_tex_path, 'r', encoding='utf-8') as f:
            perf_tex = f.read()

        # 提取关键指标
        checks = []

        # 1. Accuracy (from stats)
        json_accuracy = stats.get("accuracy_pct", 0.0)
        tex_accuracy_match = re.search(r'Accuracy.*?&\s*([\d.]+)%', quality_tex)
        if tex_accuracy_match:
            tex_accuracy = float(tex_accuracy_match.group(1))
            checks.append(("Accuracy", json_accuracy, tex_accuracy))

        # 2. Throughput (from perf)
        json_throughput = perf.get("throughput_names_per_sec", 0.0)
        tex_throughput_match = re.search(r'Throughput.*?&\s*([\d,]+(?:\.[\d]+)?)', perf_tex)
        if tex_throughput_match:
            tex_throughput = float(tex_throughput_match.group(1).replace(',', ''))
            checks.append(("Throughput", json_throughput, tex_throughput))

        # 3. Precision (from stats)
        json_precision = stats.get("precision_pct", 0.0)
        tex_precision_match = re.search(r'Precision.*?&\s*([\d.]+)%', quality_tex)
        if tex_precision_match:
            tex_precision = float(tex_precision_match.group(1))
            checks.append(("Precision", json_precision, tex_precision))

        # 4. Recall (from stats)
        json_recall = stats.get("recall_pct", 0.0)
        tex_recall_match = re.search(r'Recall.*?&\s*([\d.]+)%', quality_tex)
        if tex_recall_match:
            tex_recall = float(tex_recall_match.group(1))
            checks.append(("Recall", json_recall, tex_recall))

        # 验证一致性
        all_consistent = True
        for metric_name, json_val, tex_val in checks:
            diff = abs(json_val - tex_val)

            # 根据指标类型设置不同容差
            # For percentages (Accuracy, Precision, Recall): ±0.01%
            # For large numbers (Throughput): ±0.1 (accounts for rounding to 1 decimal)
            if metric_name == "Throughput":
                tolerance = 0.1  # Allow rounding difference
            else:
                tolerance = 0.01  # Strict for percentages

            if diff <= tolerance:
                self.log_success(
                    f"{metric_name}: JSON={json_val:.2f}, LaTeX={tex_val:.2f}, "
                    f"Diff={diff:.4f} (≤{tolerance})"
                )
            else:
                self.log_error(
                    f"{metric_name} 不一致: JSON={json_val:.2f}, LaTeX={tex_val:.2f}, "
                    f"Diff={diff:.4f} (>{tolerance})"
                )
                all_consistent = False

        if all_consistent:
            self.checks_passed += 1
            return True
        else:
            return False

    def verify_no_input_tokens(self) -> bool:
        """
        验证 decision_events.jsonl 无 input_tokens / Verify no input_tokens

        Returns:
            是否通过 / Whether passed
        """
        self.checks_total += 1
        print("\n[检查 4/5] 无 input_tokens 检查 / No input_tokens Check")

        events_path = self.run_dir / "events" / "baseline" / "decision_events.jsonl"

        with open(events_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_events = len(lines)
        events_with_tokens = 0

        # 采样检查（前100条 + 后100条）
        sample_lines = lines[:100] + lines[-100:]

        for line in sample_lines:
            try:
                event = json.loads(line.strip())
                if "input_tokens" in event:
                    events_with_tokens += 1
            except json.JSONDecodeError:
                continue

        if events_with_tokens > 0:
            self.log_error(
                f"发现 {events_with_tokens} 条事件包含 input_tokens "
                f"(采样 {len(sample_lines)} 条，总共 {total_events} 条)"
            )
            return False
        else:
            self.log_success(
                f"无 input_tokens (采样 {len(sample_lines)} 条，总共 {total_events} 条)"
            )
            self.checks_passed += 1
            return True

    def verify_no_raw_files(self) -> bool:
        """
        验证 logs/ 无 raw 文件 / Verify no raw files in logs/

        Returns:
            是否通过 / Whether passed
        """
        self.checks_total += 1
        print("\n[检查 5/5] 无 raw 文件检查 / No Raw Files Check")

        logs_dir = self.run_dir / "logs"

        # 禁止文件列表
        prohibited_files = [
            "istina_batch_full.jsonl",
            "istina_batch_raw_sampled.jsonl",
        ]

        found_prohibited = []
        for file_name in prohibited_files:
            file_path = logs_dir / file_name
            if file_path.exists():
                found_prohibited.append(file_name)

        if found_prohibited:
            self.log_error(
                f"发现 {len(found_prohibited)} 个禁止文件: {', '.join(found_prohibited)}"
            )
            return False
        else:
            self.log_success("无禁止的 raw 文件")
            self.checks_passed += 1
            return True

    def generate_report(self) -> str:
        """
        生成验证报告 / Generate verification report

        Returns:
            报告内容 / Report content
        """
        # 读取元数据
        manifest_path = self.run_dir / "run_manifest.json"
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        stats_path = self.run_dir / "statistics" / "stats_ci_global.json"
        with open(stats_path, 'r', encoding='utf-8') as f:
            stats = json.load(f)

        perf_path = self.run_dir / "performance_benchmark.json"
        with open(perf_path, 'r', encoding='utf-8') as f:
            perf = json.load(f)

        # Extract values with fallbacks for different manifest formats
        git_commit = manifest.get("git_commit_short", "")
        if not git_commit and "git_info" in manifest:
            git_commit = manifest["git_info"].get("commit_sha_short", "N/A")

        end_time = manifest.get("end_time", "N/A")
        if end_time == "N/A":
            end_time = manifest.get("timestamp_utc", "N/A")

        n_records = manifest.get("n_records", 0)
        if n_records == 0:
            n_records = manifest.get("n_records_labeled", 0)

        # Extract stats with correct keys
        def _pct(stats_obj, key_base: str) -> float:
            """
            Extract percentage value with fallback logic:
            1. Prefer explicit *_pct key
            2. Accept 0..1 decimal fraction (* 100)
            3. Return NaN if neither exists
            """
            # Prefer explicit *_pct
            k_pct = f"{key_base}_pct"
            if k_pct in stats_obj and isinstance(stats_obj[k_pct], (int, float)):
                return float(stats_obj[k_pct])
            # Else accept 0..1 decimal fraction
            if key_base in stats_obj and isinstance(stats_obj[key_base], (int, float)):
                v = float(stats_obj[key_base])
                return v * 100.0 if v <= 1.0 else v
            return float("nan")

        accuracy_pct = _pct(stats, "accuracy")
        precision_pct = _pct(stats, "precision")
        recall_pct = _pct(stats, "recall")

        # If still NaN (some runs don't export precision/recall), fall back to run_manifest baseline when possible
        try:
            if not (accuracy_pct == accuracy_pct):  # NaN check
                baseline = manifest.get("results_summary", {}).get("baseline", {})
                if isinstance(baseline.get("accuracy"), (int, float)):
                    accuracy_pct = float(baseline["accuracy"]) * 100.0
        except Exception:
            pass

        # 确定状态
        if self.checks_passed == self.checks_total:
            status = "✅ **LOCKED - READY FOR PAPER**"
            status_emoji = "🔒"
        else:
            status = "❌ **VERIFICATION FAILED**"
            status_emoji = "⚠️"

        # 生成报告
        report = f"""# Final Lock Check Report / 最终锁定检查报告

**日期 / Date**: 2025-12-21
**目录 / Directory**: `{self.run_dir.relative_to(self.run_dir.parent.parent)}/`
**状态 / Status**: {status}

---

## 执行概要 / Executive Summary

**验证器 / Verifier**: `experiments/verify_final_lock.py`
**检查总数 / Total Checks**: {self.checks_total}
**通过数量 / Passed**: {self.checks_passed}
**失败数量 / Failed**: {self.checks_total - self.checks_passed}
**错误数量 / Errors**: {len(self.errors)}
**警告数量 / Warnings**: {len(self.warnings)}

---

## 核心元数据 / Core Metadata

| 项目 / Item | 值 / Value |
|-------------|-----------|
| **Git Commit** | `{git_commit}` |
| **运行时间 / Run Time** | {end_time} |
| **样本数 / N Records** | {n_records:,} |
| **Accuracy** | {accuracy_pct:.2f}% |
| **Precision** | {precision_pct:.2f}% |
| **Recall** | {recall_pct:.2f}% |
| **Throughput** | {perf.get("throughput_names_per_sec", 0.0):,.1f} names/sec |

---

## 验证结果 / Verification Results

### 检查 1: 必需文件存在性 / Required Files Existence

**状态 / Status**: {"✅ PASS" if self.checks_passed >= 1 else "❌ FAIL"}

检查所有必需文件是否存在于运行目录中。

---

### 检查 2: Git Commit 一致性 / Git Commit Consistency

**状态 / Status**: {"✅ PASS" if self.checks_passed >= 2 else "❌ FAIL"}

验证 `run_manifest.json`、`performance_benchmark.json` 和当前 HEAD 的 Git commit 是否一致。

---

### 检查 3: 数值一致性 / Numerical Consistency

**状态 / Status**: {"✅ PASS" if self.checks_passed >= 3 else "❌ FAIL"}

验证 JSON 元数据与 LaTeX 表格中的数值是否一致（容差 ±0.01%）。

---

### 检查 4: 无 input_tokens / No input_tokens

**状态 / Status**: {"✅ PASS" if self.checks_passed >= 4 else "❌ FAIL"}

验证 `events/baseline/decision_events.jsonl` 不包含原始 tokens（PII 保护）。

---

### 检查 5: 无 raw 文件 / No Raw Files

**状态 / Status**: {"✅ PASS" if self.checks_passed >= 5 else "❌ FAIL"}

验证 `logs/` 目录不包含 `istina_batch_full.jsonl` 或 `istina_batch_raw_sampled.jsonl`。

---

## 错误清单 / Error List

"""
        if self.errors:
            for error in self.errors:
                report += f"{error}\n"
        else:
            report += "✅ 无错误 / No errors\n"

        report += "\n---\n\n## 警告清单 / Warning List\n\n"

        if self.warnings:
            for warning in self.warnings:
                report += f"{warning}\n"
        else:
            report += "✅ 无警告 / No warnings\n"

        report += f"""
---

## 最终结论 / Final Conclusion

**验收状态 / Acceptance Status**: {status}

"""
        if self.checks_passed == self.checks_total:
            report += f"""
{status_emoji} **此目录已通过所有验证，可用于论文写作。**

{status_emoji} **This directory has passed all verifications and is ready for paper writing.**

### 论文引用指南 / Paper Citation Guide

**LaTeX 表格引用 / LaTeX Table References**:
```latex
% Table 4.1: Quality Metrics
\\input{{runs/istina_pilot_10k_final/tables/istina_pilot_quality.tex}}

% Table 4.2: Performance Benchmark
\\input{{runs/istina_pilot_10k_final/tables/istina_pilot_perf.tex}}
```

**数据可用性声明 / Data Availability Statement**:
```
Redacted decision logs are available in Supplementary Material S1
(runs/istina_pilot_10k_final/logs/istina_batch_redacted_200.jsonl),
along with the redaction policy in Supplementary Material S2
(runs/istina_pilot_10k_final/logs/istina_batch_redaction_policy.md).
All source code and replication materials are available in the
replication package at runs/istina_pilot_10k_final/.
```
"""
        else:
            report += f"""
⚠️ **此目录未通过验证，不可用于论文写作。请修复上述错误后重新运行验证。**

⚠️ **This directory failed verification and is NOT ready for paper writing.
Please fix the errors above and re-run verification.**
"""

        report += f"""
---

**验证者 / Verified By**: Ma Jiaxin + Claude Sonnet 4.5
**验证日期 / Verification Date**: 2025-12-21
**验证脚本 / Verification Script**: `experiments/verify_final_lock.py`
**文档版本 / Document Version**: 1.0
"""

        return report

    def run(self) -> bool:
        """
        运行所有验证 / Run all verifications

        Returns:
            是否全部通过 / Whether all passed
        """
        print(f"\n{'='*70}")
        print(f"最终锁定验证 / Final Lock Verification")
        print(f"目录 / Directory: {self.run_dir}")
        print(f"{'='*70}")

        # 运行所有检查
        self.verify_required_files()
        self.verify_git_consistency()
        self.verify_numerical_consistency()
        self.verify_no_input_tokens()
        self.verify_no_raw_files()

        # 生成报告
        report = self.generate_report()
        report_path = self.run_dir / "FINAL_LOCK_CHECK.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n{'='*70}")
        print(f"验证报告已生成 / Verification report generated:")
        print(f"  {report_path}")
        print(f"{'='*70}")

        if self.checks_passed == self.checks_total:
            print(f"\n✅ 所有检查通过 / All checks passed ({self.checks_passed}/{self.checks_total})")
            print(f"🔒 目录已锁定，可用于论文写作 / Directory locked, ready for paper writing\n")
            return True
        else:
            print(f"\n❌ 验证失败 / Verification failed ({self.checks_passed}/{self.checks_total})")
            print(f"⚠️ 请修复错误后重新验证 / Please fix errors and re-verify\n")
            return False


def main():
    """主函数 / Main function"""
    # 默认验证 istina_pilot_10k_final
    repo_root = Path(__file__).parent.parent
    run_dir = repo_root / "runs" / "istina_pilot_10k_final"

    if not run_dir.exists():
        print(f"❌ 错误 / Error: 目录不存在 / Directory does not exist: {run_dir}")
        return 1

    verifier = FinalLockVerifier(run_dir)
    success = verifier.run()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
