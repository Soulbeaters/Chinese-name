# -*- coding: utf-8 -*-
"""
异体拼音映射表 / Таблица вариантов пиньинь
Mapping of variant romanization systems to standard Pinyin
用于处理粤语拼音、威妥玛拼音等非标准拼音形式

中文注释: 将粤语拼音、威妥玛拼音等异体拼音映射到标准汉语拼音
Русский комментарий: Сопоставление вариантов романизации (кантонская, Уэйда-Джайлза) со стандартным пиньинь
"""

# 粤语拼音 → 普通话拼音映射 / Кантонская романизация → Пиньинь
# Cantonese romanization → Mandarin Pinyin mapping
CANTONESE_TO_PINYIN = {
    # 高频姓氏 / Высокочастотные фамилии
    'chan': ['chen'],           # 陈 (152次) - 最常见粤语姓氏
    'wong': ['wang', 'huang'],  # 王/黄 (121次) - 多对应
    'ho': ['he'],               # 何 (104次)
    'chow': ['zhou'],           # 周
    'cheung': ['zhang'],        # 张 (46次)
    'chung': ['zhong'],         # 钟 (46次)
    'leung': ['liang'],         # 梁 (26次)
    'lau': ['liu'],             # 刘 (28次)

    # 其他常见粤语拼音 / Другие распространенные варианты
    'ng': ['wu', 'ng'],         # 吴/伍/吴
    'yip': ['ye'],              # 叶
    'mak': ['mo'],              # 莫
    'szeto': ['situ'],          # 司徒 (复姓)
    'yeung': ['yang'],          # 杨
    'tam': ['tan'],             # 谭
    'cheng': ['zheng'],         # 郑
    'tse': ['xie'],             # 谢
    'siu': ['xiao'],            # 萧
    'ko': ['ge'],               # 葛/戈
    'kwan': ['guan'],           # 关
}

# 威妥玛拼音 → 汉语拼音映射 / Система Уэйда-Джайлза → Пиньинь
# Wade-Giles romanization → Pinyin mapping
WADE_GILES_TO_PINYIN = {
    # 高频姓氏 / Высокочастотные фамилии
    'hsu': ['xu'],              # 许/徐 (120次) - 非常常见
    'tsai': ['cai'],            # 蔡 (75次)

    # 其他威妥玛拼音变体 / Другие варианты Уэйда-Джайлза
    'teng': ['deng'],           # 邓
    'chu': ['zhu'],             # 朱
    'ch\'en': ['chen'],         # 陈
    'chang': ['zhang'],         # 张
    'chao': ['zhao'],           # 赵
    'chou': ['zhou'],           # 周
    'ch\'ien': ['qian'],        # 钱
    'ch\'in': ['qin'],          # 秦
    'ch\'eng': ['cheng'],       # 程
    'ch\'ang': ['chang'],       # 常
    'ts\'ao': ['cao'],          # 曹
    'ts\'ui': ['cui'],          # 崔
    'tung': ['dong'],           # 董
    'tang': ['dang'],           # 党
}

# 其他拼音系统 / Другие системы романизации
# Other romanization systems
OTHER_VARIANTS = {
    # 旧式邮政式拼音 / Старая почтовая романизация
    'soong': ['song'],          # 宋
    'kung': ['kong'],           # 孔 (20次)
    'tung': ['dong'],           # 董

    # 简化或变体拼写 / Упрощенные или вариантные написания
    'kuo': ['guo'],             # 郭 (60次)
    'lo': ['luo'],              # 罗 (60次)
    'chiu': ['qiu'],            # 邱/丘 (29次)
    'lyu': ['lv'],              # 吕 (126次) - 官方标准拼写，避免与lv混淆
}

# 合并所有映射 / Объединение всех сопоставлений
# Combine all mappings
ALL_VARIANT_MAPPINGS = {}
ALL_VARIANT_MAPPINGS.update(CANTONESE_TO_PINYIN)
ALL_VARIANT_MAPPINGS.update(WADE_GILES_TO_PINYIN)
ALL_VARIANT_MAPPINGS.update(OTHER_VARIANTS)


def normalize_pinyin(pinyin: str) -> list:
    """
    将异体拼音标准化为普通话拼音 / Нормализация вариантов пиньинь в стандартный пиньинь
    Normalize variant pinyin to standard Mandarin pinyin

    中文: 输入异体拼音,返回可能的标准拼音列表
    Русский: Принимает вариант пиньинь, возвращает список возможных стандартных форм

    Args:
        pinyin (str): 输入的拼音 (可能是粤语、威妥玛等)
                      Входной пиньинь (может быть кантонский, Уэйда-Джайлза и т.д.)

    Returns:
        list: 标准拼音列表 / Список стандартных форм пиньинь
              如果找不到映射,返回包含原输入的列表
              Если сопоставление не найдено, возвращает список с исходным вводом

    Examples:
        >>> normalize_pinyin('chan')
        ['chen']
        >>> normalize_pinyin('wong')
        ['wang', 'huang']
        >>> normalize_pinyin('hsu')
        ['xu']
        >>> normalize_pinyin('zhang')  # 已经是标准拼音
        ['zhang']
    """
    pinyin_lower = pinyin.lower().strip()

    # 检查是否在映射表中 / Проверка наличия в таблице сопоставлений
    if pinyin_lower in ALL_VARIANT_MAPPINGS:
        return ALL_VARIANT_MAPPINGS[pinyin_lower]

    # 不在映射表中,返回原值 / Если нет в таблице, возвращаем исходное значение
    return [pinyin_lower]


def is_variant_pinyin(pinyin: str) -> bool:
    """
    判断是否为异体拼音 / Проверка, является ли пиньинь вариантной формой
    Check if the pinyin is a variant form

    Args:
        pinyin (str): 待检查的拼音 / Пиньинь для проверки

    Returns:
        bool: 是否为异体拼音 / Является ли вариантной формой

    Examples:
        >>> is_variant_pinyin('chan')
        True
        >>> is_variant_pinyin('zhang')
        False
    """
    return pinyin.lower().strip() in ALL_VARIANT_MAPPINGS


def get_all_possible_pinyins(pinyin: str) -> list:
    """
    获取所有可能的拼音形式(包括原始输入和标准化后的)
    Получить все возможные формы пиньинь (включая исходную и нормализованную)
    Get all possible pinyin forms (including original and normalized)

    中文: 返回输入拼音本身+标准化后的拼音,用于全面匹配
    Русский: Возвращает сам входной пиньинь + нормализованные формы для полного сопоставления

    Args:
        pinyin (str): 输入拼音 / Входной пиньинь

    Returns:
        list: 所有可能的拼音形式列表 / Список всех возможных форм

    Examples:
        >>> get_all_possible_pinyins('chan')
        ['chan', 'chen']
        >>> get_all_possible_pinyins('wong')
        ['wong', 'wang', 'huang']
    """
    result = [pinyin.lower().strip()]
    normalized = normalize_pinyin(pinyin)

    for py in normalized:
        if py not in result:
            result.append(py)

    return result


if __name__ == '__main__':
    print("=" * 60)
    print("异体拼音映射表测试 / Тестирование таблицы вариантов пиньинь")
    print("=" * 60)

    # 测试用例 / Тестовые примеры
    test_cases = [
        ('chan', '陈'),
        ('wong', '王/黄'),
        ('ho', '何'),
        ('hsu', '许/徐'),
        ('tsai', '蔡'),
        ('cheung', '张'),
        ('kuo', '郭'),
        ('zhang', '张(标准拼音)'),
    ]

    print("\n1. 标准化测试 / Тест нормализации:")
    print("-" * 60)
    for variant, expected in test_cases:
        normalized = normalize_pinyin(variant)
        is_variant = is_variant_pinyin(variant)
        print(f"{variant:10} -> {str(normalized):30} (预期: {expected}) [变体: {is_variant}]")

    print("\n2. 全部可能拼音测试 / Тест всех возможных форм:")
    print("-" * 60)
    for variant, expected in test_cases[:5]:
        all_forms = get_all_possible_pinyins(variant)
        print(f"{variant:10} -> {all_forms}")

    print("\n3. 映射统计 / Статистика сопоставлений:")
    print("-" * 60)
    print(f"粤语拼音映射数 / Кантонских вариантов: {len(CANTONESE_TO_PINYIN)}")
    print(f"威妥玛拼音映射数 / Уэйда-Джайлза вариантов: {len(WADE_GILES_TO_PINYIN)}")
    print(f"其他映射数 / Других вариантов: {len(OTHER_VARIANTS)}")
    print(f"总计映射数 / Всего сопоставлений: {len(ALL_VARIANT_MAPPINGS)}")
