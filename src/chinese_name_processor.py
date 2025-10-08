# -*- coding: utf-8 -*-
"""
中文姓名处理器 - 极简版 / Процессор китайских имен - минимальная версия
基于ISTINA风格，只保留核心功能 / На основе стиля ИСТИНА, только основная функциональность
"""
import re
import sys
from pathlib import Path

# 导入完整的姓氏数据库 / Импорт полных баз данных фамилий
try:
    # 尝试相对导入 / Попытка относительного импорта
    from ..data.chinese_surnames import SINGLE_SURNAMES, COMPOUND_SURNAMES, ALL_SURNAMES
    from ..data.surname_pinyin_db import is_surname_pinyin, SURNAME_PINYIN_SET
    from ..data.surname_russian_db import is_surname_russian, SURNAME_RUSSIAN_SET
except (ImportError, ValueError):
    try:
        # 尝试添加路径 / Попытка добавить путь
        data_path = Path(__file__).parent.parent / 'data'
        sys.path.insert(0, str(data_path))
        from chinese_surnames import SINGLE_SURNAMES, COMPOUND_SURNAMES, ALL_SURNAMES
        from surname_pinyin_db import is_surname_pinyin, SURNAME_PINYIN_SET
        from surname_russian_db import is_surname_russian, SURNAME_RUSSIAN_SET
    except ImportError:
        # 备用：使用基础数据 / Резервный вариант
        SINGLE_SURNAMES = {'李', '王', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周'}
        COMPOUND_SURNAMES = {'欧阳', '司马', '诸葛', '上官'}
        ALL_SURNAMES = SINGLE_SURNAMES | COMPOUND_SURNAMES
        SURNAME_PINYIN_SET = set()
        SURNAME_RUSSIAN_SET = set()

        def is_surname_pinyin(text):
            basic_surnames = {'li', 'wang', 'zhang', 'liu', 'chen', 'yang', 'huang', 'zhao'}
            return text.lower() in basic_surnames

        def is_surname_russian(text):
            return False

# 正则 / Регулярные выражения
SEP_RE = re.compile(r'[.,;\s+]')

# 兼容性：保留旧的SURNAMES字典 / Совместимость
SURNAMES = {surname: 90 for surname in SINGLE_SURNAMES}
for surname in COMPOUND_SURNAMES:
    SURNAMES[surname] = 80


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
        if len(name) >= 2 and name[:2] in COMPOUND_SURNAMES:
            return name[:2], name[2:]
        # 单字姓 / Однословная фамилия
        if name[0] in SINGLE_SURNAMES:
            return name[0], name[1:]
        # 默认第一个字为姓 / По умолчанию первый символ
        return name[0], name[1:] if len(name) > 1 else ""

    # 拼音姓名 / Имя в пиньинь
    parts = [p for p in SEP_RE.split(name.lower()) if p]
    if not parts:
        return None, None

    # 查找姓氏：检查是否为已知拼音姓氏 / Поиск фамилии
    surname = parts[0]
    if is_surname_pinyin(surname):
        # 保持原样返回拼音形式 / Вернуть в пиньинь форме
        return surname.capitalize(), " ".join(parts[1:]).capitalize()

    # 默认处理 / Обработка по умолчанию
    return parts[0].capitalize(), " ".join(parts[1:]).capitalize()


# 集成姓名顺序检测 / Интеграция определения порядка
try:
    from .name_order_detector import detect_order, parse_authors
except ImportError:
    from name_order_detector import detect_order, parse_authors


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
        """检查姓氏 / Проверка фамилии"""
        if not surname:
            return False

        # 检查中文姓氏 / Проверка китайской фамилии
        if surname in ALL_SURNAMES:
            return True

        # 检查拼音姓氏 / Проверка пиньинь фамилии
        if is_surname_pinyin(surname):
            return True

        # 检查俄语姓氏 / Проверка русской фамилии
        if is_surname_russian(surname):
            return True

        return False


def create_default_processor():
    """工厂函数 / Фабричная функция"""
    return ChineseNameProcessor()


# 兼容旧API / Совместимость со старым API
class SurnameDatabase:
    """完整姓氏数据库 / Полная база фамилий"""

    def __init__(self):
        self.surnames = SURNAMES
        self.all_surnames = ALL_SURNAMES

    def is_known_surname(self, surname):
        """检查姓氏 / Проверка фамилии"""
        if not surname:
            return False

        # 检查中文姓氏 / Проверка китайской фамилии
        if surname in ALL_SURNAMES:
            return True

        # 检查拼音姓氏 / Проверка пиньинь фамилии
        if is_surname_pinyin(surname):
            return True

        # 检查俄语姓氏 / Проверка русской фамилии
        if is_surname_russian(surname):
            return True

        return False
