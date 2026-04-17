# -*- coding: utf-8 -*-
"""
事件收集包装器 / Event Collection Wrapper

包装v8.0算法，收集决策过程中的事件信息
用于论文审稿证据链分析
Wraps v8.0 algorithm to collect decision events for paper review evidence chain

作者: Ma Jiaxin
日期: 2025-12-19
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.surname_identifier_v8 import (
    NameRecord,
    NameDecision,
    preprocess_name,
    detect_mode,
    extract_features,
    decide_chinese,
    decide_western,
    identify_surname_position_v8,
    local_decision,
)

# 确保NameDecision可用
try:
    from src.surname_identifier_v8 import NameDecision
except ImportError:
    pass  # 已经导入
from src.config_v8 import (
    get_config,
    get_ablation_config,
    AblationConfig
)
from src.event_tracker import DecisionEvent, EventAggregator
from src.contribution_tracker import estimate_contributions_from_decision


def collect_event_from_decision(
    record: NameRecord,
    decision: NameDecision,
    fam_score: float = 0.0,
    giv_score: float = 0.0,
    initial_order: Optional[str] = None,
    consistency_changed: bool = False
) -> DecisionEvent:
    """
    从决策结果创建事件 / Create event from decision result

    Args:
        record: 姓名记录
        decision: 决策结果
        fam_score: family_first分数
        giv_score: given_first分数
        initial_order: 初始决策（一致性调整前）
        consistency_changed: 一致性是否改变了结果

    Returns:
        DecisionEvent对象
    """
    event = DecisionEvent(
        record_id=record.record_id,
        mode=decision.mode,
        final_order=decision.order,
        initial_order=initial_order or decision.order,
        confidence=decision.confidence,
        family_first_score=fam_score,
        given_first_score=giv_score,
        score_margin=fam_score - giv_score,
        reason_codes=decision.reason_codes[:],
        name_raw=record.name_raw,
        affiliation=record.affiliation_raw,
        source=record.source
    )

    # 检测模块触发情况
    ablation = get_ablation_config()

    # 1. Source prior applied (Layer 2: Fired)
    if not ablation.disable_source_prior:
        # 如果source是CROSSREF/ORCID/ISTINA，则source prior生效
        if record.source.upper() in ("CROSSREF", "ORCID", "ISTINA", "ИСТИНА"):
            event.source_prior_applied = True

    # 2. Western exclusion fired (Layer 2: Fired)
    if not ablation.disable_western_exclusion:
        # 检查reason_codes中是否有西方姓氏相关的代码
        west_reasons = [r for r in decision.reason_codes
                        if "WEST" in r or "WESTERN" in r]
        if west_reasons:
            event.western_exclusion_fired = True

    # 3. Consistency overrides (already Layer 3: Effective)
    if consistency_changed:
        event.batch_consistency_override = True
        # 更细粒度的一致性类型需要在batch函数中设置

    # 4. Default inference
    if "DEFAULT" in " ".join(decision.reason_codes).upper():
        event.default_inference_used = True

    # 5. Estimate effective contributions (Layer 3: Effective)
    # Note: 这是启发式估算。完整追踪需要instrument v8核心决策函数
    # This is heuristic estimation. Full tracking requires instrumenting v8 core
    contributions = estimate_contributions_from_decision(
        decision, record, fam_score, giv_score
    )

    # 应用effective标记
    if "source_prior" in contributions:
        event.source_prior_effective = contributions["source_prior"].effective

    if "western_exclusion" in contributions:
        event.western_exclusion_effective = contributions["western_exclusion"].effective

    return event


def identify_with_event_tracking(
    record: NameRecord
) -> Tuple[str, float, str, DecisionEvent]:
    """
    单个姓名识别（带事件追踪）
    Single name identification with event tracking

    Args:
        record: 姓名记录

    Returns:
        (order, confidence, reason, event)
    """
    # 调用原函数
    order, confidence, reason = identify_surname_position_v8(record)

    # 创建决策对象（模拟）
    decision = NameDecision(
        order=order,
        confidence=confidence,
        mode="UNKNOWN",  # 单次调用无法获取mode
        reason_codes=reason.split(', ') if reason else []
    )

    # 创建事件（缺少分数信息）
    event = collect_event_from_decision(record, decision)

    return order, confidence, reason, event


def batch_identify_with_event_tracking(
    records: List[NameRecord],
    source: Optional[str] = None,
    enable_person_consistency: bool = True,
    enable_pub_consistency: bool = True,
) -> Tuple[Dict[str, NameDecision], EventAggregator]:
    """
    批量识别（带完整事件追踪）
    Batch identification with complete event tracking

    Args:
        records: 姓名记录列表
        source: 数据源
        enable_person_consistency: 是否启用person一致性
        enable_pub_consistency: 是否启用publication一致性

    Returns:
        (decisions, aggregator)
    """
    aggregator = EventAggregator()
    cfg = get_config(source)
    ablation = get_ablation_config()

    # ========== 第1步：局部决策 ==========
    initial_decisions = {}
    initial_events = {}

    for rec in records:
        rec_cfg = get_config(rec.source) if rec.source else cfg

        # 调用v8的local_decision函数（包含完整的缩写检测、模式识别、决策逻辑）
        decision = local_decision(rec, rec_cfg)
        initial_decisions[rec.record_id] = decision

        # 获取parsed和mode用于事件追踪
        parsed = preprocess_name(rec.name_raw)
        if parsed.first_idx < 0 or parsed.last_idx < 0 or len(parsed.tokens) == 0:
            mode = "INVALID"
        else:
            mode = detect_mode(rec, parsed, rec_cfg)

        # 计算分数（简化：从reason codes推断）
        fam_score, giv_score = estimate_scores_from_reasons(decision, mode)

        # 创建初始事件
        event = collect_event_from_decision(
            rec, decision, fam_score, giv_score
        )
        initial_events[rec.record_id] = event

    # ========== 第2步：一致性调整（如果启用）==========
    final_decisions = dict(initial_decisions)

    # Person consistency
    if enable_person_consistency and not ablation.disable_batch_consistency:
        changed_ids = apply_person_consistency(records, final_decisions, cfg)
        for rid in changed_ids:
            if rid in initial_events:
                # Consistency overrides are inherently effective (Layer 3)
                initial_events[rid].person_consistency_override = True
                initial_events[rid].batch_consistency_override = True
                initial_events[rid].initial_order = initial_decisions[rid].order

    # Publication consistency
    if enable_pub_consistency and not ablation.disable_batch_consistency:
        changed_ids = apply_pub_consistency(records, final_decisions, cfg)
        for rid in changed_ids:
            if rid in initial_events:
                # Consistency overrides are inherently effective (Layer 3)
                initial_events[rid].pub_consistency_override = True
                initial_events[rid].batch_consistency_override = True
                initial_events[rid].initial_order = initial_decisions[rid].order

    # ========== 第3步：更新最终决策到事件 ==========
    for rid, event in initial_events.items():
        if rid in final_decisions:
            event.final_order = final_decisions[rid].order
            event.confidence = final_decisions[rid].confidence

            # Re-estimate contributions with final decision
            # (for cases where consistency changed the order)
            rec = next((r for r in records if r.record_id == rid), None)
            if rec:
                fam_score = event.family_first_score
                giv_score = event.given_first_score
                contributions = estimate_contributions_from_decision(
                    final_decisions[rid], rec, fam_score, giv_score
                )

                # Update effective flags (unless already set by consistency)
                if not event.person_consistency_override and not event.pub_consistency_override:
                    if "source_prior" in contributions:
                        event.source_prior_effective = contributions["source_prior"].effective
                    if "western_exclusion" in contributions:
                        event.western_exclusion_effective = contributions["western_exclusion"].effective

        aggregator.add_event(event)

    return final_decisions, aggregator


def estimate_scores_from_reasons(decision: NameDecision, mode: str) -> Tuple[float, float]:
    """
    从reason codes估算分数（简化版）
    Estimate scores from reason codes (simplified)

    Note: 这是一个近似方法，无法获得精确分数
    """
    from src.config_v8 import CHINESE_FEATURE_WEIGHTS, WESTERN_FEATURE_WEIGHTS

    fam_score = 0.0
    giv_score = 0.0

    if mode == "CHINESE":
        fam_score = 0.5  # Prior
        giv_score = 0.5

        for code in decision.reason_codes:
            if "CN_SURNAME_FIRST_ONLY" in code:
                fam_score += CHINESE_FEATURE_WEIGHTS.get("CN_SURNAME_FIRST_ONLY", 0.6)
            elif "CN_SURNAME_LAST_ONLY" in code:
                giv_score += CHINESE_FEATURE_WEIGHTS.get("CN_SURNAME_LAST_ONLY", 0.6)
            elif "CN_SURNAME_DOUBLE_FREQ_FIRST" in code:
                fam_score += CHINESE_FEATURE_WEIGHTS.get("CN_SURNAME_DOUBLE_FREQ", 0.4)
            elif "CN_SURNAME_DOUBLE_FREQ_LAST" in code:
                giv_score += CHINESE_FEATURE_WEIGHTS.get("CN_SURNAME_DOUBLE_FREQ", 0.4)
            elif "CN_SURNAME_DOUBLE_DEFAULT_FAM" in code:
                fam_score += CHINESE_FEATURE_WEIGHTS.get("CN_SURNAME_DOUBLE_DEFAULT", 0.3)
            elif "FIRST_VALID_PY_NAME" in code:
                giv_score += CHINESE_FEATURE_WEIGHTS.get("FIRST_VALID_PY_NAME", 0.3)
            elif "LAST_VALID_PY_NAME" in code:
                fam_score += CHINESE_FEATURE_WEIGHTS.get("LAST_VALID_PY_NAME", 0.3)

    elif mode == "WESTERN":
        fam_score = 0.3  # Prior
        giv_score = 0.7

        for code in decision.reason_codes:
            if "WEST_SURNAME_LAST" in code:
                giv_score += WESTERN_FEATURE_WEIGHTS.get("WEST_SURNAME_LAST", 0.5)
            elif "WEST_SURNAME_FIRST" in code:
                fam_score += WESTERN_FEATURE_WEIGHTS.get("WEST_SURNAME_FIRST", 0.4)

    return fam_score, giv_score


def apply_person_consistency(
    records: List[NameRecord],
    decisions: Dict[str, NameDecision],
    cfg
) -> List[str]:
    """
    应用person一致性调整
    Apply person consistency adjustment

    Returns:
        被改变的record_id列表
    """
    changed_ids = []
    groups = defaultdict(list)

    for rec in records:
        if rec.person_id:
            groups[rec.person_id].append(rec.record_id)

    for pid, rec_ids in groups.items():
        local_decisions = [decisions[rid] for rid in rec_ids
                           if rid in decisions and decisions[rid].order != "unknown"]

        if not local_decisions:
            continue

        fam = [d for d in local_decisions
               if d.order == "family_first" and d.confidence >= cfg.person_conf_thresh]
        giv = [d for d in local_decisions
               if d.order == "given_first" and d.confidence >= cfg.person_conf_thresh]

        if len(fam) == 0 and len(giv) == 0:
            continue

        target_order = "family_first" if len(fam) >= len(giv) else "given_first"

        # 覆盖低置信度或unknown（与v8算法一致）
        for rid in rec_ids:
            if rid not in decisions:
                continue
            d = decisions[rid]
            if d.order == "unknown" or d.confidence < cfg.person_override_thresh:
                decisions[rid] = NameDecision(
                    order=target_order,
                    confidence=max(d.confidence, cfg.person_override_conf),
                    mode=d.mode,
                    reason_codes=d.reason_codes + ["PERSON_CONSISTENCY_OVERRIDE"]
                )
                changed_ids.append(rid)

    return changed_ids


def apply_pub_consistency(
    records: List[NameRecord],
    decisions: Dict[str, NameDecision],
    cfg
) -> List[str]:
    """
    应用publication一致性调整
    Apply publication consistency adjustment

    Returns:
        被改变的record_id列表
    """
    changed_ids = []
    groups = defaultdict(list)

    for rec in records:
        if rec.publication_id:
            groups[rec.publication_id].append(rec.record_id)

    for pub_id, rec_ids in groups.items():
        fam = [decisions[rid] for rid in rec_ids if rid in decisions
               and decisions[rid].order == "family_first"
               and decisions[rid].confidence >= cfg.pub_conf_thresh]
        giv = [decisions[rid] for rid in rec_ids if rid in decisions
               and decisions[rid].order == "given_first"
               and decisions[rid].confidence >= cfg.pub_conf_thresh]

        if len(fam) == 0 and len(giv) == 0:
            continue

        if abs(len(fam) - len(giv)) < cfg.pub_dominance_min_diff:
            continue

        target_order = "family_first" if len(fam) > len(giv) else "given_first"

        # 覆盖低置信度或unknown（与v8算法一致）
        for rid in rec_ids:
            if rid not in decisions:
                continue
            d = decisions[rid]
            if d.order == "unknown" or d.confidence < cfg.pub_override_thresh:
                decisions[rid] = NameDecision(
                    order=target_order,
                    confidence=max(d.confidence, cfg.pub_override_conf),
                    mode=d.mode,
                    reason_codes=d.reason_codes + ["PUB_CONSISTENCY_OVERRIDE"]
                )
                changed_ids.append(rid)

    return changed_ids
