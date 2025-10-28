# -*- coding: utf-8 -*-
"""
完整的拼音姓氏数据库 / Полная база фамилий в пиньинь
自动生成，基于pypinyin和中文姓氏库 / Автоматически сгенерировано на основе pypinyin и базы китайских фамилий

包含:
- 拼音→中文姓氏映射
- 所有姓氏的拼音形式集合（用于快速识别）
"""

try:
    from pypinyin import lazy_pinyin, Style
    from .chinese_surnames import ALL_SURNAMES, SINGLE_SURNAMES, COMPOUND_SURNAMES
    PYPINYIN_AVAILABLE = True
except (ImportError, ValueError):
    try:
        from pypinyin import lazy_pinyin, Style
        from chinese_surnames import ALL_SURNAMES, SINGLE_SURNAMES, COMPOUND_SURNAMES
        PYPINYIN_AVAILABLE = True
    except ImportError:
        PYPINYIN_AVAILABLE = False
        ALL_SURNAMES = set()
        SINGLE_SURNAMES = set()
        COMPOUND_SURNAMES = set()


def _generate_pinyin_surname_set():
    """
    生成所有可能的姓氏拼音形式 / Генерация всех возможных форм фамилий в пиньинь
    用于快速判断一个拼音字符串是否为姓氏 / Для быстрой проверки, является ли пиньинь фамилией
    """
    if not PYPINYIN_AVAILABLE:
        return set()

    from pypinyin import pinyin

    # 多音字姓氏特殊处理 / Специальная обработка многозначных фамилий
    POLYPHONIC_SURNAMES = {
        '曾': ['ceng', 'zeng'],  # 曾作为姓氏读zeng
        '仇': ['chou', 'qiu'],   # 仇作为姓氏读qiu
        '区': ['qu', 'ou'],      # 区作为姓氏读ou
        '查': ['cha', 'zha'],    # 查作为姓氏读zha
        '员': ['yuan', 'yun'],   # 员作为姓氏读yun
        '盖': ['gai', 'ge'],     # 盖作为姓氏读ge或gai
        '种': ['zhong', 'chong'],# 种作为姓氏读chong
        '解': ['jie', 'xie'],    # 解作为姓氏读xie
        '单': ['dan', 'shan'],   # 单作为姓氏读shan
        '朴': ['pu', 'piao'],    # 朴作为姓氏读piao
        '繁': ['fan', 'po'],     # 繁作为姓氏读po
        '翟': ['di', 'zhai'],    # 翟作为姓氏读zhai
    }

    surname_pinyin_set = set()

    for surname in ALL_SURNAMES:
        # 检查是否是多音字 / Проверка многозначности
        if len(surname) == 1 and surname in POLYPHONIC_SURNAMES:
            # 添加所有可能的读音 / Добавить все возможные чтения
            for py in POLYPHONIC_SURNAMES[surname]:
                surname_pinyin_set.add(py.lower())
                surname_pinyin_set.add(py.upper())
                surname_pinyin_set.add(py.capitalize())
        else:
            # 常规处理 / Обычная обработка
            pinyin_parts = lazy_pinyin(surname, style=Style.NORMAL)

            # 连写形式 / Слитная форма
            joined = ''.join(pinyin_parts)
            surname_pinyin_set.add(joined.lower())
            surname_pinyin_set.add(joined.upper())
            surname_pinyin_set.add(joined.capitalize())

            # 分写形式 / Раздельная форма
            spaced = ' '.join(pinyin_parts)
            surname_pinyin_set.add(spaced.lower())
            surname_pinyin_set.add(spaced.upper())
            surname_pinyin_set.add(' '.join([p.capitalize() for p in pinyin_parts]))

            # 每个部分首字母大写 / Каждая часть с заглавной
            surname_pinyin_set.add(' '.join([p.upper() for p in pinyin_parts]))

    return surname_pinyin_set


def _generate_pinyin_to_surname_map():
    """
    生成拼音→姓氏映射表 / Генерация таблицы пиньинь→фамилия
    """
    if not PYPINYIN_AVAILABLE:
        return {}

    # 多音字姓氏特殊处理 (同_generate_pinyin_surname_set中的定义)
    POLYPHONIC_SURNAMES = {
        '曾': ['ceng', 'zeng'],
        '仇': ['chou', 'qiu'],
        '区': ['qu', 'ou'],
        '查': ['cha', 'zha'],
        '员': ['yuan', 'yun'],
        '盖': ['gai', 'ge'],
        '种': ['zhong', 'chong'],
        '解': ['jie', 'xie'],
        '单': ['dan', 'shan'],
        '朴': ['pu', 'piao'],
        '繁': ['fan', 'po'],
        '翟': ['di', 'zhai'],
    }

    pinyin_map = {}

    for surname in ALL_SURNAMES:
        # 检查是否是多音字
        if len(surname) == 1 and surname in POLYPHONIC_SURNAMES:
            # 添加所有可能的读音
            for py in POLYPHONIC_SURNAMES[surname]:
                if py not in pinyin_map:
                    pinyin_map[py] = []
                if surname not in pinyin_map[py]:
                    pinyin_map[py].append(surname)
        else:
            # 常规处理
            pinyin_parts = lazy_pinyin(surname, style=Style.NORMAL)

            # 小写连写 / Строчная слитная
            key = ''.join(pinyin_parts).lower()
            if key not in pinyin_map:
                pinyin_map[key] = []
            pinyin_map[key].append(surname)

            # 小写分写 / Строчная раздельная
            key = ' '.join(pinyin_parts).lower()
            if key not in pinyin_map:
                pinyin_map[key] = []
            pinyin_map[key].append(surname)

    return pinyin_map


# 全局数据库 / Глобальные базы данных
SURNAME_PINYIN_SET = _generate_pinyin_surname_set()
PINYIN_TO_SURNAME = _generate_pinyin_to_surname_map()


def is_surname_pinyin(text: str) -> bool:
    """
    判断拼音文本是否为姓氏 / Проверка, является ли пиньинь фамилией

    Examples:
        >>> is_surname_pinyin('ZHANG')
        True
        >>> is_surname_pinyin('zhang')
        True
        >>> is_surname_pinyin('OUYANG')
        True
        >>> is_surname_pinyin('hello')
        False
    """
    if not text:
        return False
    return text in SURNAME_PINYIN_SET or text.lower() in SURNAME_PINYIN_SET


def get_surname_from_pinyin(pinyin: str):
    """
    从拼音获取可能的中文姓氏 / Получение возможных китайских фамилий из пиньинь

    Examples:
        >>> get_surname_from_pinyin('wang')
        ['王', '汪']
    """
    if not pinyin:
        return []
    return PINYIN_TO_SURNAME.get(pinyin.lower(), [])


if __name__ == '__main__':
    print(f"姓氏拼音集合大小: {len(SURNAME_PINYIN_SET)}")
    print(f"拼音→姓氏映射数量: {len(PINYIN_TO_SURNAME)}")

    # 测试 / Тесты
    test_cases = ['ZHANG', 'zhang', 'Zhang', 'WANG', 'OUYANG', 'ouyang', 'LI', 'hello']
    print("\n测试姓氏识别:")
    for test in test_cases:
        is_surname = is_surname_pinyin(test)
        surnames = get_surname_from_pinyin(test)
        print(f"  {test:15} → 是姓氏: {is_surname:5}  对应汉字: {surnames}")
