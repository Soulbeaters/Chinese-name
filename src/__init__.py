# -*- coding: utf-8 -*-
"""
ChineseNameProcessor - Модуль обработки китайских имён / 中文姓名处理模块

Автор / 作者: Ма Цзясин (Ma Jiaxin)
Проект / 项目: ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных
             智能科学计量数据专题研究系统

Версия / 版本: 2.0.0
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
    Создать процессор китайских имён по умолчанию / 创建默认的中文姓名处理器

    Returns:
        ChineseNameProcessor: Настроенный экземпляр процессора / 配置好的处理器实例
    """
    from .chinese_name_processor import create_default_processor
    return create_default_processor()