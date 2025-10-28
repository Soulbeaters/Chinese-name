# -*- coding: utf-8 -*-
"""
姓氏-名字识别算法 v3.0 - 姓名顺序判断
Surname-Given Name Identifier v3.0 - Name Order Detection

核心任务 / Основная задача:
识别"Wei Li"中哪个是姓氏，哪个是名字
Identify which token is surname and which is given name in "Wei Li"

设计原则 / Принципы дизайна:
1. 主要目标：判断姓名顺序（Family Name First vs Given Name First）
2. 次要目标：识别是否为中文作者（用于排除明显非中文名）
3. 利用中韩名字特征差异：韩国名不使用拼音，名字部分音节模式不同

中文注释：识别英文文献中作者姓名的正确顺序
Русский комментарий：Определение правильного порядка имени и фамилии в англоязычных публикациях
"""

import re
import sys
from pathlib import Path
from typing import Tuple, Dict, Optional

# 添加项目根目录 / Добавление корневой директории
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.surname_pinyin_db import is_surname_pinyin, get_surname_from_pinyin
from data.variant_pinyin_map import get_all_possible_pinyins
from data.non_chinese_surnames import is_non_chinese_surname, get_surname_origin
from data.surname_frequency import compare_surname_frequency, get_surname_frequency_rank


def is_chinese_given_name_pattern(text: str) -> bool:
    """
    判断是否符合中文名字的拼音模式
    Check if text matches Chinese given name pinyin pattern

    中文名特征 / Признаки китайских имён:
    - 2-3个音节 / 2-3 слога
    - 连字符连接（Wei-Hua, Ming-Li）/ Дефис (Wei-Hua, Ming-Li)
    - 典型拼音结构 / Типичная структура пиньинь

    韩国名特征 / Признаки корейских имён:
    - 通常1-2个短音节 / Обычно 1-2 коротких слога
    - 不使用连字符（或使用空格）/ Без дефиса (или с пробелом)
    - 例如：Min, Suji, Dong Hyun
    """
    if not text:
        return False

    text_lower = text.lower().strip()

    # 连字符是强烈的中文名信号 / Дефис - сильный сигнал китайского имени
    if '-' in text_lower:
        return True

    # 计算音节数（简化：元音组数量）/ Подсчёт слогов (упрощённо: группы гласных)
    vowel_groups = len(re.findall(r'[aeiou]+', text_lower))

    # 长度和音节数分析 / Анализ длины и количества слогов
    length = len(text_lower)

    # 中文名通常较长且多音节 / Китайские имена обычно длиннее и многосложные
    if length >= 6 and vowel_groups >= 2:
        return True  # 如 "Mingyuan", "Zhongxiao"

    # 短名字可能是韩国名 / Короткие имена могут быть корейскими
    if length <= 4 and vowel_groups <= 2:
        return False  # 如 "Min", "Ran", "Yu"

    # 中等长度，检查更多特征 / Средняя длина, проверка дополнительных признаков
    # 检查是否有典型中文名拼音组合 / Проверка типичных комбинаций китайских имён
    chinese_patterns = ['ing', 'ang', 'ong', 'eng', 'iao', 'ian', 'uan', 'uang']
    if any(pattern in text_lower for pattern in chinese_patterns):
        return True

    return False


def identify_surname_position(
    original_name: str,
    lastname: Optional[str] = None,
    firstname: Optional[str] = None,
    affiliation: Optional[str] = None
) -> Tuple[Optional[str], float, str]:
    """
    识别姓氏位置 / Определение позиции фамилии
    Identify surname position in author name

    Args:
        original_name: 完整姓名 (如 "Wei Li" 或 "Li Wei")
                       Полное имя (например, "Wei Li" или "Li Wei")
        lastname: Crossref标注的lastname（可能错误）
                  Фамилия по данным Crossref (может быть неверной)
        firstname: Crossref标注的firstname
        affiliation: 机构信息 / Информация об учреждении

    Returns:
        Tuple[str, float, str]:
            - 判断结果 / Результат:
              "family_first": 姓在前（中日韩顺序）/ Фамилия первой (китайский/японский/корейский порядок)
              "given_first": 名在前（西方顺序）/ Имя первым (западный порядок)
              "unknown": 无法判断 / Невозможно определить
            - 置信度 / Уверенность: 0.0-1.0
            - 判断依据 / Обоснование

    Examples:
        >>> identify_surname_position("Wei Li")
        ("family_first", 0.8, "Li是姓氏拼音；Wei符合中文名模式")

        >>> identify_surname_position("John Smith")
        ("given_first", 0.95, "Smith是欧美姓氏")
    """

    if not original_name:
        return ("unknown", 0.0, "姓名为空")

    # 解析姓名 / Парсинг имени
    parts = original_name.split()
    if len(parts) < 2:
        return ("unknown", 0.0, "姓名格式不完整")

    # 提取第一个和最后一个token / Извлечение первого и последнего токена
    first_token = parts[0].strip()
    last_token = parts[-1].strip()
    middle_tokens = ' '.join(parts[1:-1]) if len(parts) > 2 else ''

    confidence = 0.0
    evidence = []

    # ========== 证据1: 排除明显非中文姓氏 ==========
    # 检查last_token / Проверка last_token
    if is_non_chinese_surname(last_token.lower()):
        origin = get_surname_origin(last_token.lower())
        return ("given_first", 0.95, f"西方顺序：{last_token}是{origin}姓氏")

    # 检查first_token / Проверка first_token
    if is_non_chinese_surname(first_token.lower()):
        origin = get_surname_origin(first_token.lower())
        # 西方人名也可能姓在前（极少数情况）
        return ("given_first", 0.90, f"可能西方顺序：{first_token}是{origin}姓氏（罕见）")

    # ========== 证据2: 姓氏拼音匹配 ==========
    # 检查last_token是否为中文姓氏 / Проверка, является ли last_token китайской фамилией
    last_is_surname = False
    last_all_forms = get_all_possible_pinyins(last_token.lower())
    for form in last_all_forms:
        if is_surname_pinyin(form):
            surnames = get_surname_from_pinyin(form)
            confidence += 0.6
            evidence.append(f"{last_token}是姓氏拼音→{surnames}")
            last_is_surname = True
            break

    # 检查first_token是否为中文姓氏 / Проверка, является ли first_token китайской фамилией
    first_is_surname = False
    first_all_forms = get_all_possible_pinyins(first_token.lower())
    for form in first_all_forms:
        if is_surname_pinyin(form):
            surnames = get_surname_from_pinyin(form)
            confidence += 0.3  # 权重较低，因为可能是名字部分
            evidence.append(f"{first_token}也匹配姓氏→{surnames}")
            first_is_surname = True
            break

    # ========== 证据3: 姓氏频率先验（处理双姓氏歧义）==========
    # 检查是否存在双姓氏歧义 / Проверка двусмысленности двух фамилий
    # Check if both tokens are valid surnames (ambiguous case)
    if first_is_surname and last_is_surname:
        # 两个token都是姓氏，使用频率比较消歧
        # Both tokens are surnames, use frequency comparison to disambiguate
        freq_comparison = compare_surname_frequency(first_token.lower(), last_token.lower())

        if freq_comparison['confidence'] > 0.7:
            # 高置信度，可以使用频率判断 / Высокая уверенность
            if freq_comparison['more_common'] == last_token.lower():
                # last_token更常见作为姓氏，增加family_first的置信度
                # last_token is more common as surname, increase family_first confidence
                confidence += 0.4
                evidence.append(f"{last_token}更常见姓氏(rank {freq_comparison['rank2']} vs {first_token} rank {freq_comparison['rank1']})")
            elif freq_comparison['more_common'] == first_token.lower():
                # first_token更常见，但位置异常（罕见情况）
                # first_token more common, but unusual position
                confidence += 0.2
                evidence.append(f"{first_token}更常见但位置异常(rank {freq_comparison['rank1']} vs {last_token} rank {freq_comparison['rank2']})")
        else:
            # 低置信度，频率相近，无法通过频率判断
            # Low confidence, similar frequency, cannot disambiguate by frequency alone
            evidence.append(f"双姓氏歧义：{first_token}和{last_token}频率相近(diff={freq_comparison['rank_diff']})")

    # ========== 证据4: 名字模式分析 ==========
    # 分析中间部分和first/last token的名字特征
    # Анализ характеристик имени в средней части и first/last токенах

    if len(parts) == 2:
        # 两部分姓名 / Имя из двух частей
        first_is_chinese_name = is_chinese_given_name_pattern(first_token)
        last_is_chinese_name = is_chinese_given_name_pattern(last_token)

        if first_is_chinese_name and not last_is_chinese_name:
            confidence += 0.4
            evidence.append(f"{first_token}符合中文名模式")
        elif last_is_chinese_name and not first_is_chinese_name:
            confidence += 0.4
            evidence.append(f"{last_token}符合中文名模式")

    # ========== 证据5: 中国机构信息 ==========
    if affiliation:
        chinese_keywords = ['china', 'chinese', 'beijing', 'shanghai', 'guangzhou',
                           'tsinghua', 'peking university', 'fudan']
        if any(kw in affiliation.lower() for kw in chinese_keywords):
            confidence += 0.3
            evidence.append("中国机构")

    # ========== 最终判断 ==========
    # 情况1：last_token是姓氏 + 证据支持 → family_first
    if last_is_surname and confidence >= 0.6:
        return ("family_first", confidence, f"姓在前: {'; '.join(evidence)}")

    # 情况2：first_token是姓氏 + last_token不是姓氏 → given_first（罕见）
    if first_is_surname and not last_is_surname:
        return ("given_first", confidence * 0.7, f"名在前（罕见）: {'; '.join(evidence)}")

    # 情况3：都不是姓氏或证据不足
    if evidence:
        return ("unknown", confidence, f"证据不足: {'; '.join(evidence)}")
    else:
        return ("unknown", 0.0, "无有效证据")


def batch_identify_surnames(authors: list) -> list:
    """
    批量识别姓氏位置 / Пакетное определение позиции фамилии
    Batch identify surname positions

    Args:
        authors: 作者列表 / Список авторов

    Returns:
        list: 包含识别结果的字典列表 / Список словарей с результатами
    """
    results = []
    for author in authors:
        position, confidence, reason = identify_surname_position(
            original_name=author.get('original_name', ''),
            lastname=author.get('lastname', ''),
            firstname=author.get('firstname', ''),
            affiliation=author.get('affiliation', '')
        )

        results.append({
            'author': author,
            'surname_position': position,
            'confidence': confidence,
            'reason': reason
        })

    return results


if __name__ == '__main__':
    print("=" * 80)
    print("姓氏-名字识别算法 v3.0 测试")
    print("Surname-Given Name Identifier v3.0 Test")
    print("=" * 80)

    test_cases = [
        # 中文作者 - 姓在后 / Китайские авторы - фамилия последней
        {
            'original_name': 'Wei Li',
            'affiliation': 'Tsinghua University, Beijing, China',
            'expected': 'family_first'
        },
        {
            'original_name': 'Mingyuan Han',
            'affiliation': 'Beijing Key Laboratory',
            'expected': 'family_first'
        },
        {
            'original_name': 'Shi-Qing Wong',
            'affiliation': 'Shenzhen University',
            'expected': 'family_first'
        },

        # 韩国作者 - 姓在后 / Корейские авторы - фамилия последней
        {
            'original_name': 'Ran Han',
            'affiliation': None,
            'expected': 'family_first'  # 尽管是韩国名，姓氏顺序相同
        },

        # 西方作者 - 名在前 / Западные авторы - имя первым
        {
            'original_name': 'John Smith',
            'affiliation': 'Harvard University, USA',
            'expected': 'given_first'
        },
        {
            'original_name': 'Kei Murata',
            'affiliation': 'University of Tokyo',
            'expected': 'given_first'  # 日本姓氏，但可能按西方顺序
        },

        # 边缘案例 / Граничные случаи
        {
            'original_name': 'Unknown Xyz',
            'affiliation': None,
            'expected': 'unknown'
        },
    ]

    print("\n测试结果 / Результаты тестирования:")
    print("-" * 80)

    for i, case in enumerate(test_cases, 1):
        position, confidence, reason = identify_surname_position(
            original_name=case['original_name'],
            affiliation=case['affiliation']
        )

        expected = case['expected']
        status = 'PASS' if position == expected else 'FAIL'

        print(f"\n{i}. [{status}] {case['original_name']}")
        print(f"   结果: {position} (期望: {expected})")
        print(f"   置信度: {confidence:.2f}")
        print(f"   原因: {reason}")
