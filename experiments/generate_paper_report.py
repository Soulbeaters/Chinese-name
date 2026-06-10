# -*- coding: utf-8 -*-
"""
论文数据报告生成器 / Paper Data Report Generator

动态生成论文数据报告，根据实际实验状态自动判断完成情况
Dynamically generate paper data report based on actual experiment status

P2实现：不允许硬编码"301k已完成"，必须动态检查实验状态
P2 Implementation: No hardcoding "301k completed", must check experiment status dynamically

作者: Ma Jiaxin
日期: 2025-12-20
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from experiments.experiment_status import check_experiment_status, ExperimentStatus


class PaperReportGenerator:
    """论文报告生成器 / Paper Report Generator"""

    def __init__(self, project_root: str = None):
        """
        初始化生成器

        Args:
            project_root: 项目根目录 (默认为当前文件的父级父级目录)
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = Path(project_root)

        self.runs_dir = self.project_root / "runs"

    def check_key_experiments(self) -> Dict[str, Dict[str, Any]]:
        """
        检查关键实验的状态 / Check key experiment statuses

        Returns:
            实验名称 -> 状态信息的字典
        """
        # 定义关键实验 (按用户需求定义)
        key_experiments = {
            "evidence_chain_10k_strict_test": str(self.runs_dir / "evidence_chain_10k_strict_test"),
            "evidence_chain_301k_FINAL": str(self.runs_dir / "evidence_chain_301k_FINAL"),
            "evidence_chain_301k_STRICT": str(self.runs_dir / "evidence_chain_301k_STRICT"),
            "performance_benchmark_10k_FINAL": str(self.runs_dir / "performance_benchmark_10k_FINAL"),
        }

        statuses = {}
        for exp_name, exp_dir in key_experiments.items():
            status_info = check_experiment_status(exp_dir, require_validation=True)
            statuses[exp_name] = status_info

        return statuses

    def generate_executive_summary(self, statuses: Dict[str, Dict[str, Any]]) -> str:
        """
        生成执行摘要 / Generate executive summary

        Args:
            statuses: 实验状态字典

        Returns:
            Markdown格式的执行摘要
        """
        lines = [
            "## 执行摘要 / Executive Summary",
            "",
        ]

        # Count experiment statuses
        completed_count = sum(
            1 for s in statuses.values()
            if s["status"] == ExperimentStatus.COMPLETED
        )
        running_count = sum(
            1 for s in statuses.values()
            if s["status"] == ExperimentStatus.RUNNING
        )
        failed_count = sum(
            1 for s in statuses.values()
            if s["status"] == ExperimentStatus.FAILED
        )
        not_started_count = sum(
            1 for s in statuses.values()
            if s["status"] == ExperimentStatus.NOT_STARTED
        )

        total_count = len(statuses)

        lines.append(f"**实验总数**: {total_count}")
        lines.append(f"**已完成**: {completed_count} {('✅' if completed_count > 0 else '')}")
        lines.append(f"**运行中**: {running_count} {('🔄' if running_count > 0 else '')}")
        lines.append(f"**失败**: {failed_count} {('❌' if failed_count > 0 else '')}")
        lines.append(f"**未开始**: {not_started_count} {('⏸️' if not_started_count > 0 else '')}")
        lines.append("")

        # List individual experiments
        lines.append("### 实验状态详情 / Experiment Status Details")
        lines.append("")

        for exp_name, status_info in statuses.items():
            emoji = status_info["status_emoji"]
            status_str = status_info["status_str"]
            details = status_info["details"]

            lines.append(f"- **{exp_name}**: {emoji} {status_str}")
            lines.append(f"  - {details}")

            # (P0-P3收敛任务1): 如果失败，显示完整验证错误
            # If failed, display full validation error
            if status_info["status"] == ExperimentStatus.FAILED and status_info.get("validation_error"):
                lines.append(f"")
                lines.append(f"  **完整验证错误输出**:")
                lines.append(f"  ```")
                # 使用summary版本（最后20行）
                error_summary = status_info.get("validation_error_summary", status_info["validation_error"])
                for line in error_summary.split('\n'):
                    lines.append(f"  {line}")
                lines.append(f"  ```")

            # 如果运行中，显示缺失文件
            # If running, display missing files
            if status_info["status"] == ExperimentStatus.RUNNING and status_info.get("missing_files"):
                lines.append(f"  **缺失文件** ({len(status_info['missing_files'])}个):")
                for mf in status_info["missing_files"][:5]:  # 最多显示5个
                    lines.append(f"    - `{mf}`")
                if len(status_info["missing_files"]) > 5:
                    lines.append(f"    - ... (还有{len(status_info['missing_files'])-5}个)")

            lines.append("")

        return "\n".join(lines)

    def generate_results_summary(self, statuses: Dict[str, Dict[str, Any]]) -> str:
        """
        生成结果摘要 / Generate results summary

        Args:
            statuses: 实验状态字典

        Returns:
            Markdown格式的结果摘要
        """
        lines = [
            "## 主要结果 / Main Results",
            "",
        ]

        # 10K实验结果
        exp_10k = "evidence_chain_10k_strict_test"
        if exp_10k in statuses:
            status_10k = statuses[exp_10k]
            if status_10k["status"] == ExperimentStatus.COMPLETED:
                lines.append(f"### {exp_10k} {status_10k['status_emoji']}")
                lines.append("")
                lines.append(self._extract_results_from_manifest(
                    self.runs_dir / "evidence_chain_10k_strict_test"
                ))
            else:
                lines.append(f"### {exp_10k} {status_10k['status_emoji']}")
                lines.append("")
                lines.append(f"**状态**: {status_10k['status_str']}")
                lines.append(f"**详情**: {status_10k['details']}")
                lines.append("")

        # 301K实验结果
        exp_301k_final = "evidence_chain_301k_FINAL"
        exp_301k_strict = "evidence_chain_301k_STRICT"

        # 优先使用STRICT版本，如果不存在则使用FINAL版本
        exp_301k = None
        if exp_301k_strict in statuses and statuses[exp_301k_strict]["status"] == ExperimentStatus.COMPLETED:
            exp_301k = exp_301k_strict
        elif exp_301k_final in statuses and statuses[exp_301k_final]["status"] == ExperimentStatus.COMPLETED:
            exp_301k = exp_301k_final

        if exp_301k:
            status_301k = statuses[exp_301k]
            lines.append(f"### {exp_301k} {status_301k['status_emoji']}")
            lines.append("")
            lines.append(self._extract_results_from_manifest(
                self.runs_dir / exp_301k
            ))
        else:
            # 两个版本都未完成
            lines.append(f"### 301K实验 🔄")
            lines.append("")
            lines.append("**状态**: 尚未完成或验证失败")
            lines.append("")

            # 显示各版本的详细状态
            if exp_301k_final in statuses:
                lines.append(f"- **{exp_301k_final}**: {statuses[exp_301k_final]['status_emoji']} {statuses[exp_301k_final]['status_str']}")
            if exp_301k_strict in statuses:
                lines.append(f"- **{exp_301k_strict}**: {statuses[exp_301k_strict]['status_emoji']} {statuses[exp_301k_strict]['status_str']}")
            lines.append("")

        return "\n".join(lines)

    def _extract_results_from_manifest(self, exp_dir: Path) -> str:
        """
        从实验目录提取结果 / Extract results from experiment directory

        Args:
            exp_dir: 实验目录

        Returns:
            Markdown格式的结果摘要
        """
        lines = []

        # Read run_manifest.json
        manifest_path = exp_dir / "run_manifest.json"
        if not manifest_path.exists():
            lines.append("*No run_manifest.json found*")
            return "\n".join(lines)

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Extract key info
            n_total = manifest.get("n_records_total", "N/A")
            n_labeled = manifest.get("n_records_labeled", "N/A")

            lines.append(f"- **总记录数**: {n_total}")
            lines.append(f"- **标注记录数**: {n_labeled}")
            lines.append("")

            # Read stats_ci_global.json for accuracy
            stats_path = exp_dir / "statistics" / "stats_ci_global.json"
            if stats_path.exists():
                with open(stats_path, 'r', encoding='utf-8') as f:
                    stats = json.load(f)

                # Extract baseline accuracy
                if "confidence_intervals" in stats and "baseline" in stats["confidence_intervals"]:
                    baseline_cis = stats["confidence_intervals"]["baseline"]

                    # (P0-P3收敛任务4): 论文主指标只引用 end_to_end_accuracy
                    # Primary metric: end_to_end_accuracy ONLY (avoid metric confusion)
                    # - end_to_end: unknown counted as error (strictest)
                    # - conditional: unknown excluded (shows performance when system decides)
                    # - coverage: proportion with definitive answer

                    # 论文主指标 / Primary metric for paper
                    if "end_to_end_accuracy" in baseline_cis:
                        e2e = baseline_cis["end_to_end_accuracy"]
                        lines.append(f"- **Accuracy** (end-to-end, primary metric): {e2e['point_estimate']*100:.2f}% (95% CI: [{e2e['lower_bound']*100:.2f}%, {e2e['upper_bound']*100:.2f}%])")
                        lines.append(f"  - Definition: correct / N_labeled (unknown counted as error)")

                    # 补充指标（仅供参考，不引用到论文主表）
                    # Supplementary metrics (for reference only, not for paper main table)
                    if "conditional_accuracy" in baseline_cis and "coverage" in baseline_cis:
                        cond = baseline_cis["conditional_accuracy"]
                        cov = baseline_cis["coverage"]
                        lines.append(f"- **Supplementary**:")
                        lines.append(f"  - Conditional Accuracy: {cond['point_estimate']*100:.2f}% (unknown excluded)")
                        lines.append(f"  - Coverage: {cov['point_estimate']*100:.2f}% (proportion with answer)")

                    lines.append("")

        except Exception as e:
            lines.append(f"*Error extracting results: {str(e)}*")
            lines.append("")

        return "\n".join(lines)

    def generate_full_report(self) -> str:
        """
        生成完整报告 / Generate full report

        Returns:
            Markdown格式的完整报告
        """
        # Check all key experiments
        statuses = self.check_key_experiments()

        lines = [
            "# 论文数据收集报告 (动态生成) / Paper Data Collection Report (Dynamically Generated)",
            "",
            f"**生成日期**: {datetime.now().isoformat()}",
            "**作者**: Ma Jiaxin",
            "**项目**: Chinese Name Processing System v8.0",
            "",
            "---",
            "",
            self.generate_executive_summary(statuses),
            "",
            "---",
            "",
            self.generate_results_summary(statuses),
            "",
            "---",
            "",
            "## 说明 / Note",
            "",
            "本报告由 `experiments/generate_paper_report.py` 自动生成。",
            "实验状态根据实际文件存在性和 `validate_deliverables.py` 验证结果动态判断。",
            "",
            "**不再硬编码实验完成状态**（P2要求）。",
            "",
            "This report is automatically generated by `experiments/generate_paper_report.py`.",
            "Experiment status is dynamically determined based on actual file existence and `validate_deliverables.py` validation results.",
            "",
            "**No longer hardcoding experiment completion status** (P2 requirement).",
            "",
        ]

        return "\n".join(lines)


def main():
    """命令行入口 / CLI Entry Point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="生成论文数据报告 / Generate paper data report"
    )
    parser.add_argument(
        "--output",
        default="PAPER_DATA_REPORT_DYNAMIC.md",
        help="输出文件路径 / Output file path"
    )

    args = parser.parse_args()

    # Generate report
    generator = PaperReportGenerator()
    report_content = generator.generate_full_report()

    # Write to file
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\n[Report Generated]")
    print(f"  Output: {output_path}")
    print(f"  Size: {len(report_content)} bytes")
    print(f"\nDone!")


if __name__ == "__main__":
    main()
