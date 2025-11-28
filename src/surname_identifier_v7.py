# -*- coding: utf-8 -*-
"""
v7.0中文姓氏位置识别算法 / v7.0 Chinese Surname Position Identifier

核心改进:
1. 双模式架构 (Chinese/Western/Mixed)
2. 拼音合法性检测 (DP分词)
3. Western模式默认推断
4. 修正双姓氏频率逻辑

作者: Ma Jiaxin
日期: 2025-11-28
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入数据库和工具
from data.surname_pinyin_db import (
    is_surname_pinyin,
    get_surname_from_pinyin,
)
from data.surname_frequency import get_surname_frequency_rank
from data.western_name_features import (
    has_western_suffix,
    has_western_consonant_cluster,
    has_latin_extended_chars,
    is_likely_western_name,
    is_common_western_surname,
)
from src.pinyin_validator import (
    calculate_given_name_confidence_v7,
    is_valid_pinyin_name,
)
from src.affiliation_analyzer import analyze_affiliation, AffiliationInfo


@dataclass
class ModeScore:
    """模式评分 / Mode Score"""
    chinese_score: float = 0.0  # 中文证据分数
    western_score: float = 0.0  # 西方证据分数
    mode: str = "Mixed"  # Chinese / Western / Mixed
    evidence_cn: List[str] = None  # 中文证据列表
    evidence_west: List[str] = None  # 西方证据列表

    def __post_init__(self):
        if self.evidence_cn is None:
            self.evidence_cn = []
        if self.evidence_west is None:
            self.evidence_west = []


def calculate_mode_scores(
    original_name: str,
    first_token: str,
    last_token: str,
    affil_info: Optional[AffiliationInfo] = None
) -> ModeScore:
    """
    计算Chinese vs Western证据分数
    Calculate Chinese vs Western evidence scores

    Args:
        original_name: 原始姓名
        first_token: 第一个token
        last_token: 最后一个token
        affil_info: 机构信息

    Returns:
        ModeScore: 模式评分对象
    """
    score_cn = 0.0
    score_west = 0.0
    evidence_cn = []
    evidence_west = []

    # === 中文证据 Chinese Evidence ===

    # CN1: 首/末token命中中文姓氏表
    if is_surname_pinyin(first_token):
        score_cn += 0.6
        variants = get_surname_from_pinyin(first_token)
        evidence_cn.append(f"{first_token}是中文姓氏→{variants[:2]}")

    if is_surname_pinyin(last_token):
        score_cn += 0.6
        variants = get_surname_from_pinyin(last_token)
        evidence_cn.append(f"{last_token}是中文姓氏→{variants[:2]}")

    # CN2: token通过拼音合法性检测
    for token_name, token in [("first", first_token), ("last", last_token)]:
        is_valid, count, syllables = is_valid_pinyin_name(token)
        if is_valid and count in [2, 3]:  # 2-3音节是典型中文名
            score_cn += 0.2
            evidence_cn.append(f"{token}是合法拼音({count}音节)")

    # CN3: 中国机构
    if affil_info and affil_info.is_chinese:
        score_cn += 0.3
        evidence_cn.append("中国机构")

    # CN4: 原字符串中含有中文字符（直接判定）
    if re.search(r'[\u4e00-\u9fff]', original_name):
        score_cn += 0.8
        evidence_cn.append("含中文字符")

    # === 西方证据 Western Evidence ===

    # W1: token含非拼音辅音组合
    for token in [first_token, last_token]:
        if has_western_consonant_cluster(token):
            score_west += 0.3
            evidence_west.append(f"{token}含西方辅音组合")

    # W2: token含拉丁扩展字符
    for token in [first_token, last_token]:
        if has_latin_extended_chars(token):
            score_west += 0.3
            evidence_west.append(f"{token}含拉丁扩展字符")

    # W3: token含西方姓氏后缀
    for token in [first_token, last_token]:
        if has_western_suffix(token):
            score_west += 0.3
            evidence_west.append(f"{token}含西方姓氏后缀")

    # W4: token命中西方姓氏表
    for token in [first_token, last_token]:
        if is_common_western_surname(token):
            score_west += 0.4
            evidence_west.append(f"{token}是常见西方姓氏")

    # W5: 非中国机构
    if affil_info and not affil_info.is_chinese and affil_info.country:
        score_west += 0.2
        evidence_west.append(f"非中国机构({affil_info.country})")

    # 封顶
    score_cn = min(score_cn, 1.0)
    score_west = min(score_west, 1.0)

    # 模式选择
    if score_cn >= 0.7 and score_cn >= score_west + 0.2:
        mode = "Chinese"
    elif score_west >= 0.7 and score_west >= score_cn + 0.2:
        mode = "Western"
    else:
        mode = "Mixed"

    return ModeScore(
        chinese_score=score_cn,
        western_score=score_west,
        mode=mode,
        evidence_cn=evidence_cn,
        evidence_west=evidence_west,
    )


def identify_surname_position_v7(
    original_name: str,
    lastname: Optional[str] = None,
    firstname: Optional[str] = None,
    affiliation: Optional[str] = None,
    mode_hint: Optional[str] = None,
) -> Tuple[Optional[str], float, str]:
    """
    v7.0 姓氏位置识别算法
    v7.0 Surname Position Identification Algorithm

    定义 / Definition:
    - family_first: 姓氏在第一位置 (surname in first position)
    - given_first: 姓氏在最后位置 (surname in last position)
    - unknown: 证据不足 (insufficient evidence)

    Args:
        original_name: 原始姓名（必需）
        lastname: 姓氏（可选，v7不使用）
        firstname: 名字（可选，v7不使用）
        affiliation: 机构信息（可选但强烈推荐）
        mode_hint: 模式提示 ("Chinese" / "Western" / None)

    Returns:
        - order: "family_first" | "given_first" | "unknown"
        - confidence: float [0.0, 1.0]
        - reason: str (推理依据)
    """
    # ========== 预处理 Preprocessing ==========

    # 清洗姓名
    name = original_name.strip()
    if not name:
        return ("unknown", 0.0, "空姓名")

    # 去掉多余符号
    name = re.sub(r'[,\(\)\[\]]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    # 分词
    tokens = name.split()
    if len(tokens) < 2:
        return ("unknown", 0.0, f"姓名格式不符({len(tokens)}个token)")

    # 提取首尾token（忽略中间名缩写）
    # 缩写模式：A., J.M., A.B.C.等
    abbrev_pattern_filter = r'^[A-Z](\.[A-Z])*\.?$'
    clean_tokens = [t for t in tokens if not re.fullmatch(abbrev_pattern_filter, t)]

    if len(clean_tokens) < 2:
        clean_tokens = tokens

    first_token = clean_tokens[0]
    last_token = clean_tokens[-1]

    # 记录是否有连字符
    has_hyphen = ('-' in name)

    # ========== 特殊情况：缩写检测 Abbreviation Detection ==========

    # 科学文献中常见格式："Liu W." 或 "Chen J.M."
    # 缩写模式：单字母或多字母缩写（如A., J.M., A.B.C.）
    abbrev_pattern = r'^[A-Z](\.[A-Z])*\.?$'

    if len(tokens) == 2:
        if re.match(abbrev_pattern, tokens[1]):
            return ("family_first", 1.0,
                   f"缩写格式: {tokens[0]} {tokens[1]} → 姓在前")

    if len(tokens) >= 3:
        if all(re.match(abbrev_pattern, t) for t in tokens[1:]):
            return ("family_first", 1.0,
                   f"缩写格式: {tokens[0]} + 缩写 → 姓在前")

    # ========== 机构分析 Affiliation Analysis ==========

    affil_info = None
    if affiliation:
        affil_info = analyze_affiliation(affiliation)

    # ========== 模式识别 Mode Recognition ==========

    mode_score = calculate_mode_scores(
        original_name, first_token, last_token, affil_info
    )

    # 如果有外部模式提示，优先使用
    if mode_hint in ["Chinese", "Western"]:
        mode = mode_hint
    else:
        mode = mode_score.mode

    # ========== 姓氏检测 Surname Detection ==========

    first_is_surname = is_surname_pinyin(first_token)
    last_is_surname = is_surname_pinyin(last_token)

    first_variants = get_surname_from_pinyin(first_token) if first_is_surname else []
    last_variants = get_surname_from_pinyin(last_token) if last_is_surname else []

    # ========== 名字模式检测 Given Name Pattern Detection ==========

    # v7.0: 使用拼音合法性检测
    first_given_conf, first_given_reason = calculate_given_name_confidence_v7(first_token)
    last_given_conf, last_given_reason = calculate_given_name_confidence_v7(last_token)

    # ========== 西方姓氏检测 Western Surname Detection ==========

    first_is_western = is_likely_western_name(first_token)
    last_is_western = is_likely_western_name(last_token)

    # ========== 决策层 Decision Layer ==========

    evidence = []
    confidence = 0.0

    # === 模式1: Chinese Mode ===
    if mode == "Chinese":
        # 中文模式：优先匹配中文姓氏库

        # 情况1: first是姓 + last不是姓 → family_first
        if first_is_surname and not last_is_surname:
            confidence = 0.6
            evidence.append(f"{first_token}是姓氏→{first_variants[:2]}")

            # Boost: last是合法拼音名
            if last_given_conf > 0.5:
                confidence += 0.3
                evidence.append(f"{last_token}是拼音名(conf={last_given_conf:.2f})")

            # Boost: 中国机构
            if affil_info and affil_info.is_chinese:
                confidence += 0.2
                evidence.append("中国机构")

            return ("family_first", min(confidence, 1.0),
                   f"姓氏在第一位置（中文顺序）: {'; '.join(evidence)}")

        # 情况2: last是姓 + first不是姓 → given_first
        if last_is_surname and not first_is_surname:
            confidence = 0.6
            evidence.append(f"{last_token}是姓氏→{last_variants[:2]}")

            # Boost: first是合法拼音名
            if first_given_conf > 0.5:
                confidence += 0.3
                evidence.append(f"{first_token}是拼音名(conf={first_given_conf:.2f})")

            # Boost: 中国机构
            if affil_info and affil_info.is_chinese:
                confidence += 0.2
                evidence.append("中国机构")

            return ("given_first", min(confidence, 1.0),
                   f"姓氏在最后位置（西方顺序）: {'; '.join(evidence)}")

        # 情况3: 双姓氏（Wei Chen, Li Wang等）
        if first_is_surname and last_is_surname:
            first_rank = get_surname_frequency_rank(first_token)
            last_rank = get_surname_frequency_rank(last_token)

            evidence.append(f"{first_token}是姓氏→{first_variants[:2]}")
            evidence.append(f"{last_token}是姓氏→{last_variants[:2]}")

            # v7.0修正：在Chinese模式下，双姓氏默认family_first（姓在前）
            # 因为中文数据库中的姓名通常是"姓 名"格式
            # 只有在明确是国际文献（有中国机构但没有其他中文证据）时才用频率
            if mode == "Chinese":
                # Chinese模式：默认姓在前
                return ("family_first", 0.7,
                       f"Chinese模式-双姓氏默认姓在前: {'; '.join(evidence)}")

            # Western/Mixed模式：使用频率排序
            # 选择更常见的姓氏在后（西方顺序更普遍）
            if first_rank and last_rank and abs(first_rank - last_rank) > 20:
                if last_rank < first_rank:  # last更常见
                    return ("given_first", 0.7,
                           f"双姓氏: {last_token}更常见(rank {last_rank} vs {first_rank}); {'; '.join(evidence)}")
                else:  # first更常见
                    return ("family_first", 0.7,
                           f"双姓氏: {first_token}更常见(rank {first_rank} vs {last_rank}); {'; '.join(evidence)}")

            # 频率差距不大，Mixed模式默认given_first
            return ("given_first", 0.6,
                   f"双姓氏频率相近-默认西方顺序: {'; '.join(evidence)}")

        # 情况4: 都不是姓氏，但有其他中文证据
        if mode_score.chinese_score >= 0.5:
            # 有中文证据但没有姓氏匹配
            # 可能是罕见姓氏或拼音变体
            # 返回unknown而不是强制给一个答案
            return ("unknown", 0.4,
                   f"中文证据但无姓氏匹配: {'; '.join(mode_score.evidence_cn)}")

        # 情况5: 完全没有中文证据
        # 虽然模式是Chinese，但实际没有证据
        # 可能是模式判断错误，返回unknown
        return ("unknown", 0.3,
               f"Chinese模式但证据不足: {'; '.join(evidence)}")

    # === 模式2: Western Mode ===
    elif mode == "Western":
        # 西方模式：优先识别西方姓氏特征

        # W1: last_token是西方姓氏 → given_first
        if last_is_western or is_common_western_surname(last_token):
            confidence = 0.8
            evidence.append(f"{last_token}是西方姓氏")

            # 额外检查：first是否也是西方姓氏（罕见但可能）
            if first_is_western:
                confidence = 0.7  # 降低置信度
                evidence.append(f"{first_token}也可能是西方姓氏")

            return ("given_first", confidence,
                   f"西方姓氏在最后位置: {'; '.join(evidence)}")

        # W2: first_token是西方姓氏 → family_first（罕见但可能）
        if first_is_western or is_common_western_surname(first_token):
            confidence = 0.6
            evidence.append(f"{first_token}是西方姓氏")
            return ("family_first", confidence,
                   f"西方姓氏在第一位置（罕见）: {'; '.join(evidence)}")

        # W3: 偶然姓氏匹配处理（如Mo A. Verhoeven）
        if first_is_surname and last_is_western:
            # first恰好命中中文姓氏，但last明显是西方姓
            # Western模式下，优先认为是西方顺序
            confidence = 0.7
            evidence.append(f"{last_token}是西方姓氏")
            evidence.append(f"{first_token}虽然是中文姓但可能是西方名")
            return ("given_first", confidence,
                   f"Western模式优先: {'; '.join(evidence)}")

        # W4: 无任何中文证据 → 默认给given_first
        # **这是v7.0的关键改进**：避免返回unknown
        if mode_score.chinese_score < 0.3:
            confidence = 0.6
            evidence.append("无中文证据")
            evidence.append("默认西方顺序")
            return ("given_first", confidence,
                   f"Western模式默认: {'; '.join(evidence)}")

        # W5: 有少量中文证据但不足
        # 仍然偏向given_first，但降低置信度
        if mode_score.chinese_score < 0.6:
            confidence = 0.5
            evidence.append("中文证据不足")
            evidence.append("Western模式默认given_first")
            return ("given_first", confidence,
                   f"Western模式偏向: {'; '.join(evidence)}")

        # W6: 中文证据较强，但仍在Western模式
        # 可能是模式判断错误，返回unknown
        return ("unknown", 0.4,
               f"Western模式但有中文证据: CN={mode_score.chinese_score:.2f}")

    # === 模式3: Mixed Mode ===
    else:  # mode == "Mixed"
        # 混合模式：证据不明确

        # M1: 如果有姓氏匹配，但证据不足
        if first_is_surname or last_is_surname:
            if first_is_surname:
                evidence.append(f"{first_token}是姓氏")
            if last_is_surname:
                evidence.append(f"{last_token}是姓氏")

            # 有姓氏但其他证据不够，给低置信度判断
            if first_is_surname and not last_is_surname:
                return ("family_first", 0.6,
                       f"Mixed模式-姓氏在前: {'; '.join(evidence)}")
            elif last_is_surname and not first_is_surname:
                return ("given_first", 0.6,
                       f"Mixed模式-姓氏在后: {'; '.join(evidence)}")

        # M2: 完全没有姓氏匹配 → 默认given_first（轻微偏向西方）
        if not first_is_surname and not last_is_surname:
            confidence = 0.5
            evidence.append("无姓氏匹配")
            evidence.append("默认西方顺序")
            return ("given_first", confidence,
                   f"Mixed模式默认: {'; '.join(evidence)}")

        # M3: 其他疑难情况 → unknown
        return ("unknown", 0.4,
               f"Mixed模式-证据不足: CN={mode_score.chinese_score:.2f}, "
               f"West={mode_score.western_score:.2f}")


# 向后兼容
identify_surname_position = identify_surname_position_v7
