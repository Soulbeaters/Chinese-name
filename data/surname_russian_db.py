# -*- coding: utf-8 -*-
"""
完整的俄语帕拉迪姓氏数据库 / Полная база фамилий в транслитерации Палладия
自动生成，基于pypinyin、帕拉迪规则和中文姓氏库 / Автоматически сгенерировано

包含:
- 俄语→中文姓氏映射
- 所有姓氏的俄语帕拉迪转写形式集合
"""

try:
    from pypinyin import lazy_pinyin, Style
    from .chinese_surnames import ALL_SURNAMES, SINGLE_SURNAMES, COMPOUND_SURNAMES
    from .palladius_mapping import PINYIN_TO_RUSSIAN
    PYPINYIN_AVAILABLE = True
except (ImportError, ValueError):
    try:
        from pypinyin import lazy_pinyin, Style
        from chinese_surnames import ALL_SURNAMES, SINGLE_SURNAMES, COMPOUND_SURNAMES
        from palladius_mapping import PINYIN_TO_RUSSIAN
        PYPINYIN_AVAILABLE = True
    except ImportError:
        PYPINYIN_AVAILABLE = False
        ALL_SURNAMES = set()
        PINYIN_TO_RUSSIAN = {}


def _generate_russian_surname_set():
    """
    生成所有可能的姓氏俄语形式 / Генерация всех возможных форм фамилий на русском
    """
    if not PYPINYIN_AVAILABLE:
        return set()

    russian_surname_set = set()

    for surname in ALL_SURNAMES:
        pinyin_parts = lazy_pinyin(surname, style=Style.NORMAL)
        russian_parts = [PINYIN_TO_RUSSIAN.get(p.lower(), p) for p in pinyin_parts]

        # 连写形式 / Слитная форма
        joined = ''.join(russian_parts)
        russian_surname_set.add(joined.lower())
        russian_surname_set.add(joined.capitalize())
        russian_surname_set.add(joined.upper())

        # 分写形式 / Раздельная форма
        spaced = ' '.join(russian_parts)
        russian_surname_set.add(spaced.lower())
        russian_surname_set.add(' '.join([p.capitalize() for p in russian_parts]))
        russian_surname_set.add(spaced.upper())

    return russian_surname_set


def _generate_russian_to_surname_map():
    """
    生成俄语→姓氏映射表 / Генерация таблицы русский→фамилия
    """
    if not PYPINYIN_AVAILABLE:
        return {}

    russian_map = {}

    for surname in ALL_SURNAMES:
        pinyin_parts = lazy_pinyin(surname, style=Style.NORMAL)
        russian_parts = [PINYIN_TO_RUSSIAN.get(p.lower(), p) for p in pinyin_parts]

        # 小写连写 / Строчная слитная
        key = ''.join(russian_parts).lower()
        if key not in russian_map:
            russian_map[key] = []
        russian_map[key].append(surname)

        # 小写分写 / Строчная раздельная
        key = ' '.join(russian_parts).lower()
        if key not in russian_map:
            russian_map[key] = []
        russian_map[key].append(surname)

    return russian_map


# 全局数据库 / Глобальные базы данных
SURNAME_RUSSIAN_SET = _generate_russian_surname_set()
RUSSIAN_TO_SURNAME = _generate_russian_to_surname_map()


def is_surname_russian(text: str) -> bool:
    """
    判断俄语文本是否为姓氏 / Проверка, является ли русский текст фамилией

    Examples:
        >>> is_surname_russian('Чжан')
        True
        >>> is_surname_russian('чжан')
        True
        >>> is_surname_russian('Оуян')
        True
    """
    if not text:
        return False
    return text in SURNAME_RUSSIAN_SET or text.lower() in SURNAME_RUSSIAN_SET


def get_surname_from_russian(russian: str):
    """
    从俄语获取可能的中文姓氏 / Получение возможных китайских фамилий из русского

    Examples:
        >>> get_surname_from_russian('ван')
        ['王', '汪']
    """
    if not russian:
        return []
    return RUSSIAN_TO_SURNAME.get(russian.lower(), [])


def chinese_to_russian_surname(surname: str) -> str:
    """
    中文姓氏→俄语帕拉迪转写 / Китайская фамилия→русская транслитерация Палладия

    Examples:
        >>> chinese_to_russian_surname('张')
        'Чжан'
        >>> chinese_to_russian_surname('欧阳')
        'Оуян'
    """
    if not PYPINYIN_AVAILABLE or not surname:
        return surname

    pinyin_parts = lazy_pinyin(surname, style=Style.NORMAL)
    russian_parts = [PINYIN_TO_RUSSIAN.get(p.lower(), p) for p in pinyin_parts]

    # 首字母大写 / Заглавная буква
    result = ''.join(russian_parts)
    return result.capitalize()


if __name__ == '__main__':
    print(f"姓氏俄语集合大小: {len(SURNAME_RUSSIAN_SET)}")
    print(f"俄语→姓氏映射数量: {len(RUSSIAN_TO_SURNAME)}")

    # 测试 / Тесты
    test_cases_ru = ['Чжан', 'чжан', 'Ван', 'Ли', 'Оуян', 'оуян', 'привет']
    print("\n测试俄语姓氏识别:")
    for test in test_cases_ru:
        is_surname = is_surname_russian(test)
        surnames = get_surname_from_russian(test)
        print(f"  {test:15} → 是姓氏: {is_surname:5}  对应汉字: {surnames}")

    test_cases_cn = ['张', '王', '李', '欧阳', '司马', '诸葛']
    print("\n测试中文→俄语转写:")
    for cn in test_cases_cn:
        ru = chinese_to_russian_surname(cn)
        print(f"  {cn} → {ru}")
