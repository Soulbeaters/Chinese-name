# -*- coding: utf-8 -*-
"""
完整拼音转写库 / Полная база транслитерации пиньинь
基于pypinyin，支持41923个汉字 / На основе pypinyin, поддержка 41923 иероглифов
"""

try:
    from pypinyin import lazy_pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False
    print("Warning: pypinyin未安装。安装: pip install pypinyin")


def to_pinyin(text: str, uppercase: bool = True) -> list:
    """
    中文→拼音 / Китайский→пиньинь

    Examples:
        >>> to_pinyin('马嘉星')
        ['MA', 'JIA', 'XING']
    """
    if not PYPINYIN_AVAILABLE:
        return list(text)

    result = lazy_pinyin(text, style=Style.NORMAL)
    return [p.upper() for p in result] if uppercase else result


def to_pinyin_string(text: str, separator: str = ' ') -> str:
    """
    中文→拼音字符串 / Китайский→строка пиньинь

    Examples:
        >>> to_pinyin_string('马嘉星')
        'MA JIA XING'
    """
    return separator.join(to_pinyin(text))


if __name__ == '__main__':
    if PYPINYIN_AVAILABLE:
        tests = ['马嘉星', '李明', '王芳', '欧阳锋']
        for name in tests:
            print(f"{name} → {to_pinyin_string(name)}")
    else:
        print("请安装: pip install pypinyin")
