# -*- coding: utf-8 -*-
"""
模块贡献追踪器 / Module Contribution Tracker

通过在决策过程中记录中间状态,计算每个模块的counterfactual effective
Without 2x rerun by tracking incremental contributions

作者: Ma Jiaxin
日期: 2025-12-19
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class ModuleContribution:
    """单个模块的贡献记录"""
    module_name: str
    applied: bool = False           # Layer 2: Fired
    effective: bool = False         # Layer 3: Effective (changed outcome)

    # Contribution details
    delta_fam_score: float = 0.0    # 对family_first分数的贡献
    delta_giv_score: float = 0.0    # 对given_first分数的贡献

    # Order change tracking
    order_before: str = "unknown"   # 应用该模块前的order
    order_after: str = "unknown"    # 应用该模块后的order
    change_type: str = ""           # e.g., "unknown→family_first", "given_first→family_first"


class ContributionTracker:
    """
    贡献追踪器 - 在决策过程中记录每个模块的增量贡献
    Contribution Tracker - Records incremental contributions during decision

    使用方法 / Usage:
    ```python
    tracker = ContributionTracker()

    # 在应用source prior前
    tracker.record_state("source_prior", "before", fam_score, giv_score, current_order)
    # ... apply source prior ...
    tracker.record_state("source_prior", "after", fam_score, giv_score, new_order)
    tracker.finalize_module("source_prior")

    # 获取结果
    contributions = tracker.get_contributions()
    ```
    """

    def __init__(self):
        self.modules: Dict[str, ModuleContribution] = {}
        self._states: Dict[str, Dict[str, Tuple[float, float, str]]] = {}

    def record_state(
        self,
        module_name: str,
        stage: str,  # "before" or "after"
        fam_score: float,
        giv_score: float,
        order: str
    ):
        """
        记录模块应用前后的状态
        Record state before/after applying a module
        """
        if module_name not in self._states:
            self._states[module_name] = {}

        self._states[module_name][stage] = (fam_score, giv_score, order)

    def finalize_module(self, module_name: str):
        """
        完成模块记录,计算贡献
        Finalize module recording and compute contribution
        """
        if module_name not in self._states:
            return

        states = self._states[module_name]
        before = states.get("before")
        after = states.get("after")

        if not before or not after:
            return

        fam_before, giv_before, order_before = before
        fam_after, giv_after, order_after = after

        contrib = ModuleContribution(module_name=module_name)

        # Check if fired (any score changed)
        if abs(fam_after - fam_before) > 1e-6 or abs(giv_after - giv_before) > 1e-6:
            contrib.applied = True
            contrib.delta_fam_score = fam_after - fam_before
            contrib.delta_giv_score = giv_after - giv_before

        # Check if effective (order changed)
        contrib.order_before = order_before
        contrib.order_after = order_after

        if order_before != order_after:
            contrib.effective = True
            contrib.change_type = f"{order_before}→{order_after}"

        self.modules[module_name] = contrib

    def mark_applied(self, module_name: str):
        """
        直接标记模块为applied (用于无法追踪分数的模块,如western_exclusion)
        """
        if module_name not in self.modules:
            self.modules[module_name] = ModuleContribution(module_name=module_name)
        self.modules[module_name].applied = True

    def mark_effective(self, module_name: str, change_type: str = ""):
        """
        直接标记模块为effective
        """
        if module_name not in self.modules:
            self.modules[module_name] = ModuleContribution(module_name=module_name)
        self.modules[module_name].effective = True
        if change_type:
            self.modules[module_name].change_type = change_type

    def get_contributions(self) -> Dict[str, ModuleContribution]:
        """返回所有模块的贡献记录"""
        return self.modules.copy()

    def to_dict(self) -> Dict[str, Dict]:
        """转换为字典格式 (用于序列化)"""
        return {
            name: {
                "applied": contrib.applied,
                "effective": contrib.effective,
                "delta_fam_score": contrib.delta_fam_score,
                "delta_giv_score": contrib.delta_giv_score,
                "order_before": contrib.order_before,
                "order_after": contrib.order_after,
                "change_type": contrib.change_type
            }
            for name, contrib in self.modules.items()
        }


def estimate_contributions_from_decision(
    decision,
    record,
    fam_score: float,
    giv_score: float
) -> Dict[str, ModuleContribution]:
    """
    从决策结果估算模块贡献 (启发式方法,用于无法直接追踪的情况)
    Estimate module contributions from decision result (heuristic fallback)

    这是一个fallback方法,不如直接追踪准确,但可在无法修改v8时使用
    """
    contributions = {}

    # 1. Source Prior
    source_prior = ModuleContribution(module_name="source_prior")
    if record.source.upper() in ("CROSSREF", "ORCID", "ISTINA", "ИСТИНА"):
        source_prior.applied = True
        # 估算: 如果reason_codes中包含source相关的,可能是effective
        source_reasons = [r for r in decision.reason_codes if "SOURCE" in r.upper()]
        if source_reasons:
            # 简化：如果有source reason且margin小，可能source prior起了关键作用
            margin = abs(fam_score - giv_score)
            if margin < 0.3:  # Threshold for "close call"
                source_prior.effective = True
                source_prior.change_type = "close_call_influenced"
    contributions["source_prior"] = source_prior

    # 2. Western Exclusion
    western_exclusion = ModuleContribution(module_name="western_exclusion")
    west_reasons = [r for r in decision.reason_codes if "WEST" in r.upper()]
    if west_reasons:
        western_exclusion.applied = True
        # 如果western reason是主要原因（排在前面），标记为effective
        if any("WEST" in decision.reason_codes[0].upper() for i in range(min(2, len(decision.reason_codes)))):
            western_exclusion.effective = True
            western_exclusion.change_type = "western_surname_detected"
    contributions["western_exclusion"] = western_exclusion

    # 3-5. Consistency modules (需要在event_collection中单独处理)
    for module in ["batch_consistency", "person_consistency", "pub_consistency"]:
        contributions[module] = ModuleContribution(module_name=module)

    return contributions
