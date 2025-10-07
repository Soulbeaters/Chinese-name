# -*- coding: utf-8 -*-
"""
中文姓名处理器 - 极简版 / Процессор китайских имен - минимальная версия
基于ISTINA风格，只保留核心功能 / На основе стиля ИСТИНА, только основная функциональность
"""
import re

# 正则 / Регулярные выражения
SEP_RE = re.compile(r'[.,;\s+]')

# 中文姓氏库（高频Top50） / База китайских фамилий (топ-50)
SURNAMES = {
    '李': 95, '王': 92, '张': 90, '刘': 85, '陈': 80, '杨': 77, '黄': 74,
    '赵': 72, '吴': 70, '周': 69, '徐': 64, '孙': 63, '马': 62, '朱': 60,
    '胡': 59, '郭': 58, '何': 57, '高': 56, '林': 55, '罗': 52, '郑': 50,
    '梁': 48, '谢': 46, '宋': 45, '唐': 43, '许': 42, '韩': 40, '冯': 38,
    '邓': 36, '曹': 35, '彭': 33, '曾': 32, '萧': 30, '田': 28, '董': 27,
    # 复合姓 / Составные фамилии
    '欧阳': 15, '司马': 12, '诸葛': 11, '上官': 10,
}

# 音译映射（精简） / Транслитерация (упрощенная)
PINYIN = {
    'li': '李', 'wang': '王', 'zhang': '张', 'liu': '刘', 'chen': '陈',
    'yang': '杨', 'huang': '黄', 'zhao': '赵', 'wu': '吴', 'zhou': '周',
}


def is_chinese(char):
    """判断是否为中文字符 / Проверка китайского символа"""
    return '\u4e00' <= char <= '\u9fff'


def process_name(name):
    """
    处理姓名 / Обработка имени
    返回: (surname, firstname) / Возвращает: (фамилия, имя)
    """
    name = name.strip()
    if not name:
        return None, None

    # 纯中文姓名 / Чисто китайское имя
    if all(is_chinese(c) for c in name):
        # 尝试双字姓 / Попытка составной фамилии
        if len(name) >= 2 and name[:2] in SURNAMES:
            return name[:2], name[2:]
        # 单字姓 / Однословная фамилия
        if name[0] in SURNAMES:
            return name[0], name[1:]
        # 默认第一个字为姓 / По умолчанию первый символ
        return name[0], name[1:] if len(name) > 1 else ""

    # 拼音姓名 / Имя в пиньинь
    parts = [p for p in SEP_RE.split(name.lower()) if p]
    if not parts:
        return None, None

    # 查找姓氏 / Поиск фамилии
    surname = parts[0]
    if surname in PINYIN:
        return PINYIN[surname], " ".join(parts[1:])

    # 默认处理 / Обработка по умолчанию
    return parts[0].capitalize(), " ".join(parts[1:]).capitalize()


# 集成姓名顺序检测 / Интеграция определения порядка
from .name_order_detector import detect_order, parse_authors


class ChineseNameProcessor:
    """极简处理器 / Минимальный процессор"""

    def __init__(self):
        self.surnames = SURNAMES
        self.name_order_detector = self

    def process_name(self, name):
        """处理姓名，返回结构化结果"""
        surname, firstname = process_name(name)
        return type('Result', (), {
            'components': type('Components', (), {
                'surname': surname or "",
                'first_name': firstname or "",
                'confidence': 0.9 if surname in SURNAMES else 0.7,
            })(),
            'confidence_score': 0.9 if surname in SURNAMES else 0.7,
        })()

    def detect_name_order(self, name):
        """检测姓名顺序"""
        order = detect_order(name, self)
        parts = [x for x in SEP_RE.split(name.strip()) if x]
        return {
            'name_string': name,
            'name_parts': parts,
            'order_value': order,
            'detected_order': {1: 'SURNAME_FIRST', 0: 'UNDETERMINED', -1: 'GIVEN_NAME_FIRST'}[order],
            'confidence': 0.8,
            'is_first_name_map': [],
        }

    def parse_author_list(self, authors):
        """解析作者列表"""
        results = []
        for surname, first, middle, is_first in parse_authors(authors, self):
            results.append({
                'surname': surname,
                'given_name': first,
                'middle_name': middle,
                'is_first_author': is_first,
                'order': 'SURNAME_FIRST',
                'order_value': 1,
            })
        return results

    def batch_detect_name_orders(self, names):
        """批量检测"""
        return [self.detect_name_order(n) for n in names]

    def is_known_surname(self, surname):
        """检查姓氏"""
        return surname in SURNAMES or surname.upper() in {'ZHANG', 'LI', 'WANG', 'LIU'}


def create_default_processor():
    """工厂函数 / Фабричная функция"""
    return ChineseNameProcessor()


# 兼容旧API / Совместимость со старым API
class SurnameDatabase:
    """极简姓氏数据库 / Минимальная база фамилий"""

    def __init__(self):
        self.surnames = SURNAMES

    def is_known_surname(self, surname):
        """检查姓氏"""
        return surname in SURNAMES or surname.upper() in {'ZHANG', 'LI', 'WANG', 'LIU'}
