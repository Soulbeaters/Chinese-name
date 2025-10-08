# -*- coding: utf-8 -*-
"""
生成完整的姓氏映射数据库 / Генерация полных баз данных фамилий
基于pypinyin自动生成拼音和帕拉迪转写 / Автоматическая генерация на основе pypinyin
"""
from pypinyin import lazy_pinyin, Style
from chinese_surnames import SINGLE_SURNAMES, COMPOUND_SURNAMES, ALL_SURNAMES
from palladius_mapping import PINYIN_TO_RUSSIAN


def generate_pinyin_surname_mapping():
    """
    生成拼音→中文姓氏映射 / Генерация пиньинь→китайские фамилии
    """
    pinyin_to_surname = {}

    # 单字姓氏 / Односложные фамилии
    for surname in sorted(SINGLE_SURNAMES):
        pinyin = lazy_pinyin(surname, style=Style.NORMAL)[0]
        if pinyin not in pinyin_to_surname:
            pinyin_to_surname[pinyin] = []
        pinyin_to_surname[pinyin].append(surname)

    # 复合姓氏 / Составные фамилии
    for surname in sorted(COMPOUND_SURNAMES):
        pinyin_parts = lazy_pinyin(surname, style=Style.NORMAL)
        pinyin = ''.join(pinyin_parts)  # 连写
        if pinyin not in pinyin_to_surname:
            pinyin_to_surname[pinyin] = []
        pinyin_to_surname[pinyin].append(surname)

        # 也添加分写形式 / Также добавить раздельную форму
        pinyin_spaced = ' '.join(pinyin_parts)
        if pinyin_spaced not in pinyin_to_surname:
            pinyin_to_surname[pinyin_spaced] = []
        pinyin_to_surname[pinyin_spaced].append(surname)

    return pinyin_to_surname


def generate_russian_surname_mapping():
    """
    生成俄语帕拉迪→中文姓氏映射 / Генерация Палладий→китайские фамилии
    """
    russian_to_surname = {}

    # 单字姓氏 / Односложные фамилии
    for surname in sorted(SINGLE_SURNAMES):
        pinyin = lazy_pinyin(surname, style=Style.NORMAL)[0]
        russian = PINYIN_TO_RUSSIAN.get(pinyin.lower(), pinyin)

        # 添加小写形式 / Добавить строчную форму
        if russian.lower() not in russian_to_surname:
            russian_to_surname[russian.lower()] = []
        russian_to_surname[russian.lower()].append(surname)

        # 添加首字母大写形式 / Добавить форму с заглавной буквы
        capitalized = russian.capitalize()
        if capitalized not in russian_to_surname:
            russian_to_surname[capitalized] = []
        russian_to_surname[capitalized].append(surname)

    # 复合姓氏 / Составные фамилии
    for surname in sorted(COMPOUND_SURNAMES):
        pinyin_parts = lazy_pinyin(surname, style=Style.NORMAL)
        russian_parts = [PINYIN_TO_RUSSIAN.get(p.lower(), p) for p in pinyin_parts]

        # 连写形式 / Слитная форма
        russian = ''.join(russian_parts)
        if russian.lower() not in russian_to_surname:
            russian_to_surname[russian.lower()] = []
        russian_to_surname[russian.lower()].append(surname)

        # 首字母大写 / Заглавная буква
        capitalized = russian.capitalize()
        if capitalized not in russian_to_surname:
            russian_to_surname[capitalized] = []
        russian_to_surname[capitalized].append(surname)

        # 分写形式 / Раздельная форма
        russian_spaced = ' '.join([p.capitalize() for p in russian_parts])
        if russian_spaced not in russian_to_surname:
            russian_to_surname[russian_spaced] = []
        russian_to_surname[russian_spaced].append(surname)

    return russian_to_surname


def generate_surname_pinyin_list():
    """
    生成所有姓氏的拼音列表（用于快速查找）/ Генерация списка пиньинь всех фамилий
    """
    surname_pinyin_set = set()

    for surname in ALL_SURNAMES:
        pinyin_parts = lazy_pinyin(surname, style=Style.NORMAL)
        # 小写 / Строчные
        surname_pinyin_set.add(''.join(pinyin_parts).lower())
        surname_pinyin_set.add(' '.join(pinyin_parts).lower())
        # 大写 / Заглавные
        surname_pinyin_set.add(''.join(pinyin_parts).upper())
        surname_pinyin_set.add(' '.join(pinyin_parts).upper())
        # 首字母大写 / Первая заглавная
        surname_pinyin_set.add(''.join(pinyin_parts).capitalize())
        surname_pinyin_set.add(' '.join([p.capitalize() for p in pinyin_parts]))

    return sorted(surname_pinyin_set)


if __name__ == '__main__':
    print("="*70)
    print("生成姓氏映射数据库 / Генерация баз данных фамилий")
    print("="*70)

    # 生成拼音映射 / Генерация пиньинь
    pinyin_map = generate_pinyin_surname_mapping()
    print(f"\n拼音映射数量: {len(pinyin_map)}")
    print("示例:")
    for pinyin in list(pinyin_map.keys())[:10]:
        print(f"  {pinyin}: {pinyin_map[pinyin]}")

    # 生成俄语映射 / Генерация русского
    russian_map = generate_russian_surname_mapping()
    print(f"\n俄语映射数量: {len(russian_map)}")
    print("示例:")
    for russian in list(russian_map.keys())[:10]:
        print(f"  {russian}: {russian_map[russian]}")

    # 生成拼音列表 / Генерация списка пиньинь
    pinyin_list = generate_surname_pinyin_list()
    print(f"\n姓氏拼音总数: {len(pinyin_list)}")
    print("示例:", pinyin_list[:20])

    print("\n" + "="*70)
    print("数据库生成完成！/ Генерация завершена!")
    print("="*70)
