# -*- coding: utf-8 -*-
"""
完整中文字符库 / Полная база китайских иероглифов
基于pypinyin的完整汉字集 / На основе полного набора pypinyin
包含41923个汉字 / Содержит 41923 иероглифа
"""

try:
    from pypinyin import pinyin_dict
    # 从pypinyin提取所有汉字
    ALL_CHINESE_CHARS = set(chr(code) for code in pinyin_dict.pinyin_dict.keys())
    CHAR_COUNT = len(ALL_CHINESE_CHARS)
except ImportError:
    # 如果pypinyin未安装，使用Unicode CJK基本集
    ALL_CHINESE_CHARS = set(chr(i) for i in range(0x4E00, 0x9FFF))
    CHAR_COUNT = len(ALL_CHINESE_CHARS)
    print(f"Warning: pypinyin未安装，使用Unicode CJK基本集 ({CHAR_COUNT}字)")


def is_chinese_char(char: str) -> bool:
    """判断是否为中文字符"""
    return char in ALL_CHINESE_CHARS


if __name__ == '__main__':
    print(f"汉字总数: {CHAR_COUNT}")
    print(f"示例字符: {''.join(list(ALL_CHINESE_CHARS)[:100])}")
