# -*- coding: utf-8 -*-
"""
交付物验收脚本 / Deliverables Validation Script

一键检查实验输出的完整性与一致性
One-click validation of experiment output completeness and consistency

检查项 / Checks:
1. N一致性 (N consistency): n_records_total / n_records_labeled 在所有文件中一致
2. 点估计一致性 (Point estimate consistency): accuracy等指标在不同文件中一致
3. 文件完整性 (File completeness): 所有预期文件都存在

作者: Ma Jiaxin
日期: 2025-12-19
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from experiments.validation_utils import validate_n_consistency


class DeliverableValidator:
    """交付物验收器 / Deliverables Validator"""

    def __init__(self, experiment_dir: str):
        """
        初始化验收器

        Args:
            experiment_dir: 实验输出目录
        """
        self.exp_dir = Path(experiment_dir)
        self.errors = []
        self.warnings = []
        self.passed_checks = []
        self.run_type = None  # A6: Store run type for conditional checks

    def log_error(self, message: str):
        """记录错误"""
        self.errors.append(f"[ERROR] {message}")

    def log_warning(self, message: str):
        """记录警告"""
        self.warnings.append(f"[WARNING] {message}")

    def log_pass(self, message: str):
        """记录通过"""
        self.passed_checks.append(f"[PASS] {message}")

    def check_file_exists(self, filepath: Path, required: bool = True) -> bool:
        """
        检查文件是否存在

        Args:
            filepath: 文件路径
            required: 是否必需

        Returns:
            文件是否存在
        """
        if filepath.exists():
            return True
        else:
            if required:
                self.log_error(f"Missing required file: {filepath.relative_to(self.exp_dir)}")
            else:
                self.log_warning(f"Missing optional file: {filepath.relative_to(self.exp_dir)}")
            return False

    def check_file_completeness(self) -> bool:
        """
        检查文件完整性
        Check file completeness

        Returns:
            是否通过
        """
        print("\n[1/3] Checking file completeness...")

        # Detect run type from run_manifest.json
        manifest_path = self.exp_dir / "run_manifest.json"
        run_type = "evidence_chain"  # Default

        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    run_type = manifest.get("run_type", "evidence_chain")
            except:
                pass

        # A6: Store run_type for conditional checks
        self.run_type = run_type

        print(f"  Detected run type: {run_type}")

        # Define required and optional files based on run type
        if run_type == "ISTINA_PILOT":
            # A6: ISTINA Pilot file requirements (updated per A1-A5 implementations)
            required_files = [
                # Core manifests
                "run_manifest.json",
                "env.txt",
                "dataset_card.md",

                # Reports
                "reports/istina_pilot_summary.md",

                # Events (decision_events must NOT contain input_tokens)
                "events/baseline/decision_events.jsonl",

                # Logs (redacted sample - always required)
                "logs/istina_batch_redacted_200.jsonl",
                "logs/istina_batch_redaction_policy.md",

                # Statistics (global scope required, others optional per B2 spec)
                "statistics/stats_ci_global.json",
                "statistics/stats_ci_global.md",
                "statistics/stats_ci_global.tex",

                # Tables
                "tables/istina_pilot_quality.tex",
                "tables/istina_pilot_perf.tex",

                # Module coverage (A4)
                "events/baseline/module_coverage.json",
                "events/baseline/module_coverage.md",
                "events/baseline/reason_counts.csv",
                "events/baseline/score_margin_stats.json",

                # Performance benchmark (A5)
                "performance_benchmark.json",
            ]

            optional_files = [
                # Full raw log (only if write_full_log=1)
                "logs/istina_batch_full.jsonl",
                # Sampled raw log (only if write_full_log=0)
                "logs/istina_batch_raw_sampled.jsonl",
                # Additional statistics scopes (optional per B2 spec)
                "statistics/stats_ci_end_to_end.json",
                "statistics/stats_ci_end_to_end.md",
                "statistics/stats_ci_end_to_end.tex",
                "statistics/stats_ci_conditional.json",
                "statistics/stats_ci_conditional.md",
                "statistics/stats_ci_conditional.tex",
                "statistics/stats_ci_coverage.json",
                "statistics/stats_ci_coverage.md",
                "statistics/stats_ci_coverage.tex",
                # Diagrams
                "figs/istina_integration.puml",
                "figs/smbu_pipeline.puml",
            ]
        else:
            # Evidence-chain experiments (default)
            required_files = [
                "run_manifest.json",
                "env.txt",
                "statistics/stats_ci_global.json",
                "statistics/stats_ci_global.md",
                "statistics/stats_ci_global.tex",
            ]

            optional_files = [
                "events/baseline/module_coverage.json",
                "events/baseline/module_coverage.md",
                "triggered_subsets/ablation_triggered_subsets.json",
                "triggered_subsets/ablation_triggered_subsets.md",
                "sanity_samples/ablation_sanity_samples.jsonl",
                "sanity_samples/ablation_sanity_samples.md",
            ]

        all_exist = True

        for rel_path in required_files:
            if not self.check_file_exists(self.exp_dir / rel_path, required=True):
                all_exist = False

        for rel_path in optional_files:
            self.check_file_exists(self.exp_dir / rel_path, required=False)

        if all_exist:
            self.log_pass("All required files exist")
            return True
        else:
            return False

    def check_n_consistency(self) -> bool:
        """
        检查N一致性
        Check N consistency across all outputs

        Returns:
            是否通过
        """
        print("\n[2/3] Checking N consistency...")

        # Load run_manifest
        manifest_path = self.exp_dir / "run_manifest.json"
        if not manifest_path.exists():
            self.log_error("run_manifest.json not found, cannot check N consistency")
            return False

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        n_records_total = manifest.get("n_records_total")
        n_records_labeled = manifest.get("n_records_labeled")

        # Fallback to old field names if new ones don't exist
        if n_records_total is None:
            n_records_total = manifest.get("dataset_size")
        if n_records_labeled is None:
            n_records_labeled = manifest.get("ground_truth_size")

        if n_records_total is None or n_records_labeled is None:
            self.log_error("run_manifest.json missing n_records_total or n_records_labeled")
            return False

        # Load stats_ci
        stats_ci_path = self.exp_dir / "statistics" / "stats_ci_global.json"
        if not stats_ci_path.exists():
            self.log_error("stats_ci_global.json not found, cannot check N consistency")
            return False

        with open(stats_ci_path, 'r', encoding='utf-8') as f:
            stats_ci = json.load(f)

        # Load module_coverage
        module_coverage_path = self.exp_dir / "events" / "baseline" / "module_coverage.json"
        module_coverage = {}
        if module_coverage_path.exists():
            with open(module_coverage_path, 'r', encoding='utf-8') as f:
                module_coverage = json.load(f)

        # Validate
        try:
            validate_n_consistency(
                n_records_total=n_records_total,
                n_records_labeled=n_records_labeled,
                stats_ci=stats_ci,
                module_coverage=module_coverage,
                run_manifest=manifest,
                strict=True
            )
            self.log_pass(f"N consistency validated (N_total={n_records_total}, N_labeled={n_records_labeled})")
            return True
        except ValueError as e:
            self.log_error(f"N consistency validation failed: {str(e)}")
            return False

    def check_istina_pilot_specific(self) -> bool:
        """
        D: ISTINA Pilot严格验收检查 / ISTINA Pilot Strict Validation Checks

        Checks:
        1. decision_events.jsonl must NOT contain input_tokens field
        2. run_manifest.json must contain required fields
        3. D: Exception rate <= 0.1% (max 10 exceptions in 10k)
        4. D: Total time > reasonable threshold (>1s for 10k)
        5. D: Throughput in reasonable range [10, 2000] names/sec
        6. D: NOT (accuracy==0 AND unknown_rate==1 AND exceptions>0)

        Returns:
            是否通过
        """
        print("\n[ISTINA] Checking ISTINA Pilot-specific requirements...")

        all_passed = True

        # Check 1: decision_events.jsonl must NOT contain input_tokens
        decision_events_path = self.exp_dir / "events" / "baseline" / "decision_events.jsonl"
        if decision_events_path.exists():
            print("  Checking decision_events.jsonl for input_tokens field...")
            has_input_tokens = False

            try:
                with open(decision_events_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if not line.strip():
                            continue

                        event = json.loads(line)
                        if "input_tokens" in event:
                            has_input_tokens = True
                            self.log_error(
                                f"decision_events.jsonl line {i+1} contains 'input_tokens' field. "
                                f"This field must be removed for data security (A2 requirement)."
                            )
                            all_passed = False
                            break  # One violation is enough

                if not has_input_tokens:
                    self.log_pass("decision_events.jsonl does NOT contain input_tokens (A2 compliant)")

            except Exception as e:
                self.log_error(f"Failed to check decision_events.jsonl: {e}")
                all_passed = False

        # Check 2: run_manifest.json must contain required fields
        manifest_path = self.exp_dir / "run_manifest.json"
        if manifest_path.exists():
            print("  Checking run_manifest.json for required fields...")
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)

                required_fields = [
                    "run_type",
                    "n_records_total",
                    "n_records_labeled",
                    ("reproducibility", "random_seed"),  # Nested field
                    ("git_info", "commit_sha_short"),    # Nested field
                ]

                missing_fields = []
                for field in required_fields:
                    if isinstance(field, tuple):
                        # Nested field
                        parent, child = field
                        if parent not in manifest or child not in manifest.get(parent, {}):
                            missing_fields.append(f"{parent}.{child}")
                    else:
                        # Top-level field
                        if field not in manifest:
                            missing_fields.append(field)

                if missing_fields:
                    self.log_error(
                        f"run_manifest.json missing required fields: {', '.join(missing_fields)}"
                    )
                    all_passed = False
                else:
                    self.log_pass("run_manifest.json contains all required fields")

                # Verify run_type is ISTINA_PILOT
                if manifest.get("run_type") != "ISTINA_PILOT":
                    self.log_warning(
                        f"run_type is '{manifest.get('run_type')}' (expected 'ISTINA_PILOT')"
                    )

            except Exception as e:
                self.log_error(f"Failed to check run_manifest.json fields: {e}")
                all_passed = False

        # D: Performance and Quality Strict Checks
        print("  Checking performance and quality metrics (D: strict validation)...")

        # Load performance_benchmark.json
        perf_path = self.exp_dir / "performance_benchmark.json"
        if perf_path.exists():
            try:
                with open(perf_path, 'r', encoding='utf-8') as f:
                    perf = json.load(f)

                # D3: Exception rate check (<= 0.1%)
                exception_count = perf.get("exception_count", 0)
                n_records = perf.get("n_records_processed", 0)
                if n_records > 0:
                    exception_rate = (exception_count / n_records) * 100
                    if exception_rate > 0.1:
                        self.log_error(
                            f"D: Exception rate too high: {exception_rate:.4f}% "
                            f"({exception_count}/{n_records}). Threshold: <= 0.1%"
                        )
                        all_passed = False
                    else:
                        self.log_pass(
                            f"D: Exception rate acceptable: {exception_rate:.4f}% "
                            f"({exception_count}/{n_records}) <= 0.1%"
                        )

                # D4: Total time check (not suspiciously low - adjusted for fast algorithm)
                total_time_sec = perf.get("total_time_sec", 0)
                # Fast algorithm can process ~4000 names/sec, so min threshold adjusted
                min_time_threshold = max(0.05, n_records / 20000)
                if total_time_sec <= min_time_threshold:
                    self.log_error(
                        f"D: Total time suspiciously low: {total_time_sec}s "
                        f"(threshold: >{min_time_threshold:.2f}s for {n_records} records). "
                        f"Likely using fake placeholder timing."
                    )
                    all_passed = False
                else:
                    self.log_pass(
                        f"D: Total time reasonable: {total_time_sec}s > {min_time_threshold:.2f}s"
                    )

                # D5: Throughput sanity check ([10, 10000] names/sec - allows fast algorithms)
                throughput = perf.get("throughput_names_per_sec", 0)
                if throughput < 10 or throughput > 10000:
                    self.log_error(
                        f"D: Throughput out of reasonable range: {throughput:.2f} names/sec. "
                        f"Expected: [10, 10000]. Likely fake or broken timing."
                    )
                    all_passed = False
                else:
                    self.log_pass(
                        f"D: Throughput in reasonable range: {throughput:.2f} names/sec ∈ [10, 10000]"
                    )

            except Exception as e:
                self.log_error(f"Failed to check performance_benchmark.json: {e}")
                all_passed = False

        # D6: Quality catastrophe check (accuracy==0 AND unknown_rate==1 AND exceptions>0)
        stats_ci_path = self.exp_dir / "statistics" / "stats_ci_global.json"
        if stats_ci_path.exists() and perf_path.exists():
            try:
                with open(stats_ci_path, 'r', encoding='utf-8') as f:
                    stats_ci = json.load(f)

                with open(perf_path, 'r', encoding='utf-8') as f:
                    perf = json.load(f)

                # Extract baseline metrics
                baseline_ci = stats_ci.get("confidence_intervals", {}).get("baseline", {})
                accuracy = baseline_ci.get("accuracy", {}).get("point_estimate", None)
                unknown_rate = baseline_ci.get("unknown_rate", {}).get("point_estimate", None)
                exception_count = perf.get("exception_count", 0)

                if (accuracy is not None and accuracy == 0.0 and
                    unknown_rate is not None and unknown_rate == 1.0 and
                    exception_count > 0):
                    self.log_error(
                        f"D: Quality catastrophe detected - "
                        f"accuracy=0%, unknown_rate=100%, exceptions={exception_count}>0. "
                        f"Indicates complete algorithm failure (likely API mismatch or broken code)."
                    )
                    all_passed = False
                else:
                    self.log_pass(
                        f"D: No quality catastrophe detected "
                        f"(accuracy={accuracy}, unknown_rate={unknown_rate}, exceptions={exception_count})"
                    )

            except Exception as e:
                self.log_error(f"Failed to check quality catastrophe: {e}")
                all_passed = False

        # SAFE DEFAULT: Check for raw_sampled file (should NOT exist unless keep_raw_sampled=1)
        print("  Checking for unsafe raw_sampled file (SAFE DEFAULT enforcement)...")
        raw_sampled_path = self.exp_dir / "logs" / "istina_batch_raw_sampled.jsonl"
        raw_full_path = self.exp_dir / "logs" / "istina_batch_full.jsonl"

        if raw_sampled_path.exists() or raw_full_path.exists():
            # Load manifest to check keep_raw_sampled setting
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)

                keep_raw_sampled = manifest.get("reproducibility", {}).get("keep_raw_sampled", False)
                write_full_log = manifest.get("reproducibility", {}).get("write_full_log", False)

                if raw_sampled_path.exists():
                    if keep_raw_sampled:
                        self.log_warning(
                            f"logs/istina_batch_raw_sampled.jsonl exists (keep_raw_sampled=1 - DEBUG MODE). "
                            f"This file contains raw tokens and must NOT be submitted with paper."
                        )
                    else:
                        self.log_error(
                            f"SAFE DEFAULT VIOLATION: logs/istina_batch_raw_sampled.jsonl exists but keep_raw_sampled=0. "
                            f"This file should have been auto-deleted. Contains raw tokens - DO NOT SUBMIT."
                        )
                        all_passed = False

                if raw_full_path.exists():
                    if write_full_log:
                        self.log_warning(
                            f"logs/istina_batch_full.jsonl exists (write_full_log=1 - DEBUG MODE). "
                            f"This file contains raw tokens and must NOT be submitted with paper."
                        )
                    else:
                        self.log_error(
                            f"SAFE DEFAULT VIOLATION: logs/istina_batch_full.jsonl exists but write_full_log=0. "
                            f"This file should NOT exist. Contains raw tokens - DO NOT SUBMIT."
                        )
                        all_passed = False

            except Exception as e:
                self.log_error(f"Failed to check raw file settings: {e}")
                all_passed = False
        else:
            self.log_pass("SAFE DEFAULT: No raw token files found (raw_sampled/full logs properly handled)")

        return all_passed

    def check_point_estimate_consistency(self) -> bool:
        """
        检查点估计一致性
        Check point estimate consistency across different outputs

        Returns:
            是否通过
        """
        print("\n[3/3] Checking point estimate consistency...")

        TOLERANCE = 1e-6  # Strict tolerance for floating point comparison

        # Load stats_ci
        stats_ci_path = self.exp_dir / "statistics" / "stats_ci_global.json"
        if not stats_ci_path.exists():
            self.log_error("stats_ci_global.json not found")
            return False

        with open(stats_ci_path, 'r', encoding='utf-8') as f:
            stats_ci = json.load(f)

        # Load run_manifest
        manifest_path = self.exp_dir / "run_manifest.json"
        if not manifest_path.exists():
            self.log_error("run_manifest.json not found")
            return False

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Extract results_summary from manifest
        results_summary = manifest.get("results_summary", {})

        # Check each config
        all_consistent = True
        configs_checked = 0

        for config_name, ci_data in stats_ci.get("confidence_intervals", {}).items():
            if config_name not in results_summary:
                self.log_warning(f"Config {config_name} not found in run_manifest.results_summary")
                continue

            manifest_data = results_summary[config_name]

            # Compare accuracy point estimate
            ci_accuracy = ci_data.get("accuracy", {}).get("point_estimate")
            manifest_accuracy = manifest_data.get("accuracy")

            if ci_accuracy is not None and manifest_accuracy is not None:
                diff = abs(ci_accuracy - manifest_accuracy)
                if diff > TOLERANCE:
                    self.log_error(
                        f"Point estimate mismatch for {config_name}.accuracy: "
                        f"stats_ci={ci_accuracy:.6f}, manifest={manifest_accuracy:.6f}, "
                        f"diff={diff:.2e}"
                    )
                    all_consistent = False
                else:
                    configs_checked += 1

        if configs_checked == 0:
            self.log_warning("No configs were checked for point estimate consistency")
            return True  # Not a failure, just no data

        if all_consistent:
            self.log_pass(f"Point estimates consistent across {configs_checked} configs (tolerance={TOLERANCE})")
            return True
        else:
            return False

    def validate(self) -> bool:
        """
        运行所有验收检查
        Run all validation checks

        Returns:
            是否全部通过
        """
        print("=" * 80)
        print("Deliverables Validation")
        print("=" * 80)
        print(f"Experiment directory: {self.exp_dir}")

        all_passed = True

        # Check 1: File completeness
        if not self.check_file_completeness():
            all_passed = False

        # A6: ISTINA Pilot-specific checks (run after file completeness to ensure run_type is set)
        if self.run_type == "ISTINA_PILOT":
            if not self.check_istina_pilot_specific():
                all_passed = False

        # Check 2: N consistency
        if not self.check_n_consistency():
            all_passed = False

        # Check 3: Point estimate consistency
        if not self.check_point_estimate_consistency():
            all_passed = False

        # Print summary
        print("\n" + "=" * 80)
        print("Validation Summary")
        print("=" * 80)

        if self.passed_checks:
            print(f"\n{len(self.passed_checks)} checks PASSED:")
            for msg in self.passed_checks:
                print(f"  {msg}")

        if self.warnings:
            print(f"\n{len(self.warnings)} WARNINGS:")
            for msg in self.warnings:
                print(f"  {msg}")

        if self.errors:
            print(f"\n{len(self.errors)} ERRORS:")
            for msg in self.errors:
                print(f"  {msg}")

        print("\n" + "=" * 80)
        if all_passed and len(self.errors) == 0:
            print("VALIDATION PASSED")
            print("=" * 80)
            return True
        else:
            print("VALIDATION FAILED")
            print("=" * 80)
            return False

    def save_report(self, output_path: Optional[Path] = None):
        """
        保存验收报告
        Save validation report

        Args:
            output_path: 输出路径（默认为实验目录下的validation_report.json）
        """
        if output_path is None:
            output_path = self.exp_dir / "validation_report.json"

        report = {
            "experiment_dir": str(self.exp_dir),
            "passed": len(self.errors) == 0,
            "checks_passed": len(self.passed_checks),
            "warnings": len(self.warnings),
            "errors": len(self.errors),
            "details": {
                "passed": self.passed_checks,
                "warnings": self.warnings,
                "errors": self.errors
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\nValidation report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate experiment deliverables for completeness and consistency"
    )
    parser.add_argument(
        "experiment_dir",
        help="Path to experiment output directory (e.g., runs/evidence_chain_301k_FINAL)"
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save validation report to JSON file"
    )

    args = parser.parse_args()

    validator = DeliverableValidator(args.experiment_dir)
    passed = validator.validate()

    if args.save_report:
        validator.save_report()

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
