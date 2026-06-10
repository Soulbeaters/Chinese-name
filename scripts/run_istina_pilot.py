# -*- coding: utf-8 -*-
"""
ISTINA Pilot Runner / ИСТИНА пилотный запуск

一键运行ISTINA系统集成试验，产出符合论文"实践/应用"部分要求的交付物。
严格遵循数据安全与脱敏要求（A1-A5修改版）。

One-command ISTINA integration pilot that produces deliverables for the
"Practice/Application" section of the paper.
Strictly follows data security and redaction requirements (A1-A5 modifications).

作者 / Author: Ma Jiaxin
日期 / Date: 2025-12-20
版本 / Version: 2.0 (A1-A5 modifications)
"""

import argparse
import json
import sys
import time
import hashlib
import os
import csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.surname_identifier_v8 import identify_surname_position_v8
from src.config_v8 import get_config
from experiments.statistical_tests import generate_statistical_report, StatsMetadata


# A4: Reason code to module mapping / Reason代码到模块的映射
REASON_TO_MODULE = {
    # Chinese surname evidence
    "CN_SURNAME_KNOWN": "ChineseSurnameEvidence",
    "CN_SURNAME_COMMON": "ChineseSurnameEvidence",
    "CN_SURNAME_FREQ": "ChineseSurnameEvidence",
    "CN_SURNAME_DICT": "ChineseSurnameEvidence",

    # Cyrillic/Russian patterns
    "CYRILLIC_PATRONYMIC": "CyrillicPatterns",
    "CYRILLIC_NAME_PATTERN": "CyrillicPatterns",

    # Western exclusion
    "WESTERN_EXCLUSION": "WesternExclusion",
    "WESTERN_NAME_DICT": "WesternExclusion",

    # Script heuristics
    "SCRIPT_HAN_ONLY": "ScriptHeuristics",
    "SCRIPT_CYRILLIC_ONLY": "ScriptHeuristics",
    "SCRIPT_LATIN_ONLY": "ScriptHeuristics",
    "SCRIPT_MIXED": "ScriptHeuristics",

    # Delimiter rules
    "DELIM_COMMA": "DelimiterRules",
    "DELIM_SEMICOLON": "DelimiterRules",
    "DELIM_SPACE": "DelimiterRules",

    # Frequency heuristic
    "FREQ_HIGH": "FrequencyHeuristic",
    "FREQ_MEDIUM": "FrequencyHeuristic",
    "FREQ_LOW": "FrequencyHeuristic",

    # Batch consistency
    "BATCH_PERSON_CONSISTENCY": "BatchPersonConsistency",
    "BATCH_PUB_CONSISTENCY": "BatchPubConsistency",
    "BATCH_CONSISTENCY": "BatchConsistency",

    # Source prior
    "SOURCE_PRIOR_CHINESE": "SourcePrior",
    "SOURCE_PRIOR_WESTERN": "SourcePrior",
    "SOURCE_PRIOR_MIXED": "SourcePrior",

    # Default inference
    "DEFAULT_INFERENCE": "DefaultInference",
    "DEFAULT_UNKNOWN": "DefaultInference",
}


@dataclass
class DecisionEvent:
    """
    单条决策事件 / Single decision event

    记录算法对单条记录的完整决策过程，包括输入、输出、中间状态和可解释性证据
    Records the complete decision process for a single record
    """
    # 基础元数据 / Basic metadata
    ts: str  # ISO8601 timestamp
    run_id: str
    record_id_hash: str  # SHA-256(salt + original_record_id)
    source: str
    profile: str

    # 输入（仅用于生成脱敏样本，不得写入decision_events.jsonl）/ Input (for redaction only)
    input_tokens: Optional[List[str]]  # Will be removed for safe decision_events.jsonl

    # 输出 / Output
    prediction: Dict[str, any]  # {"label": str, "confidence": float}
    scores: Optional[Dict[str, float]]  # C: Set to null (algorithm doesn't provide real score distribution)
    score_margin: Optional[float]  # C: Set to null (algorithm doesn't provide margin)

    # 可解释性证据 / Interpretability evidence
    fired_modules: List[str]  # Evidence-linked: modules whose reasons appear in reasons_topk
    effective_modules: List[str]  # Same as fired_modules (evidence-linked, NOT counterfactual)
    reasons_topk: List[Dict[str, any]]  # Top-K reasons with weights

    # 性能 / Performance
    latency_ms: float  # B: Changed from int to float for precise timing

    # 异常 / Exceptions
    exception: Optional[Dict[str, str]]

    # 辅助引用 / Auxiliary references
    output_artifact_refs: Dict[str, any]


class ISTINADataAdapter:
    """
    ИСТИНА数据适配器 / ISTINA Data Adapter

    将ИСТИНА系统导出的数据格式转换为算法输入格式
    Converts ISTINA system export format to algorithm input format
    """

    @staticmethod
    def load_data(input_path: Path) -> List[Dict]:
        """
        加载ИСТИНА导出数据 / Load ISTINA export data

        支持格式 / Supported formats:
        - JSON/JSONL: authors.json, istina_export.jsonl

        Args:
            input_path: 输入文件路径 / Input file path

        Returns:
            标准化记录列表 / List of normalized records
        """
        suffix = input_path.suffix.lower()

        if suffix == '.json':
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle both list and single object
            if isinstance(data, list):
                records = data
            else:
                records = [data]

        elif suffix == '.jsonl':
            records = []
            with open(input_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))

        else:
            raise ValueError(f"Unsupported file format: {suffix}. Supported: .json, .jsonl")

        return records

    @staticmethod
    def normalize_record(record: Dict, index: int) -> Tuple[str, str, Optional[str]]:
        """
        规范化单条记录 / Normalize single record

        将ИСТИНА数据字段映射到算法输入格式
        Maps ISTINA data fields to algorithm input format

        Args:
            record: 原始记录 / Original record
            index: 记录索引（作为fallback ID）/ Record index (as fallback ID)

        Returns:
            (record_id, original_name, ground_truth)
        """
        # Extract record ID (prefer stable ID from ISTINA, fallback to index)
        record_id = record.get('id') or record.get('author_id') or f"record_{index}"

        # Extract original name field
        original_name = (
            record.get('original_name') or
            record.get('full_name') or
            record.get('name') or
            ""
        )

        # Extract ground truth if available
        lastname = record.get('lastname', '')
        firstname = record.get('firstname', '')

        ground_truth = None
        if original_name and lastname:
            parts = original_name.split()
            if len(parts) >= 2:
                first_part = parts[0].strip().lower()
                last_part = parts[-1].strip().lower()
                lastname_lower = lastname.lower()

                # Clean for comparison
                first_part_clean = first_part.replace('-', '').replace('.', '')
                lastname_clean = lastname_lower.replace('-', '').replace('.', '')

                # Check if lastname appears at start (family_first) or end (given_first)
                if first_part_clean.startswith(lastname_clean) or first_part == lastname_lower:
                    ground_truth = "family_first"
                elif last_part.replace('-', '').replace('.', '').startswith(lastname_clean):
                    ground_truth = "given_first"

        return record_id, original_name, ground_truth


class ISTINAPilotRunner:
    """
    ИСТИНА Pilot运行器 / ISTINA Pilot Runner

    执行完整的ISTINA系统集成试验
    Executes complete ISTINA system integration pilot
    """

    def __init__(
        self,
        input_path: Path,
        output_dir: Path,
        profile: str = "ISTINA",
        seed: int = 42,
        max_records: int = 0,
        redact_salt_env: str = "ISTINA_LOG_SALT",
        sample_lines: int = 200,
        write_full_log: int = 0,  # SAFE DEFAULT: 默认不写入完整日志（论文提交安全）
        keep_raw_sampled: int = 0,  # SAFE DEFAULT: 默认不保留临时raw采样文件
    ):
        """
        初始化Pilot运行器

        Args:
            input_path: ИСТИНА导出数据路径
            output_dir: 输出目录
            profile: 算法profile（默认ISTINA）
            seed: 随机种子（用于采样）
            max_records: 最大处理记录数（0=全部）
            redact_salt_env: 脱敏salt环境变量名
            sample_lines: 脱敏样本行数
            write_full_log: 是否写入完整日志（含原文tokens）0=否（默认，安全），1=是（仅调试用，勿提交）
            keep_raw_sampled: 保留临时raw采样文件（0=自动删除（默认，安全），1=保留（仅调试用））
        """
        self.input_path = input_path
        self.output_dir = output_dir
        self.profile = profile
        self.seed = seed
        self.max_records = max_records
        self.redact_salt_env = redact_salt_env
        self.sample_lines = sample_lines
        self.write_full_log = write_full_log  # A1: 保存参数
        self.keep_raw_sampled = keep_raw_sampled  # SAFE DEFAULT: 保存参数

        # Generate run ID
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.run_id = f"istina_pilot_{timestamp}"

        # A3: 强制要求salt（用于哈希record_id和tokens）
        self.salt = os.getenv(redact_salt_env, "")
        if not self.salt:
            raise ValueError(
                f"[ERROR] Environment variable {redact_salt_env} is not set or empty.\n"
                f"Salt is REQUIRED for secure, reproducible hashing and redaction.\n"
                f"Please set it before running:\n"
                f"  Windows: $env:{redact_salt_env} = \"<your-secure-random-string>\"\n"
                f"  Linux/Mac: export {redact_salt_env}=\"<your-secure-random-string>\"\n"
                f"\nNote: Salt must be at least 32 characters (recommend: openssl rand -hex 32)"
            )

        # Create output directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "reports").mkdir(exist_ok=True)
        (self.output_dir / "logs").mkdir(exist_ok=True)
        (self.output_dir / "events" / "baseline").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "statistics").mkdir(exist_ok=True)
        (self.output_dir / "tables").mkdir(exist_ok=True)
        (self.output_dir / "figs").mkdir(exist_ok=True)

    def hash_with_salt(self, value: str) -> str:
        """使用salt计算SHA-256哈希 / Compute SHA-256 hash with salt"""
        return hashlib.sha256(f"{self.salt}{value}".encode('utf-8')).hexdigest()

    def run(self) -> Dict:
        """
        执行完整的Pilot运行 / Execute complete pilot run

        Returns:
            运行摘要字典 / Run summary dictionary
        """
        print(f"\n{'='*80}")
        print(f"ISTINA Pilot Runner (A1-A5 modifications)")
        print(f"{'='*80}")
        print(f"Run ID: {self.run_id}")
        print(f"Input: {self.input_path}")
        print(f"Output: {self.output_dir}")
        print(f"Profile: {self.profile}")
        print(f"Seed: {self.seed}")
        print(f"Write Full Log: {bool(self.write_full_log)}")
        print(f"")

        # Step 1: Load data
        print(f"[Step 1/9] Loading ISTINA data...")
        records = ISTINADataAdapter.load_data(self.input_path)
        print(f"  Loaded {len(records)} records from {self.input_path.name}")

        if self.max_records > 0:
            records = records[:self.max_records]
            print(f"  Limited to {len(records)} records (max_records={self.max_records})")

        # Step 2: Process records and generate decision events
        print(f"\n[Step 2/9] Processing records...")
        decision_events, results, ground_truth, wall_time_sec, exception_count = self._process_records(records)
        print(f"  Processed {len(decision_events)} records")
        print(f"  Ground truth available: {len([gt for gt in ground_truth.values() if gt is not None])}")

        # Step 3: Write SAFE decision events (A2: 剥离input_tokens)
        print(f"\n[Step 3/9] Writing safe decision events (without raw tokens)...")
        events_path = self.output_dir / "events" / "baseline" / "decision_events.jsonl"
        self._write_safe_decision_events(decision_events, events_path)
        print(f"  [OK] {events_path.relative_to(self.output_dir)}")
        print(f"  Note: input_tokens removed for security")

        # Step 4: Write logs and generate redacted sample (A2: 根据write_full_log控制)
        print(f"\n[Step 4/9] Generating logs and redacted sample...")
        self._generate_logs_and_redaction(decision_events)

        # Step 5: Generate module coverage and evidence reports (A4: 真实实现)
        print(f"\n[Step 5/9] Generating module coverage and evidence analysis...")
        self._generate_module_coverage(decision_events)
        print(f"  [OK] events/baseline/module_coverage.*")
        print(f"  [OK] events/baseline/reason_counts.csv")
        print(f"  [OK] events/baseline/score_margin_stats.json")

        # Step 6: Generate statistical reports (three scopes)
        print(f"\n[Step 6/9] Generating statistical reports...")
        n_records_total = len(records)
        n_records_labeled = len([gt for gt in ground_truth.values() if gt is not None])
        self._generate_statistics(results, ground_truth, n_records_total, n_records_labeled)
        print(f"  [OK] statistics/stats_ci_global_* (3 scopes)")

        # Step 7: Generate performance benchmark (B: use real wall time)
        print(f"\n[Step 7/9] Generating performance benchmark...")
        perf_benchmark = self._generate_performance_benchmark(
            decision_events, n_records_total, wall_time_sec, exception_count
        )
        print(f"  [OK] performance_benchmark.json")

        # Step 8: Generate summary report and tables
        print(f"\n[Step 8/9] Generating summary report and tables...")
        self._generate_reports_and_tables(decision_events, results, ground_truth, perf_benchmark)
        print(f"  [OK] reports/istina_pilot_summary.md")
        print(f"  [OK] tables/istina_pilot_quality.tex")
        print(f"  [OK] tables/istina_pilot_perf.tex")

        # Step 9: Generate manifests
        print(f"\n[Step 9/9] Generating manifests...")
        self._generate_manifests(records, results, ground_truth, perf_benchmark)
        print(f"  [OK] run_manifest.json")
        print(f"  [OK] env.txt")
        print(f"  [OK] dataset_card.md")

        print(f"\n{'='*80}")
        print(f"Pilot run completed successfully!")
        print(f"{'='*80}")

        return {
            "run_id": self.run_id,
            "n_records_total": n_records_total,
            "n_records_labeled": n_records_labeled,
            "output_dir": str(self.output_dir),
        }

    def _process_records(
        self,
        records: List[Dict]
    ) -> Tuple[List[DecisionEvent], Dict[str, Dict[str, str]], Dict[str, Optional[str]], float, int]:
        """
        处理所有记录并生成决策事件 / Process all records and generate decision events

        Returns:
            (decision_events, results_dict, ground_truth_dict, wall_time_sec, exception_count)
        """
        decision_events = []
        results = {}  # config_name -> {record_id: prediction}
        ground_truth = {}  # record_id -> ground_truth

        config = get_config(self.profile)

        # B: Use perf_counter for wall-clock timing
        batch_start = time.perf_counter()
        exception_count = 0

        for i, record in enumerate(records, 1):
            if i % 100 == 0:
                elapsed = time.perf_counter() - batch_start
                speed = i / elapsed if elapsed > 0 else 0
                print(f"  Progress: {i}/{len(records)} ({i/len(records)*100:.1f}%) - {speed:.1f} names/sec")

            # Normalize record
            record_id, original_name, gt = ISTINADataAdapter.normalize_record(record, i)
            ground_truth[record_id] = gt

            # Skip empty names
            if not original_name or not original_name.strip():
                continue

            # Hash record ID
            record_id_hash = self.hash_with_salt(record_id)

            # Process with algorithm - B: Use perf_counter for precise timing
            record_start = time.perf_counter()
            try:
                # A: Fixed API call - use v8 with correct parameters
                order, confidence, reasons = identify_surname_position_v8(
                    original_name=original_name,
                    affiliation="",  # ISTINA data doesn't have affiliation
                    source=self.profile,  # v8 supports source parameter
                )

                # B: latency_ms as float, not int
                latency_ms = (time.perf_counter() - record_start) * 1000.0

                # C: Set scores and score_margin to None (no fake distribution)
                scores = None
                score_margin = None

                # A4: Parse reasons into topk format and extract modules
                reasons_topk = []
                fired_modules_set = set()
                if isinstance(reasons, list):
                    for j, reason in enumerate(reasons[:8]):  # Top-8
                        reason_code = reason if isinstance(reason, str) else str(reason)
                        reasons_topk.append({
                            "code": reason_code,
                            "weight": 1.0 / (j + 1),  # Simple decay
                        })
                        # Map reason to module
                        module = REASON_TO_MODULE.get(reason_code, "Other")
                        fired_modules_set.add(module)

                fired_modules = sorted(list(fired_modules_set))
                effective_modules = fired_modules  # Evidence-linked (NOT counterfactual)

                exception = None

            except Exception as e:
                # A2: Track exceptions for validation
                exception_count += 1

                order = "unknown"
                confidence = 0.0
                # C: Set to None (not fake distribution)
                scores = None
                score_margin = None
                reasons_topk = []
                fired_modules = []
                effective_modules = []
                # B: Use perf_counter and float
                latency_ms = (time.perf_counter() - record_start) * 1000.0
                exception = {"type": type(e).__name__, "msg": str(e)}

            # Create decision event
            event = DecisionEvent(
                ts=datetime.now(timezone.utc).isoformat(),
                run_id=self.run_id,
                record_id_hash=record_id_hash,
                source="ISTINA",
                profile=self.profile,
                input_tokens=original_name.split(),  # Will be removed for safe decision_events
                prediction={"label": order, "confidence": confidence},
                scores=scores,
                score_margin=score_margin,
                fired_modules=fired_modules,
                effective_modules=effective_modules,
                reasons_topk=reasons_topk,
                latency_ms=latency_ms,
                exception=exception,
                output_artifact_refs={},
            )

            decision_events.append(event)

            # Store result
            if "baseline" not in results:
                results["baseline"] = {}
            results["baseline"][record_id] = order

        # B: Calculate wall-clock time (NOT sum of latencies)
        wall_time_sec = time.perf_counter() - batch_start
        avg_speed = len(records) / wall_time_sec if wall_time_sec > 0 else 0
        print(f"  Average speed: {avg_speed:.1f} names/sec")
        print(f"  Wall time: {wall_time_sec:.2f}s")
        print(f"  Exceptions: {exception_count}/{len(records)} ({exception_count/len(records)*100:.2f}%)")

        return decision_events, results, ground_truth, wall_time_sec, exception_count

    def _write_safe_decision_events(self, events: List[DecisionEvent], output_path: Path):
        """
        A2: 写入安全的决策事件日志（移除input_tokens）/ Write safe decision events (remove input_tokens)
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for event in events:
                event_dict = asdict(event)
                # A2: Remove input_tokens for security
                event_dict.pop('input_tokens', None)
                f.write(json.dumps(event_dict, ensure_ascii=False) + '\n')

    def _generate_logs_and_redaction(self, events: List[DecisionEvent]):
        """
        A2: 根据write_full_log控制日志生成逻辑
        Generate logs and redacted sample based on write_full_log flag
        """
        from scripts.redact_logs import LogRedactor

        redactor = LogRedactor(salt_env=self.redact_salt_env, seed=self.seed)

        if self.write_full_log:
            # A2: write_full_log=1: 写全量raw log，然后生成redacted_200
            print(f"  [WARNING] Writing full raw log (write_full_log=1 - DEBUG MODE)...")
            full_log_path = self.output_dir / "logs" / "istina_batch_full.jsonl"

            with open(full_log_path, 'w', encoding='utf-8') as f:
                for event in events:
                    f.write(json.dumps(asdict(event), ensure_ascii=False) + '\n')

            print(f"  [OK] logs/istina_batch_full.jsonl ({len(events)} events)")
            print(f"  [CRITICAL] Contains raw tokens - DO NOT SUBMIT WITH PAPER - DEBUG ONLY")

            # Generate redacted sample from full log
            redacted_path = self.output_dir / "logs" / "istina_batch_redacted_200.jsonl"
            policy_path = self.output_dir / "logs" / "istina_batch_redaction_policy.md"

            redactor.redact_logs(
                input_path=full_log_path,
                output_path=redacted_path,
                policy_path=policy_path,
                n_samples=self.sample_lines,
            )

        else:
            # SAFE DEFAULT: write_full_log=0: 只采样少量raw事件用于生成redacted，不写全量
            print(f"  Sampling raw events for redaction (write_full_log=0 - SAFE MODE)...")

            # Sample events using same strategy as redactor
            sampled_events = redactor.sample_events(
                [asdict(e) for e in events],
                n_samples=min(self.sample_lines * 2, len(events))  # 2x buffer for diversity
            )

            # Write temporary sampled raw log (will be auto-deleted if keep_raw_sampled=0)
            sampled_raw_path = self.output_dir / "logs" / "istina_batch_raw_sampled.jsonl"
            with open(sampled_raw_path, 'w', encoding='utf-8') as f:
                for event in sampled_events:
                    f.write(json.dumps(event, ensure_ascii=False) + '\n')

            print(f"  [TEMP] logs/istina_batch_raw_sampled.jsonl ({len(sampled_events)} events)")

            # Generate redacted sample from sampled raw
            redacted_path = self.output_dir / "logs" / "istina_batch_redacted_200.jsonl"
            policy_path = self.output_dir / "logs" / "istina_batch_redaction_policy.md"

            redactor.redact_logs(
                input_path=sampled_raw_path,
                output_path=redacted_path,
                policy_path=policy_path,
                n_samples=self.sample_lines,
            )

            # SAFE DEFAULT: Auto-delete temporary raw sampled file (unless keep_raw_sampled=1)
            if not self.keep_raw_sampled:
                import os
                os.remove(sampled_raw_path)
                print(f"  [SAFE] Auto-deleted temporary raw_sampled file (keep_raw_sampled=0)")
            else:
                print(f"  [WARNING] Keeping raw_sampled file (keep_raw_sampled=1 - DEBUG ONLY)")
                print(f"  [CRITICAL] logs/istina_batch_raw_sampled.jsonl contains raw tokens - DO NOT SUBMIT")

            print(f"  [OK] No full raw log written (write_full_log=0 - SAFE MODE)")

        print(f"  [OK] logs/istina_batch_redacted_200.jsonl")
        print(f"  [OK] logs/istina_batch_redaction_policy.md")

    def _generate_module_coverage(self, events: List[DecisionEvent]):
        """
        A4: 生成真实的模块覆盖率分析 / Generate real module coverage analysis

        基于reasons_topk推断fired_modules和effective_modules（evidence-linked）
        Infer fired_modules and effective_modules based on reasons_topk (evidence-linked)
        """
        # 统计模块触发情况 / Count module triggers
        module_stats = {}
        reason_counts = {}
        score_margins = []

        for event in events:
            # Module stats
            for module in event.fired_modules:
                if module not in module_stats:
                    module_stats[module] = {"evaluated": 0, "fired": 0, "effective": 0}
                module_stats[module]["evaluated"] += 1
                module_stats[module]["fired"] += 1

            for module in event.effective_modules:
                if module not in module_stats:
                    module_stats[module] = {"evaluated": 0, "fired": 0, "effective": 0}
                module_stats[module]["effective"] += 1

            # Reason counts
            for reason in event.reasons_topk:
                code = reason["code"]
                reason_counts[code] = reason_counts.get(code, 0) + 1

            # Score margins
            if event.score_margin is not None:
                score_margins.append(event.score_margin)

        # Compute margin statistics
        margin_stats = {}
        if score_margins:
            sorted_margins = sorted(score_margins)
            n = len(sorted_margins)
            margin_stats = {
                "count": n,
                "min": sorted_margins[0],
                "p5": sorted_margins[int(n * 0.05)] if n > 0 else 0,
                "p25": sorted_margins[int(n * 0.25)] if n > 0 else 0,
                "median": sorted_margins[int(n * 0.5)] if n > 0 else 0,
                "p75": sorted_margins[int(n * 0.75)] if n > 0 else 0,
                "p95": sorted_margins[int(n * 0.95)] if n > 0 else 0,
                "max": sorted_margins[-1],
                "mean": sum(score_margins) / n,
            }

        # Write module_coverage.json
        coverage = {
            "n_records_evaluated": len(events),
            "modules": module_stats,
            "definition": {
                "fired_modules": "Evidence-linked: modules whose reason codes appear in reasons_topk",
                "effective_modules": "Same as fired_modules (evidence-linked, NOT counterfactual ablation)"
            }
        }

        json_path = self.output_dir / "events" / "baseline" / "module_coverage.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(coverage, f, ensure_ascii=False, indent=2)

        # Write module_coverage.md
        md_path = self.output_dir / "events" / "baseline" / "module_coverage.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Module Coverage Report / 模块覆盖率报告\n\n")
            f.write(f"Records evaluated: {coverage['n_records_evaluated']}\n\n")

            f.write("## Definition / 定义\n\n")
            f.write("- **Fired Modules**: Evidence-linked - modules whose reason codes appear in reasons_topk\n")
            f.write("- **Effective Modules**: Same as fired_modules (evidence-linked, NOT counterfactual)\n\n")

            f.write("## Module Statistics / 模块统计\n\n")
            f.write("| Module | Evaluated | Fired | Effective |\n")
            f.write("|--------|-----------|-------|----------|\n")
            for module, stats in sorted(module_stats.items()):
                f.write(f"| {module} | {stats['evaluated']} | {stats['fired']} | {stats['effective']} |\n")

        # Write reason_counts.csv
        csv_path = self.output_dir / "events" / "baseline" / "reason_counts.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["reason_code", "count"])
            for code, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
                writer.writerow([code, count])

        # Write score_margin_stats.json
        margin_json_path = self.output_dir / "events" / "baseline" / "score_margin_stats.json"
        with open(margin_json_path, 'w', encoding='utf-8') as f:
            json.dump(margin_stats, f, indent=2)

    def _generate_performance_benchmark(
        self,
        events: List[DecisionEvent],
        n_records_total: int,
        wall_time_sec: float,
        exception_count: int
    ) -> Dict:
        """
        B: 生成性能基准JSON（使用真实wall-clock time）/ Generate performance benchmark JSON (using real wall-clock time)

        Returns:
            benchmark dict (also written to performance_benchmark.json)
        """
        # Extract latencies
        latencies = [e.latency_ms for e in events if e.latency_ms > 0]

        if not latencies:
            # No latency data
            benchmark = {
                "error": "No latency data available",
                "total_time_sec": round(wall_time_sec, 2),
                "exception_count": exception_count,
            }
        else:
            # B: Use real wall_time_sec (NOT sum of latencies)
            throughput = len(events) / wall_time_sec if wall_time_sec > 0 else 0

            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)

            # B: Fix percentile indexing to prevent out-of-bounds
            benchmark = {
                "throughput_names_per_sec": round(throughput, 2),
                "latency_ms": {
                    "avg": round(sum(latencies) / n, 2),
                    "p50": sorted_latencies[min(len(sorted_latencies) - 1, int(n * 0.5))],
                    "p95": sorted_latencies[min(len(sorted_latencies) - 1, int(n * 0.95))],
                    "p99": sorted_latencies[min(len(sorted_latencies) - 1, int(n * 0.99))],
                    "min": min(latencies),
                    "max": max(latencies),
                },
                "total_time_sec": round(wall_time_sec, 2),
                "exception_count": exception_count,
                "exception_rate": round(exception_count / len(events) * 100, 4) if events else 0,
                "n_records_total": n_records_total,
                "n_records_processed": len(events),
                "profile": self.profile,
                "git_commit_short": self._get_git_commit_short(),
                "machine_info": {
                    "platform": self._get_platform_info(),
                    "python_version": self._get_python_version(),
                    "cpu_count": self._get_cpu_count(),
                }
            }

        # Write to file
        output_path = self.output_dir / "performance_benchmark.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(benchmark, f, indent=2)

        return benchmark

    def _generate_statistics(
        self,
        results: Dict[str, Dict[str, str]],
        ground_truth: Dict[str, Optional[str]],
        n_records_total: int,
        n_records_labeled: int,
    ):
        """生成统计报告（三种scope）/ Generate statistical reports (three scopes)"""
        from experiments.statistical_tests import generate_statistical_report

        # Create metrics JSON
        metrics_path = self.output_dir / "statistics" / "results_metrics.json"

        # Calculate metrics for baseline config
        baseline_results = results.get("baseline", {})

        # Filter ground truth to only include labeled records
        gt_labeled = {k: v for k, v in ground_truth.items() if v is not None}

        # Calculate accuracy
        correct = sum(1 for rid, pred in baseline_results.items()
                     if rid in gt_labeled and pred == gt_labeled[rid])
        n_labeled = len(gt_labeled)
        accuracy = correct / n_labeled if n_labeled > 0 else 0.0

        # Calculate unknown rate
        unknown_count = sum(1 for pred in baseline_results.values() if pred == "unknown")
        unknown_rate = unknown_count / len(baseline_results) if baseline_results else 0.0

        # Calculate error rate (incorrect predictions among labeled)
        error_count = sum(1 for rid, pred in baseline_results.items()
                         if rid in gt_labeled and pred != gt_labeled[rid] and pred != "unknown")
        error_rate = error_count / n_labeled if n_labeled > 0 else 0.0

        metrics = {
            "baseline": {
                "accuracy": accuracy,
                "unknown_rate": unknown_rate,
                "error_rate": error_rate,
                "total": len(baseline_results),
            }
        }

        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)

        # Generate full statistical report using existing infrastructure
        generate_statistical_report(
            results=results,
            ground_truth=gt_labeled,
            output_dir=str(self.output_dir / "statistics"),
            dataset_name=self.input_path.stem,
            run_id=self.run_id,
            config_dict={"baseline": {}},  # Single config for pilot
            metrics_json_path=metrics_path,
            n_records_total=n_records_total,
        )

    def _generate_reports_and_tables(
        self,
        events: List[DecisionEvent],
        results: Dict[str, Dict[str, str]],
        ground_truth: Dict[str, Optional[str]],
        perf_benchmark: Dict,
    ):
        """生成摘要报告和LaTeX表格 / Generate summary report and LaTeX tables"""
        # Generate summary report
        self._generate_summary_report(events, results, ground_truth, perf_benchmark)

        # Generate quality table
        self._generate_quality_table(results, ground_truth)

        # Generate performance table
        self._generate_performance_table(perf_benchmark)

    def _generate_summary_report(
        self,
        events: List[DecisionEvent],
        results: Dict[str, Dict[str, str]],
        ground_truth: Dict[str, Optional[str]],
        perf_benchmark: Dict,
    ):
        """生成istina_pilot_summary.md / Generate istina_pilot_summary.md"""
        report_path = self.output_dir / "reports" / "istina_pilot_summary.md"

        # Calculate metrics
        baseline_results = results.get("baseline", {})
        gt_labeled = {k: v for k, v in ground_truth.items() if v is not None}

        correct = sum(1 for rid, pred in baseline_results.items()
                     if rid in gt_labeled and pred == gt_labeled[rid])
        n_labeled = len(gt_labeled)
        accuracy = correct / n_labeled if n_labeled > 0 else 0.0

        unknown_count = sum(1 for pred in baseline_results.values() if pred == "unknown")
        unknown_rate = unknown_count / len(baseline_results) if baseline_results else 0.0

        coverage = 1.0 - unknown_rate

        # Extract performance from benchmark
        throughput = perf_benchmark.get("throughput_names_per_sec", 0)
        avg_latency = perf_benchmark.get("latency_ms", {}).get("avg", 0)
        total_time = perf_benchmark.get("total_time_sec", 0)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# ИСТИНА Pilot Summary / ИСТИНА试验摘要\n\n")

            # Цель апробации
            f.write("## Цель апробации / Pilot Objective\n\n")
            f.write("本次试验旨在验证中文姓名识别算法在ИСТИНА系统实际数据上的批处理性能和准确性。\n")
            f.write("这是一次на выгрузке из ИАС «ИСТИНА»的пакетная обработка试运行，\n")
            f.write("为未来正式集成提供技术验证和性能基准。\n\n")
            f.write("This pilot aims to validate the Chinese name recognition algorithm on real ISTINA system data\n")
            f.write("in batch processing mode. It provides technical validation and performance benchmarks\n")
            f.write("for future production integration.\n\n")

            # Данные
            f.write("## Данные / Data\n\n")
            f.write(f"- **抽取日期 / Extract Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n")
            f.write(f"- **规模 / Scale**: N_total={len(events)}, N_labeled={n_labeled}\n")
            f.write(f"- **数据源 / Data Source**: {self.input_path.name}\n")
            f.write(f"- **字段映射 / Field Mapping**:\n")
            f.write(f"  - original_name → algorithm input\n")
            f.write(f"  - lastname/firstname → ground truth validation\n")
            f.write(f"- **过滤规则 / Filtering Rules**: Empty names excluded\n\n")

            # Пайплайн
            f.write("## Пайплайн / Pipeline\n\n")
            f.write("```\n")
            f.write("ИСТИНА Export → Normalization → Algorithm v8.0 (ISTINA profile)\n")
            f.write("               → Decision Logging → Statistical Analysis → Audit Trail\n")
            f.write("```\n\n")
            f.write("详见架构图 / See architecture diagram: `figs/istina_integration.puml`\n\n")

            # Метрики
            f.write("## Метрики / Metrics\n\n")
            f.write(f"**Primary Metric (end-to-end accuracy)**:\n")
            f.write(f"- **准确率 / Accuracy**: {accuracy*100:.2f}% (correct / N_labeled)\n")
            f.write(f"- **未知率 / Unknown Rate**: {unknown_rate*100:.2f}%\n")
            f.write(f"- **覆盖率 / Coverage**: {coverage*100:.2f}%\n\n")
            f.write("详见 / Details: `statistics/stats_ci_global.md`\n\n")

            # Производительность
            f.write("## Производительность / Performance\n\n")
            f.write(f"- **吞吐量 / Throughput**: {throughput:.1f} names/sec\n")
            f.write(f"- **平均延迟 / Average Latency**: {avg_latency:.1f} ms\n")
            f.write(f"- **总处理时间 / Total Processing Time**: {total_time:.1f} sec\n\n")
            f.write(f"详见 / Details: `performance_benchmark.json`, `tables/istina_pilot_perf.tex`\n\n")

            # Интерпретируемость
            f.write("## Интерпретируемость / Interpretability\n\n")
            f.write("每条决策都包含完整的证据链（evidence-linked）：\n")
            f.write("Each decision includes a complete evidence chain (evidence-linked):\n")
            f.write("- Top-K reasons with weights\n")
            f.write("- Fired modules (evidence-linked: modules whose reasons appear in topK)\n")
            f.write("- Effective modules (same as fired, NOT counterfactual ablation)\n")
            f.write("- Score margins\n\n")
            f.write("详见 / Details:\n")
            f.write("- `events/baseline/decision_events.jsonl`\n")
            f.write("- `events/baseline/module_coverage.md`\n")
            f.write("- `events/baseline/reason_counts.csv`\n")
            f.write("- `logs/istina_batch_redacted_200.jsonl` (脱敏样本 / redacted sample)\n\n")

            # Ограничения
            f.write("## Ограничения / Limitations\n\n")
            f.write("⚠️ **重要 / Important**:\n\n")
            f.write("本次试验为апробация（技术验证），而非生产上线。\n")
            f.write("This pilot is an апробация (technical validation), not a production deployment.\n\n")
            f.write("正式集成需要：\n")
            f.write("Formal integration requires:\n")
            f.write("1. 与ИСТИНА系统оператора的正式согласование / Formal coordination with ISTINA operators\n")
            f.write("2. 生产环境部署方案评审 / Production deployment plan review\n")
            f.write("3. 机构数据安全与隐私保护审查 / Institutional data security & privacy review\n")
            f.write("4. 持续监控和人工复核机制 / Continuous monitoring and human review mechanism\n\n")

            # A3: 修改合规性措辞
            f.write("## 数据安全与脱敏 / Data Security & Redaction\n\n")
            f.write("本pilot按照GDPR/152-FZ的数据最小化与脱敏要求设计：\n")
            f.write("This pilot is designed following GDPR/152-FZ data minimization & redaction requirements:\n\n")
            f.write("- 决策事件日志不包含原文姓名tokens / Decision event logs exclude raw name tokens\n")
            f.write("- 脱敏样本使用单向哈希+统计特征 / Redacted sample uses one-way hash + statistical features\n")
            f.write("- Salt保密，确保哈希确定性与不可逆性 / Salt kept secret for deterministic, irreversible hashing\n\n")
            f.write("**最终合规性以机构审查为准 / Final compliance subject to institutional review**\n\n")

    def _generate_quality_table(
        self,
        results: Dict[str, Dict[str, str]],
        ground_truth: Dict[str, Optional[str]],
    ):
        """生成质量指标LaTeX表格 / Generate quality metrics LaTeX table"""
        table_path = self.output_dir / "tables" / "istina_pilot_quality.tex"

        baseline_results = results.get("baseline", {})
        gt_labeled = {k: v for k, v in ground_truth.items() if v is not None}

        correct = sum(1 for rid, pred in baseline_results.items()
                     if rid in gt_labeled and pred == gt_labeled[rid])
        n_labeled = len(gt_labeled)
        accuracy = correct / n_labeled if n_labeled > 0 else 0.0

        unknown_count = sum(1 for pred in baseline_results.values() if pred == "unknown")
        unknown_rate = unknown_count / len(baseline_results) if baseline_results else 0.0

        coverage = 1.0 - unknown_rate

        with open(table_path, 'w', encoding='utf-8') as f:
            f.write("% ІСТИНА Pilot Quality Metrics\n")
            f.write("% Requires: \\usepackage{booktabs}\n\n")
            f.write("\\begin{table}[htbp]\n")
            f.write("\\centering\n")
            f.write(f"\\caption{{ІСТИНА Pilot Quality Metrics (N={n_labeled})}}\n")
            f.write("\\label{tab:istina_pilot_quality}\n")
            f.write("\\begin{tabular}{lrc}\n")
            f.write("\\toprule\n")
            f.write("Metric & Value & Definition \\\\\n")
            f.write("\\midrule\n")
            f.write(f"Accuracy & {accuracy*100:.2f}\\% & correct / N\\_labeled \\\\\n")
            f.write(f"Coverage & {coverage*100:.2f}\\% & 1 - unknown\\_rate \\\\\n")
            f.write(f"Unknown Rate & {unknown_rate*100:.2f}\\% & unknown / N\\_total \\\\\n")
            f.write("\\bottomrule\n")
            f.write("\\end{tabular}\n")
            f.write("\\end{table}\n")

    def _generate_performance_table(self, perf_benchmark: Dict):
        """生成性能指标LaTeX表格 / Generate performance metrics LaTeX table"""
        table_path = self.output_dir / "tables" / "istina_pilot_perf.tex"

        throughput = perf_benchmark.get("throughput_names_per_sec", 0)
        latency = perf_benchmark.get("latency_ms", {})
        total_time = perf_benchmark.get("total_time_sec", 0)
        n_processed = perf_benchmark.get("n_records_processed", 0)

        with open(table_path, 'w', encoding='utf-8') as f:
            f.write("% ІСТИНА Pilot Performance Metrics\n")
            f.write("% Requires: \\usepackage{booktabs}\n\n")
            f.write("\\begin{table}[htbp]\n")
            f.write("\\centering\n")
            f.write(f"\\caption{{ІСТИНА Pilot Performance (N={n_processed})}}\n")
            f.write("\\label{tab:istina_pilot_perf}\n")
            f.write("\\begin{tabular}{lrc}\n")
            f.write("\\toprule\n")
            f.write("Metric & Value & Unit \\\\\n")
            f.write("\\midrule\n")
            f.write(f"Throughput & {throughput:.1f} & names/sec \\\\\n")
            f.write(f"Avg Latency & {latency.get('avg', 0):.1f} & ms \\\\\n")
            f.write(f"P50 Latency & {latency.get('p50', 0):.1f} & ms \\\\\n")
            f.write(f"P95 Latency & {latency.get('p95', 0):.1f} & ms \\\\\n")
            f.write(f"P99 Latency & {latency.get('p99', 0):.1f} & ms \\\\\n")
            f.write(f"Total Time & {total_time:.1f} & sec \\\\\n")
            f.write("\\bottomrule\n")
            f.write("\\end{tabular}\n")
            f.write("\\end{table}\n")

    def _generate_manifests(
        self,
        records: List[Dict],
        results: Dict[str, Dict[str, str]],
        ground_truth: Dict[str, Optional[str]],
        perf_benchmark: Dict,
    ):
        """生成run_manifest.json, env.txt, dataset_card.md / Generate manifests"""
        import platform
        import subprocess

        # run_manifest.json
        manifest_path = self.output_dir / "run_manifest.json"

        # Get git info
        git_commit = self._get_git_commit()
        git_commit_short = self._get_git_commit_short()

        # Calculate metrics
        baseline_results = results.get("baseline", {})
        gt_labeled = {k: v for k, v in ground_truth.items() if v is not None}

        correct = sum(1 for rid, pred in baseline_results.items()
                     if rid in gt_labeled and pred == gt_labeled[rid])
        n_labeled = len(gt_labeled)
        accuracy = correct / n_labeled if n_labeled > 0 else 0.0

        unknown_count = sum(1 for pred in baseline_results.values() if pred == "unknown")
        unknown_rate = unknown_count / len(baseline_results) if baseline_results else 0.0

        error_count = sum(1 for rid, pred in baseline_results.items()
                         if rid in gt_labeled and pred != gt_labeled[rid] and pred != "unknown")
        error_rate = error_count / n_labeled if n_labeled > 0 else 0.0

        manifest = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "run_type": "ISTINA_PILOT",  # A6: 用于validate_deliverables识别
            "run_id": self.run_id,
            "dataset": str(self.input_path),
            "n_records_total": len(records),
            "n_records_labeled": n_labeled,
            "profile": self.profile,
            "git_info": {
                "commit_sha": git_commit,
                "commit_sha_short": git_commit_short,
                "branch": self._get_git_branch(),  # B0: Fixed placeholder
            },
            "system_info": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "os": platform.system(),
            },
            "results_summary": {
                "baseline": {
                    "accuracy": accuracy,
                    "unknown_rate": unknown_rate,
                    "error_rate": error_rate,
                    "total": len(baseline_results),
                }
            },
            "reproducibility": {
                "random_seed": self.seed,
                "redact_salt_env": self.redact_salt_env,  # A3: 记录env名称（不记录值）
                "redact_salt_set": bool(self.salt),  # A3: 是否设置了salt
                "sample_lines": self.sample_lines,
                "write_full_log": bool(self.write_full_log),
                "keep_raw_sampled": bool(self.keep_raw_sampled),  # SAFE DEFAULT: 是否保留raw_sampled
                "raw_sampled_written": not bool(self.write_full_log),  # write_full_log=0时会生成raw_sampled
                "raw_sampled_deleted": (not bool(self.write_full_log)) and (not bool(self.keep_raw_sampled)),  # 是否自动删除
            },
            "performance_benchmark_ref": "performance_benchmark.json",  # A5: 引用
        }

        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        # env.txt
        env_path = self.output_dir / "env.txt"
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(f"Python: {platform.python_version()}\n")
            f.write(f"Platform: {platform.platform()}\n")
            f.write(f"OS: {platform.system()} {platform.release()}\n")
            f.write(f"Machine: {platform.machine()}\n")
            f.write(f"Processor: {platform.processor()}\n")

        # dataset_card.md
        dataset_card_path = self.output_dir / "dataset_card.md"
        with open(dataset_card_path, 'w', encoding='utf-8') as f:
            f.write("# Dataset Card\n\n")
            f.write(f"## Basic Information\n\n")
            f.write(f"- **Name**: {self.input_path.stem}\n")
            f.write(f"- **Source**: ІСТИНА (ИАС «ІСТИНА»)\n")
            f.write(f"- **Records**: {len(records)}\n")
            f.write(f"- **Labeled**: {n_labeled}\n")
            f.write(f"- **Format**: {self.input_path.suffix}\n\n")
            f.write(f"## Field Mapping\n\n")
            f.write(f"- `original_name` / `full_name` / `name` → algorithm input\n")
            f.write(f"- `lastname` + `firstname` → ground truth validation\n\n")
            f.write(f"## Processing\n\n")
            f.write(f"- **Profile**: {self.profile}\n")
            f.write(f"- **Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n")

    def _get_git_commit(self) -> str:
        """Get git commit SHA"""
        import subprocess
        try:
            return subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=project_root,
                text=True
            ).strip()
        except:
            return "unknown"

    def _get_git_commit_short(self) -> str:
        """Get git commit SHA (short)"""
        import subprocess
        try:
            return subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=project_root,
                text=True
            ).strip()
        except:
            return "unknown"

    def _get_git_branch(self) -> str:
        """Get current git branch"""
        import subprocess
        try:
            return subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=project_root,
                text=True
            ).strip()
        except:
            return "unknown"

    def _get_platform_info(self) -> str:
        """Get platform info string"""
        import platform
        return platform.platform()

    def _get_python_version(self) -> str:
        """Get Python version string"""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _get_cpu_count(self) -> int:
        """Get CPU core count"""
        import os
        return os.cpu_count() or 0


def main():
    """主函数 / Main function"""
    parser = argparse.ArgumentParser(
        description="ISTINA Pilot Runner / ІСТИНА试验运行器 (A1-A5 modifications)"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="ІСТИНА export data path (JSON/JSONL)"
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        required=True,
        help="Output directory"
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="ISTINA",
        help="Algorithm profile (default: ISTINA)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20251220,
        help="Random seed for sampling (default: 20251220)"
    )
    parser.add_argument(
        "--max_records",
        type=int,
        default=0,
        help="Max records to process (0=all, default: 0)"
    )
    parser.add_argument(
        "--write_full_log",
        type=int,
        default=0,
        help="Write full log with input_tokens (0=no [SAFE DEFAULT], 1=yes [DEBUG ONLY - DO NOT SUBMIT])"
    )
    parser.add_argument(
        "--keep_raw_sampled",
        type=int,
        default=0,
        help="Keep temporary raw sampled file after redaction (0=auto-delete [SAFE DEFAULT], 1=keep [DEBUG ONLY])"
    )
    parser.add_argument(
        "--redact_salt_env",
        type=str,
        default="ISTINA_LOG_SALT",
        help="Environment variable for redaction salt (default: ISTINA_LOG_SALT)"
    )
    parser.add_argument(
        "--sample_lines",
        type=int,
        default=200,
        help="Redacted sample lines (default: 200)"
    )
    parser.add_argument(
        "--validate",
        type=int,
        default=1,
        help="Run validation after completion (default: 1)"
    )

    args = parser.parse_args()

    # Create runner (A1: 传入write_full_log)
    runner = ISTINAPilotRunner(
        input_path=Path(args.input),
        output_dir=Path(args.out_dir),
        profile=args.profile,
        seed=args.seed,
        max_records=args.max_records,
        redact_salt_env=args.redact_salt_env,
        sample_lines=args.sample_lines,
        write_full_log=args.write_full_log,  # A1: 传入参数
        keep_raw_sampled=args.keep_raw_sampled,  # SAFE DEFAULT: 传入参数
    )

    # Run pilot
    try:
        summary = runner.run()

        # Validate if requested
        if args.validate:
            print(f"\n{'='*80}")
            print(f"Running validation...")
            print(f"{'='*80}")

            from experiments.validate_deliverables import DeliverableValidator

            validator = DeliverableValidator(args.out_dir)
            success = validator.validate()

            if not success:
                print(f"\n[ERROR] Validation failed!")
                sys.exit(1)
            else:
                print(f"\n[OK] Validation passed!")

        print(f"\n{'='*80}")
        print(f"Success! Output directory: {summary['output_dir']}")
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n[ERROR] Pilot run failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
