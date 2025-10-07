# -*- coding: utf-8 -*-
"""
ChineseNameProcessor - Модуль обработки китайских имён / 中文姓名处理模块

Автор / 作者: Ма Цзясин (Ma Jiaxin)
Проект / 项目: ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных
             智能科学计量数据专题研究系统
"""

from .chinese_name_processor import ChineseNameProcessor, create_default_processor
from .name_order_detector import NameOrderDetector, NameOrder

__version__ = "2.0.0"
__author__ = "Ma Jiaxin"

__all__ = [
    'ChineseNameProcessor',
    'create_default_processor',
    'NameOrderDetector',
    'NameOrder',
]
