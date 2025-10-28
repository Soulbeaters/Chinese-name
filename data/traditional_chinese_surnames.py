# -*- coding: utf-8 -*-
"""
繁体中文姓氏拼音数据库（台湾、香港、新加坡）
Traditional Chinese Surname Database (Taiwan, Hong Kong, Singapore)

包含威妥玛拼音、粤语拼音、闽南语拼音等
Includes Wade-Giles, Cantonese, Hokkien romanizations

中文注释：收录台湾香港新加坡等地的中文姓氏拼写
Русский комментарий: База данных китайских фамилий для Тайваня, Гонконга, Сингапура
"""

# 威妥玛拼音（Wade-Giles）- 台湾常用
# Wade-Giles romanization - commonly used in Taiwan
WADE_GILES_SURNAMES = {
    # 格式: wade-giles拼写 -> (汉字, 汉语拼音)

    # 常见姓氏 / Common surnames
    'lee': ('李', 'li'),
    'chang': ('张', 'zhang'),
    'wang': ('王', 'wang'),
    'chen': ('陈', 'chen'),
    'lin': ('林', 'lin'),
    'huang': ('黄', 'huang'),
    'wu': ('吴', 'wu'),
    'cheng': ('郑', 'zheng'),
    'liu': ('刘', 'liu'),
    'yang': ('杨', 'yang'),

    # 特殊拼写 / Special spellings
    'hsu': ('徐', 'xu'),
    'hsieh': ('谢', 'xie'),
    'chu': ('朱', 'zhu'),
    'chao': ('赵', 'zhao'),
    'sun': ('孙', 'sun'),
    'ma': ('马', 'ma'),
    'kao': ('高', 'gao'),
    'chou': ('周', 'zhou'),
    'chiang': ('蒋', 'jiang'),
    'shen': ('沈', 'shen'),

    # 复杂拼写 / Complex spellings
    'tsai': ('蔡', 'cai'),
    'tseng': ('曾', 'zeng'),
    'han': ('韩', 'han'),
    'tang': ('唐', 'tang'),
    'feng': ('冯', 'feng'),
    'yu': ('于', 'yu'),
    'tung': ('董', 'dong'),
    'hsiao': ('萧', 'xiao'),
    'chung': ('钟', 'zhong'),
    'pan': ('潘', 'pan'),

    # 不常见但存在 / Less common but valid
    'liang': ('梁', 'liang'),
    'tien': ('田', 'tian'),
    'fan': ('范', 'fan'),
    'yen': ('严', 'yan'),
    'lu': ('陆', 'lu'),
    'shih': ('施', 'shi'),
    'mao': ('毛', 'mao'),
    'hao': ('郝', 'hao'),
    'tai': ('戴', 'dai'),
    'wan': ('万', 'wan'),
}

# 粤语拼音（Cantonese romanization）- 香港、广东
# Cantonese romanization - Hong Kong, Guangdong
CANTONESE_SURNAMES = {
    # 格式: 粤语拼写 -> (汉字, 汉语拼音)

    # 常见姓氏 / Common surnames
    'lee': ('李', 'li'),        # 粤语Lee
    'wong': ('王/黄', 'wang/huang'),
    'chan': ('陈', 'chen'),
    'lam': ('林', 'lin'),
    'ng': ('吴', 'wu'),
    'cheng': ('郑', 'zheng'),
    'cheung': ('张', 'zhang'),
    'leung': ('梁', 'liang'),
    'choi': ('蔡', 'cai'),      # 注意：与韩文Choi重复，需要上下文判断

    # 特殊拼写 / Special spellings
    'tsang': ('曾', 'zeng'),
    'yip': ('叶', 'ye'),
    'lau': ('刘', 'liu'),
    'mak': ('麦', 'mai'),
    'tse': ('谢', 'xie'),
    'yeung': ('杨', 'yang'),
    'tam': ('谭', 'tan'),
    'poon': ('潘', 'pan'),
    'fong': ('方', 'fang'),
    'ho': ('何', 'he'),

    # 单字姓 / Single-character surnames
    'au': ('区', 'ou'),
    'ko': ('高', 'gao'),
    'lok': ('骆', 'luo'),
    'siu': ('萧', 'xiao'),
    'tong': ('唐', 'tang'),
    'wan': ('温', 'wen'),
}

# 闽南语拼音（Hokkien romanization）- 福建、台湾南部、新加坡
# Hokkien romanization - Fujian, Southern Taiwan, Singapore
HOKKIEN_SURNAMES = {
    # 格式: 闽南语拼写 -> (汉字, 汉语拼音)

    # 常见姓氏 / Common surnames
    'lim': ('林', 'lin'),
    'tan': ('陈', 'chen'),
    'ong': ('王', 'wang'),
    'teo': ('张', 'zhang'),
    'goh': ('吴', 'wu'),
    'ng': ('黄', 'huang'),
    'koh': ('许', 'xu'),
    'tay': ('郑', 'zheng'),

    # 新加坡常见 / Common in Singapore
    'ang': ('洪', 'hong'),
    'foo': ('傅', 'fu'),
    'kwa': ('柯', 'ke'),
    'sim': ('沈', 'shen'),
    'toh': ('卓', 'zhuo'),
}

# 其他变体 / Other variants
OTHER_VARIANTS = {
    # 台湾其他拼法 / Other Taiwan spellings
    'liou': ('刘', 'liu'),
    'liew': ('刘', 'liu'),
    'shieh': ('谢', 'xie'),
    'hwang': ('黄', 'huang'),
    'soong': ('宋', 'song'),

    # 海外华人常见拼法 / Overseas Chinese spellings
    'lai': ('赖', 'lai'),
    'tong': ('唐', 'tang'),
    'yee': ('余', 'yu'),
    'yuen': ('袁', 'yuan'),
}

# 合并所有繁体中文姓氏拼写
# Combine all traditional Chinese surname spellings
ALL_TRADITIONAL_SURNAMES = {}
ALL_TRADITIONAL_SURNAMES.update(WADE_GILES_SURNAMES)
ALL_TRADITIONAL_SURNAMES.update(CANTONESE_SURNAMES)
ALL_TRADITIONAL_SURNAMES.update(HOKKIEN_SURNAMES)
ALL_TRADITIONAL_SURNAMES.update(OTHER_VARIANTS)


def is_traditional_chinese_surname(surname: str) -> bool:
    """
    判断是否为繁体中文地区的姓氏拼写
    Check if it's a traditional Chinese surname spelling

    包括：台湾（威妥玛）、香港（粤语）、新加坡（闽南语）
    Includes: Taiwan (Wade-Giles), Hong Kong (Cantonese), Singapore (Hokkien)

    Args:
        surname: 姓氏拼写

    Returns:
        bool: True表示是繁体中文姓氏拼写

    Examples:
        >>> is_traditional_chinese_surname('lee')
        True  # 李 (粤语/威妥玛)
        >>> is_traditional_chinese_surname('wong')
        True  # 王/黄 (粤语)
        >>> is_traditional_chinese_surname('hsu')
        True  # 徐 (威妥玛)
    """
    return surname.lower().strip() in ALL_TRADITIONAL_SURNAMES


def get_hanzi_and_pinyin(surname: str) -> tuple:
    """
    获取繁体拼写对应的汉字和汉语拼音
    Get Hanzi and Pinyin for traditional spelling

    Args:
        surname: 姓氏拼写

    Returns:
        tuple: (汉字, 汉语拼音) 或 (None, None)

    Examples:
        >>> get_hanzi_and_pinyin('lee')
        ('李', 'li')
        >>> get_hanzi_and_pinyin('hsu')
        ('徐', 'xu')
    """
    surname_lower = surname.lower().strip()
    if surname_lower in ALL_TRADITIONAL_SURNAMES:
        return ALL_TRADITIONAL_SURNAMES[surname_lower]
    return (None, None)


# 需要特别处理的歧义姓氏
# Ambiguous surnames that need special handling
AMBIGUOUS_SURNAMES = {
    # 中韩共享 / Shared Chinese-Korean
    'choi': {'chinese': ('蔡', 'cai'), 'korean': ('崔', 'choi')},
    'han': {'chinese': ('韩', 'han'), 'korean': ('韩', 'han')},

    # 中日共享 / Shared Chinese-Japanese
    'ko': {'chinese': ('高', 'gao'), 'japanese': ('小', 'ko')},
    'tan': {'chinese': ('陈', 'chen'), 'japanese': ('谷', 'tani')},
}


def is_ambiguous_surname(surname: str) -> bool:
    """
    判断是否为中韩日共享的歧义姓氏
    Check if it's an ambiguous Chinese-Korean-Japanese surname

    Args:
        surname: 姓氏拼写

    Returns:
        bool: True表示是歧义姓氏，需要根据名字进一步判断
    """
    return surname.lower().strip() in AMBIGUOUS_SURNAMES


if __name__ == '__main__':
    print("=" * 80)
    print("繁体中文姓氏数据库测试")
    print("Traditional Chinese Surname Database Test")
    print("=" * 80)

    print(f"\n总计姓氏拼写: {len(ALL_TRADITIONAL_SURNAMES)}")
    print(f"  威妥玛拼音: {len(WADE_GILES_SURNAMES)}")
    print(f"  粤语拼音: {len(CANTONESE_SURNAMES)}")
    print(f"  闽南语拼音: {len(HOKKIEN_SURNAMES)}")
    print(f"  其他变体: {len(OTHER_VARIANTS)}")

    print("\n测试案例:")
    print("-" * 80)

    test_cases = [
        'lee',      # 李 (粤语/威妥玛)
        'wong',     # 王/黄 (粤语)
        'hsu',      # 徐 (威妥玛)
        'chan',     # 陈 (粤语)
        'lim',      # 林 (闽南语)
        'smith',    # 非中文
    ]

    for surname in test_cases:
        is_trad = is_traditional_chinese_surname(surname)
        hanzi, pinyin = get_hanzi_and_pinyin(surname)
        print(f"{surname:10} -> 是繁体中文姓: {is_trad:5}  汉字: {hanzi or 'N/A':5}  拼音: {pinyin or 'N/A'}")

    print("\n歧义姓氏:")
    print("-" * 80)
    for surname in AMBIGUOUS_SURNAMES:
        print(f"{surname:10} -> {AMBIGUOUS_SURNAMES[surname]}")
