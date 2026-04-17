# -*- coding: utf-8 -*-
"""
事件追踪模块 / Event Tracking Module
用于记录算法决策过程中的模块触发情况
用于论文审稿证据链 / For paper review evidence chain

作者: Ma Jiaxin
日期: 2025-12-19
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json


@dataclass
class DecisionEvent:
    """
    单次决策的事件记录 / Single decision event record

    记录算法在处理单个姓名时的所有模块触发情况
    Records all module triggers when processing a single name
    """
    record_id: str

    # === 模块触发标记 (三层定义) / Module trigger flags (three-layer definition) ===
    # Layer 1: Evaluated (模块被执行) - 所有记录都会评估所有模块
    # Layer 2: Fired (模块产生非默认结果)
    source_prior_applied: bool = False          # Source prior产生非零贡献 (fired)
    western_exclusion_fired: bool = False       # 西方姓氏排除触发 (fired)

    # Layer 3: Effective (模块改变最终结果) - 包含order flip或unknown→known
    source_prior_effective: bool = False        # Source prior改变了最终order
    western_exclusion_effective: bool = False   # Western exclusion改变了最终order
    batch_consistency_override: bool = False    # Batch一致性改变了结果 (effective)
    person_consistency_override: bool = False   # Person一致性改变了结果 (effective)
    pub_consistency_override: bool = False      # Publication一致性改变了结果 (effective)
    default_inference_used: bool = False        # 使用默认推断 (fired)

    # === 决策详情 / Decision details ===
    mode: str = "UNKNOWN"                       # CHINESE/WESTERN/MIXED
    initial_order: str = "unknown"              # 初始决策（一致性调整前）
    final_order: str = "unknown"                # 最终决策（一致性调整后）
    confidence: float = 0.0                     # 置信度

    # === 分数信息 / Score information ===
    family_first_score: float = 0.0             # family_first分数
    given_first_score: float = 0.0              # given_first分数
    score_margin: float = 0.0                   # 分数差值 (fam - giv)

    # === 推理代码 / Reason codes ===
    reason_codes: List[str] = field(default_factory=list)

    # === 原始数据 / Raw data ===
    name_raw: str = ""
    affiliation: Optional[str] = None
    source: str = "DEFAULT"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 / Convert to dictionary"""
        return asdict(self)


class EventAggregator:
    """
    事件聚合器 / Event Aggregator

    收集和统计所有决策事件
    Collects and aggregates all decision events
    """

    def __init__(self):
        self.events: List[DecisionEvent] = []

    def add_event(self, event: DecisionEvent):
        """添加事件 / Add event"""
        self.events.append(event)

    def get_module_coverage(self) -> Dict[str, Any]:
        """
        计算模块覆盖率统计 (三层定义) / Calculate module coverage statistics (three-layer)

        三层定义 / Three-layer definition:
        - evaluated: 模块被执行/评估 (默认所有记录)
        - fired: 模块产生非默认结果
        - effective: 模块改变了最终决策 (order flip或unknown→known)

        Returns:
            包含各模块三层统计的字典
            Dictionary with three-layer stats for each module
        """
        total = len(self.events)
        if total == 0:
            return {}

        stats = {
            "total_records": total,
            "modules": {}
        }

        # 定义模块及其三层统计
        # Module definitions with three layers
        module_definitions = {
            "source_prior": {
                "evaluated": total,  # 所有记录都评估source prior
                "fired": sum(1 for e in self.events if e.source_prior_applied),
                "effective": sum(1 for e in self.events if getattr(e, 'source_prior_effective', False))
            },
            "western_exclusion": {
                "evaluated": total,  # 所有记录都评估western exclusion
                "fired": sum(1 for e in self.events if e.western_exclusion_fired),
                "effective": sum(1 for e in self.events if getattr(e, 'western_exclusion_effective', False))
            },
            "batch_consistency": {
                "evaluated": total,  # 所有记录都评估batch consistency
                "fired": total,  # Batch consistency总是被调用（即使没改变结果）
                "effective": sum(1 for e in self.events if e.batch_consistency_override)
            },
            "person_consistency": {
                "evaluated": total,
                "fired": total,  # Person consistency总是被调用
                "effective": sum(1 for e in self.events if e.person_consistency_override)
            },
            "pub_consistency": {
                "evaluated": total,
                "fired": total,  # Pub consistency总是被调用
                "effective": sum(1 for e in self.events if e.pub_consistency_override)
            },
            "default_inference": {
                "evaluated": total,
                "fired": sum(1 for e in self.events if e.default_inference_used),
                "effective": sum(1 for e in self.events if e.default_inference_used)  # Fired即effective
            }
        }

        for module_name, layers in module_definitions.items():
            evaluated = layers["evaluated"]
            fired = layers["fired"]
            effective = layers["effective"]

            stats["modules"][module_name] = {
                "evaluated": evaluated,
                "evaluated_rate": evaluated / total if total > 0 else 0.0,
                "fired": fired,
                "fired_rate": fired / total if total > 0 else 0.0,
                "effective": effective,
                "effective_rate": effective / total if total > 0 else 0.0,
                "fired_percentage": f"{100 * fired / total:.2f}%" if total > 0 else "0.00%",
                "effective_percentage": f"{100 * effective / total:.2f}%" if total > 0 else "0.00%"
            }

        return stats

    def get_score_margin_stats(self) -> Dict[str, float]:
        """
        计算分数差值的统计信息 / Calculate score margin statistics

        Returns:
            分数差值的统计指标（均值、中位数、分位数等）
            Statistical metrics of score margins
        """
        margins = [e.score_margin for e in self.events if e.score_margin != 0.0]

        if not margins:
            return {}

        margins_sorted = sorted(margins)
        n = len(margins_sorted)

        def percentile(p):
            k = (n - 1) * p
            f = int(k)
            c = f + 1 if f + 1 < n else f
            if f == c:
                return margins_sorted[f]
            return margins_sorted[f] * (c - k) + margins_sorted[c] * (k - f)

        return {
            "count": len(margins),
            "mean": sum(margins) / len(margins),
            "min": min(margins),
            "max": max(margins),
            "p01": percentile(0.01),
            "p05": percentile(0.05),
            "p25": percentile(0.25),
            "p50": percentile(0.50),  # median
            "p75": percentile(0.75),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
        }

    def get_reason_counts(self) -> List[Dict[str, Any]]:
        """
        统计reason code频次 / Count reason codes

        Returns:
            Reason code列表，按频次降序排列
            List of reason codes sorted by frequency
        """
        reason_counter = defaultdict(int)
        total = len(self.events)

        for event in self.events:
            for code in event.reason_codes:
                reason_counter[code] += 1

        results = []
        for code, count in sorted(reason_counter.items(), key=lambda x: -x[1]):
            results.append({
                "reason_code": code,
                "count": count,
                "rate": count / total if total > 0 else 0.0,
                "percentage": f"{100 * count / total:.2f}%" if total > 0 else "0.00%"
            })

        return results

    def get_triggered_record_ids(self, module_name: str) -> List[str]:
        """
        获取某个模块触发的record_id列表 / Get record IDs where module triggered

        Args:
            module_name: 模块名称（如 "source_prior_applied"）

        Returns:
            触发该模块的record_id列表
        """
        triggered_ids = []
        for event in self.events:
            if getattr(event, module_name, False):
                triggered_ids.append(event.record_id)
        return triggered_ids

    def get_consistency_changed_ids(self) -> Dict[str, List[str]]:
        """
        获取被一致性模块改变了结果的record_id
        Get record IDs where consistency modules changed the result

        Returns:
            字典，键为模块名，值为record_id列表
        """
        changed_ids = {
            "batch_consistency": [],
            "person_consistency": [],
            "pub_consistency": []
        }

        for event in self.events:
            if event.batch_consistency_override:
                changed_ids["batch_consistency"].append(event.record_id)
            if event.person_consistency_override:
                changed_ids["person_consistency"].append(event.record_id)
            if event.pub_consistency_override:
                changed_ids["pub_consistency"].append(event.record_id)

        return changed_ids

    def get_override_overlap(self) -> Dict[str, Any]:
        """
        分析batch_consistency和pub_consistency的重叠情况
        Analyze overlap between batch_consistency and pub_consistency

        Returns:
            包含交集、并集、Jaccard系数的统计字典
        """
        batch_ids = set()
        person_ids = set()
        pub_ids = set()

        for event in self.events:
            if event.batch_consistency_override:
                batch_ids.add(event.record_id)
            if event.person_consistency_override:
                person_ids.add(event.record_id)
            if event.pub_consistency_override:
                pub_ids.add(event.record_id)

        # Batch = Person + Pub的组合
        # 分析三者之间的关系
        only_person = person_ids - pub_ids
        only_pub = pub_ids - person_ids
        both_person_pub = person_ids & pub_ids

        # Batch应该等于Person + Pub（任一触发）
        union_person_pub = person_ids | pub_ids

        # Jaccard系数
        jaccard = 0.0
        if len(union_person_pub) > 0:
            jaccard = len(both_person_pub) / len(union_person_pub)

        return {
            "batch_consistency_count": len(batch_ids),
            "person_consistency_count": len(person_ids),
            "pub_consistency_count": len(pub_ids),
            "only_person": len(only_person),
            "only_pub": len(only_pub),
            "both_person_and_pub": len(both_person_pub),
            "union_person_pub": len(union_person_pub),
            "jaccard_coefficient": jaccard,
            "explanation": {
                "batch_equals_union": len(batch_ids) == len(union_person_pub),
                "batch_count_vs_union": f"{len(batch_ids)} vs {len(union_person_pub)}"
            }
        }

    def export_events(self, filepath: str):
        """
        导出所有事件到JSONL文件 / Export all events to JSONL file

        Args:
            filepath: 输出文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            for event in self.events:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')

    def save_statistics(self, output_dir: str):
        """
        保存所有统计结果到文件 / Save all statistics to files

        Args:
            output_dir: 输出目录
        """
        from pathlib import Path
        import csv

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. 模块覆盖率 JSON
        module_coverage = self.get_module_coverage()
        with open(out_path / "module_coverage.json", 'w', encoding='utf-8') as f:
            json.dump(module_coverage, f, indent=2, ensure_ascii=False)

        # 2. 分数差值统计 JSON
        margin_stats = self.get_score_margin_stats()
        with open(out_path / "score_margin_stats.json", 'w', encoding='utf-8') as f:
            json.dump(margin_stats, f, indent=2, ensure_ascii=False)

        # 3. Reason counts CSV
        reason_counts = self.get_reason_counts()
        with open(out_path / "reason_counts.csv", 'w', encoding='utf-8', newline='') as f:
            if reason_counts:
                writer = csv.DictWriter(f, fieldnames=["reason_code", "count", "rate", "percentage"])
                writer.writeheader()
                writer.writerows(reason_counts)

        # 4. 模块覆盖率 Markdown
        self._save_module_coverage_md(module_coverage, out_path / "module_coverage.md")

        # 5. Override overlap 统计
        override_overlap = self.get_override_overlap()
        with open(out_path / "override_overlap.json", 'w', encoding='utf-8') as f:
            json.dump(override_overlap, f, indent=2, ensure_ascii=False)

        # 6. Override overlap Markdown
        self._save_override_overlap_md(override_overlap, out_path / "override_overlap.md")

    def _save_module_coverage_md(self, coverage: Dict[str, Any], filepath: str):
        """保存模块覆盖率Markdown报告 (三层定义)"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# 模块触发率统计报告 (三层定义) / Module Trigger Rate Report (Three-Layer)\n\n")
            f.write(f"**总记录数 / Total Records**: {coverage.get('total_records', 0):,}\n\n")

            f.write("## 三层定义 / Three-Layer Definition\n\n")
            f.write("- **Evaluated** (评估): 模块被执行/调用 (通常是所有记录)\n")
            f.write("- **Fired** (触发): 模块产生非默认结果 (例如source prior非零、western exclusion规则触发)\n")
            f.write("- **Effective** (生效): 模块改变了最终决策 (order flip或unknown→known)\n\n")

            f.write("## 各模块触发情况 / Module Trigger Summary\n\n")
            f.write("| 模块 / Module | Evaluated | Fired | Fired % | Effective | Effective % |\n")
            f.write("|---------------|-----------|-------|---------|-----------|-------------|\n")

            modules = coverage.get('modules', {})
            module_labels = {
                "source_prior": "Source Prior",
                "western_exclusion": "Western Exclusion",
                "batch_consistency": "Batch Consistency",
                "person_consistency": "Person Consistency",
                "pub_consistency": "Publication Consistency",
                "default_inference": "Default Inference"
            }

            for module_key, label in module_labels.items():
                stats = modules.get(module_key, {})
                evaluated = stats.get('evaluated', 0)
                fired = stats.get('fired', 0)
                fired_pct = stats.get('fired_percentage', '0.00%')
                effective = stats.get('effective', 0)
                effective_pct = stats.get('effective_percentage', '0.00%')
                f.write(f"| {label} | {evaluated:,} | {fired:,} | {fired_pct} | {effective:,} | {effective_pct} |\n")

            f.write("\n## 解释 / Interpretation\n\n")
            f.write("### Source Prior\n")
            f.write("- **Fired**: Source prior对分数产生了非零贡献\n")
            f.write("- **Effective**: Source prior改变了最终order (需在event_collection中追踪)\n\n")

            f.write("### Western Exclusion\n")
            f.write("- **Fired**: 西方姓氏排除规则被触发 (识别到西方姓氏)\n")
            f.write("- **Effective**: Western exclusion改变了最终order\n\n")

            f.write("### Batch/Person/Publication Consistency\n")
            f.write("- **Fired**: 一致性模块被调用 (通常是所有记录)\n")
            f.write("- **Effective**: 一致性调整改变了order或填补了unknown\n\n")

            f.write("### Default Inference\n")
            f.write("- **Fired** & **Effective**: 使用了默认推断路径 (无明确证据)\n\n")

    def _save_override_overlap_md(self, overlap: Dict[str, Any], filepath: str):
        """保存Override overlap Markdown报告"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Consistency Override Overlap Analysis\n\n")
            f.write("## 概览 / Overview\n\n")
            f.write("分析Person Consistency和Publication Consistency两个模块的重叠情况。\n\n")
            f.write("Analysis of overlap between Person Consistency and Publication Consistency modules.\n\n")

            f.write("## 统计数据 / Statistics\n\n")
            f.write("| 指标 / Metric | 数量 / Count |\n")
            f.write("|---------------|-------------|\n")
            f.write(f"| Batch Consistency触发 | {overlap['batch_consistency_count']:,} |\n")
            f.write(f"| Person Consistency触发 | {overlap['person_consistency_count']:,} |\n")
            f.write(f"| Publication Consistency触发 | {overlap['pub_consistency_count']:,} |\n")
            f.write(f"| 仅Person触发 | {overlap['only_person']:,} |\n")
            f.write(f"| 仅Pub触发 | {overlap['only_pub']:,} |\n")
            f.write(f"| Person和Pub都触发 | {overlap['both_person_and_pub']:,} |\n")
            f.write(f"| Person ∪ Pub并集 | {overlap['union_person_pub']:,} |\n")
            f.write(f"| Jaccard系数 | {overlap['jaccard_coefficient']:.4f} |\n\n")

            f.write("## 解释 / Interpretation\n\n")
            f.write("**Batch Consistency = Person Consistency OR Publication Consistency**\n\n")
            f.write("在v8.0算法中，batch_consistency_override标记会在以下情况触发：\n")
            f.write("- Person一致性改变了结果，或\n")
            f.write("- Publication一致性改变了结果\n\n")

            f.write(f"**验证**: Batch count ({overlap['batch_consistency_count']}) ")
            if overlap['explanation']['batch_equals_union']:
                f.write("**等于** Person∪Pub ({overlap['union_person_pub']}) ✓\n\n")
            else:
                f.write(f"**不等于** Person∪Pub ({overlap['union_person_pub']}) - 需要检查！\n\n")

            f.write("**Jaccard系数**解释：\n")
            f.write(f"- J = |Person ∩ Pub| / |Person ∪ Pub| = {overlap['jaccard_coefficient']:.4f}\n")
            if overlap['jaccard_coefficient'] > 0.5:
                f.write("- 高重叠度（>0.5）：两个模块倾向于同时触发\n")
            elif overlap['jaccard_coefficient'] > 0.2:
                f.write("- 中等重叠度（0.2-0.5）：有一定重叠但也有独立触发\n")
            else:
                f.write("- 低重叠度（<0.2）：两个模块基本独立触发\n")
