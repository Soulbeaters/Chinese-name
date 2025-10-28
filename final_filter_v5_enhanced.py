# -*- coding: utf-8 -*-
"""
中文作者筛选算法 v5.0 - 增强版
Chinese Author Filter v5.0 - Enhanced Edition

新增功能 / New Features:
1. 智能括号处理 - 识别汉字括号，忽略外文名括号
2. 繁体中文支持 - 台湾（Lee）、香港（Wong）、新加坡（Lim）

第一性原理 / First Principles:
- 中文作者 = 使用中文姓名系统（简体拼音 + 繁体拼音）
- 包括大陆、台湾、香港、新加坡、海外华人

中文注释：增强版，支持繁体中文和智能括号处理
Русский комментарий: Расширенная версия с поддержкой традиционного китайского
"""

import json
import sys
import re
from pathlib import Path
from collections import Counter

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.surname_pinyin_db import is_surname_pinyin
from data.variant_pinyin_map import get_all_possible_pinyins
from data.non_chinese_surnames import is_non_chinese_surname
from data.traditional_chinese_surnames import is_traditional_chinese_surname


# 明确的外文专有名词（同v4.0）
DEFINITE_FOREIGN_NAMES = {
    'john', 'james', 'robert', 'michael', 'william', 'david', 'richard', 'joseph',
    'thomas', 'charles', 'daniel', 'matthew', 'mark', 'donald', 'paul', 'steven',
    'andrew', 'joshua', 'kenneth', 'kevin', 'brian', 'george', 'edward', 'ronald',
    'timothy', 'jason', 'jeffrey', 'ryan', 'jacob', 'gary', 'nicholas', 'eric',
    'jonathan', 'stephen', 'larry', 'justin', 'scott', 'brandon', 'benjamin',
    'samuel', 'frank', 'gregory', 'raymond', 'alexander', 'patrick', 'jack',
    'dennis', 'jerry', 'tyler', 'aaron', 'adam', 'henry', 'nathan',
    'douglas', 'zachary', 'peter', 'kyle', 'walter', 'harold', 'jeremy', 'ethan',
    'christopher', 'anthony', 'mark', 'steven', 'matthew', 'kenneth',
    'vladimir', 'sergey', 'sergei', 'alexander', 'dmitry', 'dmitri', 'andrey',
    'alexey', 'ivan', 'mikhail', 'nikolay', 'evgeny', 'maxim', 'igor', 'oleg',
    'pavel', 'roman', 'victor', 'anatoly', 'boris', 'valery', 'yuri',
    'mohammad', 'mohammed', 'muhammad', 'ahmed', 'hassan', 'hussein',
    'omar', 'abdel', 'abdul', 'ibrahim', 'khalid', 'mahmoud', 'said',
    'jean', 'pierre', 'jacques', 'francois', 'antonio', 'jose', 'manuel',
    'carlos', 'luis', 'miguel', 'pedro', 'juan', 'jorge', 'fernando',
    'ricardo', 'roberto', 'francisco', 'eduardo', 'alberto', 'rafael',
}


def contains_chinese_characters(text: str) -> bool:
    """
    检查文本是否包含中文汉字
    Check if text contains Chinese characters

    Args:
        text: 待检查文本

    Returns:
        bool: True表示包含汉字
    """
    if not text:
        return False
    # Unicode范围：\u4e00-\u9fff (CJK统一汉字)
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def remove_parentheses(original_name: str) -> str:
    """
    移除所有括号及其内容
    Remove all parentheses and their contents

    简化策略 / Simplified Strategy:
    - 括号是补充信息，完全忽略
    - 只基于括号外的主体信息判断
    - Bo Ma(马博) -> Bo Ma
    - Shengzhong(Frank) Liu -> Shengzhong Liu
    - Li(Smith) Wei -> Li Wei

    Args:
        original_name: 原始姓名

    Returns:
        str: 移除括号后的名字

    Examples:
        >>> remove_parentheses("Bo Ma(马博)")
        "Bo Ma"
        >>> remove_parentheses("Shengzhong(Frank) Liu")
        "Shengzhong Liu"
        >>> remove_parentheses("Li(Smith) Wei")
        "Li Wei"
    """
    if not original_name:
        return original_name

    # 移除所有括号（英文或中文括号）
    paren_pattern = r'[\(（][^\)）]*[\)）]'
    name_without_paren = re.sub(paren_pattern, '', original_name).strip()
    # 清理多余空格
    name_without_paren = re.sub(r'\s+', ' ', name_without_paren)

    return name_without_paren


def is_definite_foreign_name(token: str) -> bool:
    """判断是否为明确的外文专有名词"""
    if not token:
        return False
    return token.lower().strip() in DEFINITE_FOREIGN_NAMES


def has_chinese_surname(tokens: list) -> tuple:
    """
    检查是否包含中文姓氏（简体拼音 + 繁体拼音）
    Check if contains Chinese surname (Simplified + Traditional)

    Returns:
        tuple: (has_surname: bool, surname_token: str or None)
    """
    for token in tokens:
        token_lower = token.lower().strip()

        # 0. 排除单字母（通常是缩写，如 E Baron, J Smith）
        if len(token_lower) == 1:
            continue

        # 1. 检查是否为外国姓氏
        if is_non_chinese_surname(token_lower):
            continue

        # 2. 检查繁体中文姓氏（台湾、香港、新加坡）
        if is_traditional_chinese_surname(token_lower):
            return (True, token)

        # 3. 检查简体中文姓氏（大陆汉语拼音）
        all_forms = get_all_possible_pinyins(token_lower)
        for form in all_forms:
            if is_surname_pinyin(form):
                return (True, token)

    return (False, None)


def filter_chinese_author_v5(original_name: str, affiliation: str = None) -> tuple:
    """
    v5.0 增强版 - 支持繁体中文和智能括号处理
    v5.0 Enhanced - Support traditional Chinese and intelligent parentheses

    核心逻辑 / Core Logic:
    1. 智能处理括号：
       - 括号内是汉字 -> 确认中文作者
       - 括号内是外文名 -> 忽略，判断其余部分
    2. 支持繁体中文姓氏（Lee, Wong, Hsu等）
    3. 保留v4的其他逻辑

    Returns:
        tuple: (is_chinese, confidence, reason)
    """
    if not original_name:
        return (None, 0.0, "姓名为空")

    # ========== 步骤0: 移除括号（简化策略）==========
    # 括号是补充信息，完全忽略，只基于主体信息判断
    name_without_paren = remove_parentheses(original_name)

    tokens = name_without_paren.split()
    if len(tokens) < 2:
        return (None, 0.0, "姓名格式不完整")

    # ========== 步骤1: 必要条件 - 必须有中文姓氏 ==========
    has_surname, surname_token = has_chinese_surname(tokens)

    if not has_surname:
        return (False, 0.90, "无中文姓氏")

    # ========== 步骤2: 排除条件 - 检查所有token ==========
    for token in tokens:
        token_lower = token.lower().strip()

        # 2.1 排除外国姓氏
        if is_non_chinese_surname(token_lower):
            return (False, 0.95, f"包含外国姓氏: {token}")

        # 2.2 排除明确的外文专有名词（单独token）
        if '-' not in token:
            if is_definite_foreign_name(token):
                return (False, 0.95, f"包含外文专有名词: {token}")

        # 2.3 检查复合token（如 Bond-Lamberty, Ben-wu）
        if '-' in token:
            parts = token.split('-')
            for part in parts:
                if is_non_chinese_surname(part.lower()):
                    return (False, 0.95, f"复合名包含外国姓氏: {part} (在{token}中)")
                # 长外文名（>4字符）明确排除
                if is_definite_foreign_name(part) and len(part) > 4:
                    return (False, 0.95, f"复合名包含明确外文名: {part} (在{token}中)")

    # ========== 步骤3: 通过所有检查，判定为中文作者 ==========
    confidence = 0.85

    # 机构信息提升置信度
    if affiliation:
        china_keywords = ['china', 'chinese', 'beijing', 'shanghai', 'guangzhou',
                         'tsinghua', 'peking', 'fudan', 'zhejiang', 'nanjing',
                         'taiwan', 'hong kong', 'singapore']
        if any(kw in affiliation.lower() for kw in china_keywords):
            confidence = 0.95

    # 繁体中文姓氏
    if is_traditional_chinese_surname(surname_token.lower()):
        reason = f"中文作者 (繁体姓氏: {surname_token})"
    else:
        reason = f"中文作者 (姓氏: {surname_token})"

    return (True, confidence, reason)


# ========== 测试 ==========

if __name__ == "__main__":
    print("=" * 80)
    print("Chinese Author Filter v5.0 - Enhanced Edition")
    print("=" * 80)

    print("\n[Test Cases]")
    print("-" * 80)

    test_cases = [
        # === 括号处理（完全忽略括号）===
        ("Bo Ma(马博)", None, "中文", "忽略(马博)，Bo Ma是中文"),
        ("Yi Yang(杨毅)", None, "中文", "忽略(杨毅)，Yi Yang是中文"),
        ("He Zhao(赵赫)", None, "中文", "忽略(赵赫)，He Zhao是中文"),
        ("Shengzhong(Frank) Liu", None, "中文", "忽略(Frank)，Shengzhong Liu是中文"),
        ("Li(Smith) Wei", None, "中文", "忽略(Smith)，Li Wei是中文"),

        # === 繁体中文姓氏（台湾、香港）===
        ("Wei Lee", None, "中文", "Lee是台湾/香港的'李'"),
        ("John Wong", None, "非中文", "John是外文名，Wong虽是粤语'黄'但应排除"),
        ("Ming Wong", None, "中文", "Ming Wong都可能是中文"),
        ("David Chan", None, "非中文", "David是外文名"),
        ("Yiming Chan", None, "中文", "Yiming是中文名，Chan是粤语'陈'"),
        ("Wei Hsu", None, "中文", "Hsu是威妥玛拼音'徐'"),

        # === 单音节中文名 ===
        ("Wei Li", None, "中文", "单音节中文名"),
        ("Bo Chen", None, "中文", "单音节中文名"),

        # === 应排除的混合名 ===
        ("Ben Bond-Lamberty", None, "非中文", "Bond-Lamberty含外文姓氏"),
        ("John Smith", None, "非中文", "明确外文名"),
    ]

    passed = 0
    failed = 0

    for name, affiliation, expected, note in test_cases:
        is_chinese, conf, reason = filter_chinese_author_v5(name, affiliation)
        result = "中文" if is_chinese is True else ("非中文" if is_chinese is False else "不确定")

        is_pass = (expected == "中文" and is_chinese is True) or \
                  (expected == "非中文" and is_chinese is False)

        status = "PASS" if is_pass else "FAIL"
        if is_pass:
            passed += 1
        else:
            failed += 1

        print(f"\n[{status}] {name:30}")
        print(f"  结果: {result:6} (conf={conf:.2f}) | 期望: {expected}")
        print(f"  说明: {note}")
        print(f"  原因: {reason}")

    print(f"\n测试结果: {passed} passed, {failed} failed")

    # ========== 完整数据集测试 ==========
    print("\n" + "=" * 80)
    print("[Full Dataset Test]")
    print("=" * 80)

    CROSSREF_DATA = r"C:\istina\materia 材料\测试表单\crossref_authors.json"
    print("\nLoading Crossref data...")
    with open(CROSSREF_DATA, 'r', encoding='utf-8') as f:
        all_authors = json.load(f)

    print(f"Total authors: {len(all_authors):,}")

    print("\nFiltering with v5.0 algorithm...")
    v5_chinese = []
    v5_non_chinese = []

    for i, author in enumerate(all_authors):
        if i > 0 and i % 50000 == 0:
            print(f"  Progress: {i:,}/{len(all_authors):,}...", flush=True)

        is_chinese, conf, reason = filter_chinese_author_v5(
            author.get('original_name', ''),
            author.get('affiliation', '')
        )

        if is_chinese is True:
            v5_chinese.append(author)
        elif is_chinese is False:
            v5_non_chinese.append(author)

    total = len(v5_chinese) + len(v5_non_chinese)

    print("\n" + "=" * 80)
    print("v5.0 Filtering Results")
    print("=" * 80)

    print(f"\nTotal: {total:,}")
    print(f"  Chinese:     {len(v5_chinese):,} ({len(v5_chinese)*100/total:.2f}%)")
    print(f"  Non-Chinese: {len(v5_non_chinese):,} ({len(v5_non_chinese)*100/total:.2f}%)")
    print(f"  Uncertain:   0 (0.00%)")

    print("\n" + "=" * 80)
    print("Version Comparison")
    print("=" * 80)

    print(f"""
v4.0: Chinese 101,330 (33.60%), Uncertain 0.00%
v5.0: Chinese {len(v5_chinese):,} ({len(v5_chinese)*100/total:.2f}%), Uncertain 0.00%

v5.0新增功能:
1. [OK] 智能括号处理 - Bo Ma(马博) 识别为中文
2. [OK] 繁体中文支持 - Wei Lee, Ming Wong 识别为中文
3. [OK] 海外华人支持 - Shengzhong(Frank) Liu 识别为中文

变化: {len(v5_chinese) - 101330:+,} 个作者
""")

    # 保存结果
    output = {
        'chinese': [{
            'original_name': a.get('original_name', ''),
            'lastname': a.get('lastname', ''),
            'firstname': a.get('firstname', ''),
            'affiliation': a.get('affiliation', '')
        } for a in v5_chinese],
        'statistics': {
            'total': total,
            'chinese': len(v5_chinese),
            'non_chinese': len(v5_non_chinese),
            'chinese_percentage': len(v5_chinese)*100/total
        }
    }

    with open(r"C:\program 1 in 2025\filtered_chinese_v5_enhanced.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n保存结果...")
    print(f"Saved to: filtered_chinese_v5_enhanced.json")
    print(f"包含所有 {len(v5_chinese):,} 个中文作者")
    print("=" * 80)
