# -*- coding: utf-8 -*-
"""
姓氏位置识别算法 v6.0 / Surname Position Identifier v6.0
Алгоритм определения позиции фамилии v6.0

核心改进 / Core Improvements:
1. 修复v5.0的逻辑BUG（姓氏位置判断完全颠倒）
2. 增强中文名字模式识别（Mingyuan, Tianxiang等）
3. 改进缩写处理（支持多点缩写）
4. 统一使用位置定义（family_first=姓氏在第一位置）
5. 增强姓氏频率权重

Author: Ma Jiaxin
Date: 2025-11-28
Version: 6.0
"""

import re
import sys
from pathlib import Path
from typing import Tuple, Optional

# 添加项目根目录到路径 / Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入数据库 / Import databases
from data.surname_pinyin_db import is_surname_pinyin, get_surname_from_pinyin
from data.variant_pinyin_map import get_all_possible_pinyins
from data.non_chinese_surnames import is_non_chinese_surname, get_surname_origin
from data.surname_frequency import get_surname_frequency_rank, compare_surname_frequency


def is_chinese_given_name_pattern(text: str) -> bool:
    """
    增强版：判断是否符合中文名字模式 / Enhanced: Check if matches Chinese given name pattern

    中文名字特征 / Chinese given name characteristics:
    1. 通常2-3个音节（如Mingyuan, Tianxiang, Zhongxiao）
    2. 不是常见姓氏
    3. 长度通常>=5个字母
    4. 包含特定音节模式

    Args:
        text: 待检查的文本 / Text to check

    Returns:
        bool: 是否符合中文名字模式 / Whether matches Chinese given name pattern
    """
    if not text:
        return False

    text_lower = text.lower().strip()

    # 连字符是强烈的中文名信号 / Hyphen is strong Chinese name signal
    if '-' in text_lower:
        return True

    # 计算音节数（简化：元音组数量）/ Count syllables (simplified: vowel groups)
    vowel_groups = len(re.findall(r'[aeiou]+', text_lower))

    # 长度和音节数分析 / Length and syllable analysis
    length = len(text_lower)

    # 中文名通常较长且多音节 / Chinese given names are usually longer and multi-syllabic
    if length >= 6 and vowel_groups >= 2:
        return True  # 如 "Mingyuan", "Zhongxiao", "Tianxiang"

    # 中等长度且双音节 / Medium length with two syllables
    if length >= 5 and vowel_groups == 2:
        return True  # 如 "Shenghui", "Taiping"

    # 短名字可能是韩国名或单音节名 / Short names may be Korean or single-syllable
    if length <= 4 and vowel_groups <= 2:
        return False  # 如 "Min", "Ran", "Yu"

    return False


def is_abbreviation_token(token: str) -> bool:
    """
    检查是否为缩写token / Check if token is abbreviation

    缩写特征 / Abbreviation characteristics:
    - 包含点号
    - 去掉点号后长度<=3
    - 以字母开头

    Args:
        token: token字符串 / Token string

    Returns:
        bool: 是否为缩写 / Whether is abbreviation
    """
    if not token or '.' not in token:
        return False

    if not token[0].isalpha():
        return False

    # 去掉所有点号后检查长度 / Check length after removing all dots
    clean_token = token.replace('.', '')
    return len(clean_token) <= 3


def calculate_given_name_confidence(token: str) -> float:
    """
    计算token作为名字的置信度 / Calculate confidence that token is a given name

    Args:
        token: token字符串 / Token string

    Returns:
        float: 置信度0.0-1.0 / Confidence 0.0-1.0
    """
    if not token:
        return 0.0

    confidence = 0.0
    text_lower = token.lower().strip()
    length = len(text_lower)

    # 特征1: 连字符（强信号）/ Feature 1: Hyphen (strong signal)
    if '-' in text_lower:
        confidence += 0.6

    # 特征2: 长度 / Feature 2: Length
    if length >= 7:
        confidence += 0.4  # 很长，很可能是名字 / Very long, likely given name
    elif length >= 5:
        confidence += 0.3  # 中等长度 / Medium length
    elif length <= 3:
        confidence -= 0.2  # 太短 / Too short

    # 特征3: 音节数 / Feature 3: Syllable count
    vowel_groups = len(re.findall(r'[aeiou]+', text_lower))
    if vowel_groups >= 3:
        confidence += 0.3  # 3+音节 / 3+ syllables
    elif vowel_groups == 2:
        confidence += 0.2  # 2音节 / 2 syllables

    # 特征4: 特定模式 / Feature 4: Specific patterns
    # 双重辅音（如 "ng", "zh", "sh"）/ Double consonants
    if re.search(r'(ng|zh|sh|ch|th)', text_lower):
        confidence += 0.1

    return min(confidence, 1.0)


def identify_surname_position_v6(
    original_name: str,
    lastname: Optional[str] = None,
    firstname: Optional[str] = None,
    affiliation: Optional[str] = None
) -> Tuple[Optional[str], float, str]:
    """
    v6.0算法：识别姓氏位置 / v6.0: Identify surname position

    修复v5.0的核心BUG并增强特征识别 / Fix v5.0 core bug and enhance feature recognition

    定义 / Definition:
    - family_first: 姓氏在第一位置（如"Zhang Wei"中Zhang在第一）
    - given_first: 姓氏在最后位置（如"Wei Zhang"中Zhang在最后）

    Args:
        original_name: 完整姓名 / Full name
        lastname: Crossref标注的lastname（可选）/ Crossref lastname (optional)
        firstname: Crossref标注的firstname（可选）/ Crossref firstname (optional)
        affiliation: 机构信息（可选）/ Affiliation (optional)

    Returns:
        Tuple[str, float, str]: (判断结果, 置信度, 推理依据)
            - 判断结果: "family_first" | "given_first" | "unknown"
            - 置信度: 0.0-1.0
            - 推理依据: 详细解释
    """
    if not original_name:
        return ("unknown", 0.0, "姓名为空")

    # 解析姓名 / Parse name
    parts = original_name.split()
    if len(parts) < 2:
        return ("unknown", 0.0, "姓名格式不完整")

    # 提取第一个和最后一个token / Extract first and last tokens
    first_token = parts[0].strip()
    last_token = parts[-1].strip()

    confidence = 0.0
    evidence = []

    # ========== 优先规则1: 缩写姓名处理 ==========
    # 科学文献中的缩写格式: "Liu W." / "Chen J.M." / "Lin Y.T." 总是"姓 名缩写"
    if len(parts) >= 2:
        other_parts = parts[1:]
        all_abbreviations = all(is_abbreviation_token(p) for p in other_parts)

        if all_abbreviations:
            # 检查第一部分是否为中文姓氏
            first_all_forms = get_all_possible_pinyins(first_token.lower())
            for form in first_all_forms:
                if is_surname_pinyin(form):
                    surnames = get_surname_from_pinyin(form)
                    return ("family_first", 0.95,
                           f"缩写格式: {first_token}({surnames}) + 名缩写{' '.join(other_parts)}")

    # ========== 证据收集阶段 ==========

    # 证据1: 排除明显非中文姓氏 / Evidence 1: Exclude non-Chinese surnames
    if is_non_chinese_surname(last_token.lower()):
        origin = get_surname_origin(last_token.lower())
        return ("given_first", 0.95, f"西方顺序：{last_token}是{origin}姓氏")

    if is_non_chinese_surname(first_token.lower()):
        origin = get_surname_origin(first_token.lower())
        return ("given_first", 0.90, f"西方顺序：{first_token}是{origin}姓氏")

    # 证据2: 姓氏拼音匹配 / Evidence 2: Surname pinyin matching
    first_is_surname = False
    last_is_surname = False

    # 检查first_token / Check first_token
    first_all_forms = get_all_possible_pinyins(first_token.lower())
    for form in first_all_forms:
        if is_surname_pinyin(form):
            surnames = get_surname_from_pinyin(form)
            confidence += 0.3
            evidence.append(f"{first_token}是姓氏→{surnames}")
            first_is_surname = True
            break

    # 检查last_token / Check last_token
    last_all_forms = get_all_possible_pinyins(last_token.lower())
    for form in last_all_forms:
        if is_surname_pinyin(form):
            surnames = get_surname_from_pinyin(form)
            confidence += 0.6
            evidence.append(f"{last_token}是姓氏→{surnames}")
            last_is_surname = True
            break

    # 证据3: 姓氏频率先验（处理双姓氏歧义）/ Evidence 3: Surname frequency prior
    if first_is_surname and last_is_surname:
        freq_comparison = compare_surname_frequency(first_token.lower(), last_token.lower())

        if freq_comparison['confidence'] > 0.7:
            if freq_comparison['more_common'] == first_token.lower():
                # first_token更常见作为姓氏
                confidence += 0.3
                evidence.append(f"{first_token}更常见姓氏(rank {freq_comparison['rank1']} vs {last_token} rank {freq_comparison['rank2']})")
            elif freq_comparison['more_common'] == last_token.lower():
                # last_token更常见作为姓氏
                confidence += 0.4
                evidence.append(f"{last_token}更常见姓氏(rank {freq_comparison['rank2']} vs {first_token} rank {freq_comparison['rank1']})")
        else:
            evidence.append(f"双姓氏歧义：{first_token}和{last_token}频率相近")

    # 证据4: 名字模式分析（v6.0新增）/ Evidence 4: Given name pattern analysis (v6.0 new)
    first_given_confidence = calculate_given_name_confidence(first_token)
    last_given_confidence = calculate_given_name_confidence(last_token)

    if len(parts) == 2:
        # 两部分姓名 / Two-part name
        if first_given_confidence > 0.5:
            confidence += 0.4
            evidence.append(f"{first_token}符合中文名模式(conf={first_given_confidence:.2f})")

        if last_given_confidence > 0.5:
            confidence += 0.4
            evidence.append(f"{last_token}符合中文名模式(conf={last_given_confidence:.2f})")

    # 证据5: 中国机构信息 / Evidence 5: Chinese affiliation
    if affiliation:
        chinese_keywords = ['china', 'chinese', 'beijing', 'shanghai', 'guangzhou',
                           'tsinghua', 'peking university', 'fudan', 'zhejiang', 'nanjing']
        if any(kw in affiliation.lower() for kw in chinese_keywords):
            confidence += 0.2
            evidence.append("中国机构")

    # ========== 最终判断（v6.0修复逻辑）==========
    # 修复v5.0的BUG：正确映射姓氏位置到返回值

    # 情况1：first_token是姓氏 + last_token不是姓氏 → family_first（姓氏在第一位置）
    if first_is_surname and not last_is_surname:
        # 如果last_token符合名字模式，提高置信度
        if last_given_confidence > 0.5:
            confidence += 0.3
        return ("family_first", min(confidence, 1.0),
                f"姓氏在第一位置（中文顺序）: {'; '.join(evidence)}")

    # 情况2：last_token是姓氏 + first_token不是姓氏 → given_first（姓氏在最后位置）
    if last_is_surname and not first_is_surname:
        # 如果first_token符合名字模式，提高置信度
        if first_given_confidence > 0.5:
            confidence += 0.3
        return ("given_first", min(confidence, 1.0),
                f"姓氏在最后位置（西方顺序）: {'; '.join(evidence)}")

    # 情况3：双姓氏歧义 - 使用名字模式+频率综合判断
    if first_is_surname and last_is_surname:
        # 策略1: 名字模式差异明显
        if last_given_confidence - first_given_confidence > 0.3:
            # last更像名字 → first是姓氏 → family_first
            return ("family_first", min(confidence + 0.2, 1.0),
                   f"双姓氏但{last_token}更像名字: {'; '.join(evidence)}")
        elif first_given_confidence - last_given_confidence > 0.3:
            # first更像名字 → last是姓氏 → given_first
            return ("given_first", min(confidence + 0.2, 1.0),
                   f"双姓氏但{first_token}更像名字: {'; '.join(evidence)}")

        # 策略2: 使用频率判断
        freq_comparison = compare_surname_frequency(first_token.lower(), last_token.lower())
        if freq_comparison['confidence'] > 0.6:
            if freq_comparison['more_common'] == first_token.lower():
                # first更常见 → 可能是姓氏 → family_first
                return ("family_first", min(confidence, 1.0),
                       f"双姓氏选频率更高者: {'; '.join(evidence)}")
            else:
                # last更常见 → 可能是姓氏 → given_first
                return ("given_first", min(confidence, 1.0),
                       f"双姓氏选频率更高者: {'; '.join(evidence)}")

        # 默认：倾向family_first（中文习惯）
        return ("family_first", min(confidence * 0.8, 1.0),
               f"双姓氏歧义（默认中文顺序）: {'; '.join(evidence)}")

    # 情况4：都不是姓氏或证据不足
    if evidence:
        return ("unknown", confidence, f"证据不足: {'; '.join(evidence)}")
    else:
        return ("unknown", 0.0, "无有效证据")


# 向后兼容：提供与v5.0相同的函数名
def identify_surname_position(
    original_name: str,
    lastname: Optional[str] = None,
    firstname: Optional[str] = None,
    affiliation: Optional[str] = None
) -> Tuple[Optional[str], float, str]:
    """
    向后兼容的接口 / Backward compatible interface
    直接调用v6.0算法 / Directly calls v6.0 algorithm
    """
    return identify_surname_position_v6(original_name, lastname, firstname, affiliation)


if __name__ == '__main__':
    print("=" * 80)
    print("姓氏-名字识别算法 v6.0 测试")
    print("Surname-Given Name Identifier v6.0 Test")
    print("=" * 80)

    test_cases = [
        # ISTINA格式测试 / ISTINA format tests
        {
            'original_name': 'Tang Tianxiang',
            'expected': 'family_first',
            'note': 'ISTINA格式：姓名'
        },
        {
            'original_name': 'Liu W.',
            'expected': 'family_first',
            'note': 'ISTINA缩写'
        },
        {
            'original_name': 'Chen J.M.',
            'expected': 'family_first',
            'note': 'ISTINA多点缩写'
        },

        # Crossref格式测试 / Crossref format tests
        {
            'original_name': 'Shenghui Shen',
            'affiliation': 'Tsinghua University, Beijing, China',
            'expected': 'given_first',
            'note': 'Crossref格式：名姓'
        },
        {
            'original_name': 'Mingyuan Zhang',
            'affiliation': 'Beijing Key Laboratory',
            'expected': 'given_first',
            'note': 'Crossref格式：名姓'
        },

        # 西方姓名 / Western names
        {
            'original_name': 'John Smith',
            'expected': 'given_first',
            'note': '西方姓名'
        },

        # 歧义案例 / Ambiguous cases
        {
            'original_name': 'Wei Li',
            'expected': 'given_first',
            'note': '双姓氏歧义'
        },
    ]

    print("\n测试结果 / Test Results:")
    print("-" * 80)

    correct = 0
    total = len(test_cases)

    for i, case in enumerate(test_cases, 1):
        result, conf, reason = identify_surname_position_v6(
            case['original_name'],
            affiliation=case.get('affiliation', '')
        )

        is_correct = (result == case['expected'])
        status = "OK" if is_correct else "FAIL"

        if is_correct:
            correct += 1

        print(f"\n{i}. {case['original_name']:25} ({case['note']})")
        print(f"   Expected: {case['expected']:15} | Result: {result:15} | {status}")
        print(f"   置信度: {conf:.2f} | 理由: {reason}")

    print("\n" + "=" * 80)
    print(f"准确率: {correct}/{total} ({correct/total*100:.1f}%)")
    print("=" * 80)
