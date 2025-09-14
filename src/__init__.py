# -*- coding: utf-8 -*-
"""
ChineseNameProcessor - 中文姓名处理模块 / Chinese Name Processing Module

Автор / 作者: Ма Цзясин (Ma Jiaxin)
Проект / 项目: ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных

版本 / Version: 2.0.0
"""

from .chinese_name_processor import ChineseNameProcessor, SurnameDatabase, NameComponents, NameParsingResult
from .transliteration_db import ExtendedTransliterationDatabase, get_extended_transliteration_db
from .surname_trie import SurnameTrie, create_optimized_surname_trie

__version__ = "2.0.0"
__author__ = "Ma Jiaxin"
__email__ = "majiaxing@mail.ru"

__all__ = [
    'ChineseNameProcessor',
    'SurnameDatabase',
    'NameComponents',
    'NameParsingResult',
    'ExtendedTransliterationDatabase',
    'get_extended_transliteration_db',
    'SurnameTrie',
    'create_optimized_surname_trie'
]

def create_default_processor():
    """
    创建默认的中文姓名处理器 / Create default Chinese name processor

    Returns:
        ChineseNameProcessor: 配置好的处理器实例 / Configured processor instance
    """
    from .chinese_name_processor import create_default_processor
    return create_default_processor()