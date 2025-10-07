# -*- coding: utf-8 -*-
"""
姓名数据库模块 / Модуль баз данных имен

包含：
- 中文姓氏库（所有常见姓氏）
- 中文字符库（41923个汉字，基于pypinyin）
- 拼音转写（中文→英文）
- 帕拉迪转写（中文→俄语）
"""

# 姓氏库
from .chinese_surnames import (
    SINGLE_SURNAMES,
    COMPOUND_SURNAMES,
    ALL_SURNAMES,
    is_surname,
    get_surname_from_text,
)

# 完整汉字库
from .chinese_chars import (
    ALL_CHINESE_CHARS,
    is_chinese_char,
    CHAR_COUNT,
)

# 拼音转写
from .pinyin_mapping import (
    to_pinyin,
    to_pinyin_string,
    PYPINYIN_AVAILABLE,
)

# 俄语帕拉迪转写
from .palladius_mapping import (
    to_russian,
    to_russian_spaced,
)

__all__ = [
    # 姓氏
    'SINGLE_SURNAMES',
    'COMPOUND_SURNAMES',
    'ALL_SURNAMES',
    'is_surname',
    'get_surname_from_text',

    # 汉字
    'ALL_CHINESE_CHARS',
    'is_chinese_char',
    'CHAR_COUNT',

    # 转写
    'to_pinyin',
    'to_pinyin_string',
    'to_russian',
    'to_russian_spaced',
    'PYPINYIN_AVAILABLE',
]
