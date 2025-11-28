# -*- coding: utf-8 -*-
"""
拼音合法性检测器 / Pinyin Validity Checker
使用动态规划实现拼音音节分词，判断token是否是合法拼音组合

作者 / Author: Ma Jiaxin
日期 / Date: 2025-11-28
"""

import re
from typing import Tuple, List, Optional
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.pinyin_syllables import (
    PINYIN_SYLLABLES,
    COMMON_GIVEN_NAME_SYLLABLES,
    is_valid_pinyin_syllable,
    is_common_given_name_syllable,
)


def segment_pinyin(token: str) -> Tuple[bool, int, List[str]]:
    """
    使用动态规划将token分词为拼音音节
    Segment token into Pinyin syllables using Dynamic Programming

    Args:
        token: 待分词的token（字符串）

    Returns:
        - is_valid: bool, 是否可以完全分词为合法拼音
        - syllable_count: int, 音节数量
        - syllables: List[str], 音节列表
    """
    # 预处理：小写化，去掉连字符
    t = token.lower().replace('-', '').replace("'", '')

    # 只保留a-z字符
    if not re.fullmatch(r'[a-z]+', t):
        return False, 0, []

    # 边界情况：空字符串
    if not t:
        return False, 0, []

    n = len(t)

    # DP数组：dp[i] = True表示前i个字符可以分词
    dp = [False] * (n + 1)
    dp[0] = True

    # 记录分词路径
    syllables_count = [0] * (n + 1)
    parent = [-1] * (n + 1)  # 记录上一个分词点
    used_syllable = [''] * (n + 1)  # 记录使用的音节

    # DP填表
    for i in range(n):
        if not dp[i]:
            continue

        # 尝试从位置i开始匹配音节
        for syllable in PINYIN_SYLLABLES:
            syl_len = len(syllable)
            if i + syl_len > n:
                continue

            # 检查是否匹配
            if t[i:i+syl_len] == syllable:
                j = i + syl_len
                if not dp[j]:
                    dp[j] = True
                    syllables_count[j] = syllables_count[i] + 1
                    parent[j] = i
                    used_syllable[j] = syllable

    # 检查是否能完全分词
    is_valid = dp[n]
    count = syllables_count[n]

    # 回溯获取音节列表
    syllables = []
    if is_valid:
        pos = n
        while pos > 0:
            syllables.append(used_syllable[pos])
            pos = parent[pos]
        syllables.reverse()

    return is_valid, count, syllables


def is_valid_pinyin_name(token: str) -> Tuple[bool, int, List[str]]:
    """
    判断token是否是合法的拼音名字
    Check if token is a valid Pinyin name

    这是v7.0算法中替代calculate_given_name_confidence的核心函数

    Args:
        token: 待检查的token

    Returns:
        - is_valid: bool, 是否是合法拼音名
        - syllable_count: int, 音节数
        - syllables: List[str], 音节列表
    """
    return segment_pinyin(token)


def calculate_given_name_confidence_v7(token: str) -> Tuple[float, str]:
    """
    v7.0版本：基于拼音合法性的名字置信度计算
    v7.0 version: Given name confidence based on Pinyin validity

    核心改进 / Key Improvement:
    - 从"长度+元音数"改为"拼音合法性+音节数"
    - 只有真正的拼音才会得分，Savolainen/Desrichard等西方姓氏直接返回0

    Args:
        token: 待检查的token

    Returns:
        - confidence: float [0.0, 1.0], 置信度
        - reason: str, 推理依据
    """
    # 调用拼音分词
    is_valid, syllable_count, syllables = is_valid_pinyin_name(token)

    # 如果无法分词为合法拼音 → 置信度0
    if not is_valid:
        return 0.0, f"{token}不是合法拼音"

    # 基于音节数判断
    if syllable_count == 2 or syllable_count == 3:
        # 2-3音节是典型中文名
        confidence = 0.8

        # 微调：如果包含常见名字音节，再加一点
        common_count = sum(1 for syl in syllables if is_common_given_name_syllable(syl))
        if common_count >= 1:
            confidence = min(confidence + 0.1, 0.9)

        reason = f"{token}是合法拼音({syllable_count}音节: {'-'.join(syllables)})"
        return confidence, reason

    elif syllable_count == 1 and len(token) <= 4:
        # 单音节短名（Bo, Lin, Wei等）
        # 置信度中等，因为也可能是西方名字的一部分
        reason = f"{token}是单音节拼音({syllables[0]})"
        return 0.5, reason

    elif syllable_count >= 4:
        # 音节过多，不太像名字
        reason = f"{token}音节过多({syllable_count}个)"
        return 0.2, reason

    else:
        # 其他情况
        return 0.0, f"{token}不符合名字模式"


