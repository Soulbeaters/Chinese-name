# -*- coding: utf-8 -*-
"""
姓名顺序检测 - 极简版 / Определение порядка имен - минимальная версия
基于ISTINA系统逻辑 / На основе логики системы ИСТИНА
"""
import re
from enum import Enum
from dataclasses import dataclass
from typing import List


# 兼容旧API / Совместимость со старым API
class NameOrder(Enum):
    """姓名顺序枚举 / Перечисление порядка имен"""
    SURNAME_FIRST = 1
    UNDETERMINED = 0
    GIVEN_NAME_FIRST = -1


@dataclass
class AuthorNameParts:
    """作者姓名部分 / Части имени автора"""
    raw_string: str
    name_parts: List[str]
    detected_order: NameOrder
    is_first_name_map: List[bool]
    confidence: float = 0.8


@dataclass
class ParsedAuthor:
    """解析后的作者 / Разобранный автор"""
    surname: str
    given_name: str
    middle_name: str = ""
    order: NameOrder = NameOrder.SURNAME_FIRST

# 正则表达式 / Регулярные выражения
W_RE = re.compile(r'\W', re.U)
SEP_RE = re.compile(r'[.,;，；\s\-]+')  # 支持中文标点和连字符
NAME_SEP_RE = re.compile(r'[\s\-]+')  # 姓名部分分隔
INITIALS_RE = re.compile(r'\b(\w|([jy][aeiou]|s?ch|мл|jr|ts|[kpstz]h))\b', re.U | re.I)
PATRONYM_RE = re.compile(r'\w+(ич|вна|инична|ovich|evich|ovna|evna)\b', re.U | re.I)

# 核心数据：高频名字 / Ядро данных: высокочастотные имена
_NAMES = {
    '明': 80, '华': 75, '伟': 70, '芳': 68, '娜': 65, '强': 63, '军': 60,
    'MING': 85, 'HUA': 80, 'WEI': 75, 'IVAN': 90, 'PETR': 85, 'ANNA': 88,
    'JOHN': 92, 'MARY': 90, 'DAVID': 88, 'MICHAEL': 87,
}


def detect_order(name_string, surname_db=None):
    """
    检测姓名顺序 / Определение порядка имени
    返回: 1(姓-名), 0(未知), -1(名-姓) / Возвращает: 1, 0, -1
    """
    names = [x.upper() for x in NAME_SEP_RE.split(name_string.strip()) if x]
    if not names:
        return 0

    # 判断每个部分是否为名字 / Определение, является ли каждая часть именем
    is_name = lambda n: (_NAMES.get(n, 0) >= 30 or
                        INITIALS_RE.match(n) or
                        PATRONYM_RE.search(n) or
                        len(re.sub(W_RE, '', n)) == 1)

    name_map = [is_name(n) for n in names]

    # 推断顺序 / Вывод порядка
    if not any(name_map):
        return 0
    if name_map[0]:
        return -1  # 第一个是名 / Первое - имя
    if any(name_map[1:]):
        return 1   # 后面有名 / Есть имя после
    return 0


def parse_author(author, order):
    """
    解析单个作者 / Разбор одного автора
    返回: (surname, firstname, middlename) / Возвращает: (фамилия, имя, отчество)
    """
    names = [x for x in NAME_SEP_RE.split(author.strip()) if x]
    if not names:
        return None

    if len(names) <= 3:
        if order >= 0:  # 姓在前 / Фамилия впереди
            last = names.pop(0)
            first = names.pop(0) if names else ""
            middle = names.pop() if names else ""
        else:  # 名在前 / Имя впереди
            last = names.pop(-1)
            first = names.pop(0) if names else ""
            middle = names.pop() if names else ""
    else:
        # 多个词的情况 / Случай нескольких слов
        if order >= 0:
            last = names[0]
            first = names[1] if len(names) > 1 else ""
            middle = " ".join(names[2:])
        else:
            last = names[-1]
            first = names[0]
            middle = " ".join(names[1:-1])

    return (last, first, middle)


def parse_authors(authors_string, surname_db=None):
    """
    解析作者列表 / Разбор списка авторов
    返回: [(surname, firstname, middlename, is_first), ...]
    """
    # 分割作者 / Разделение авторов
    if ";" in authors_string or "；" in authors_string:
        parts = re.split(r'[;；]', authors_string)
    else:
        parts = re.split(r'[,，]', authors_string)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return []

    # 检测每个作者的顺序 / Определение порядка для каждого автора
    orders = [detect_order(p, surname_db) for p in parts]

    # 第一作者单独处理 / Первый автор отдельно
    first_order = orders[0] if orders else 0
    cumulative = sum(orders) - first_order
    other_order = 1 if cumulative > 0 else (-1 if cumulative < 0 else 0)

    # 解析所有作者 / Разбор всех авторов
    result = []
    for i, part in enumerate(parts):
        order = first_order if i == 0 else other_order
        parsed = parse_author(part, order)
        if parsed:
            result.append(parsed + (i == 0,))  # 添加is_first标记

    return result


# 简单的API封装 / Простая обертка API
class NameOrderDetector:
    """极简检测器 / Минимальный детектор"""

    # ISTINA兼容性: 频率阈值 / Совместимость с ИСТИНА: порог частоты
    FREQUENCY_THRESHOLD = 30

    def __init__(self, surname_db=None, given_name_db=None):
        self.surname_db = surname_db
        self.given_name_db = given_name_db or _NAMES

    def _is_given_name(self, part):
        """判断是否为名字 / Проверка, является ли именем"""
        part_upper = part.upper()
        return (_NAMES.get(part_upper, 0) >= 30 or
                bool(INITIALS_RE.match(part)) or
                bool(PATRONYM_RE.search(part)) or
                len(re.sub(W_RE, '', part)) == 1)

    def detect_name_order(self, name):
        """检测姓名顺序，返回AuthorNameParts对象"""
        order = detect_order(name, self.surname_db)
        parts = [x for x in NAME_SEP_RE.split(name.strip()) if x]

        # 判断每个部分是否为名字
        is_first_name_map = [self._is_given_name(p) for p in parts]

        # 转换为NameOrder枚举
        order_enum = {1: NameOrder.SURNAME_FIRST, 0: NameOrder.UNDETERMINED,
                      -1: NameOrder.GIVEN_NAME_FIRST}[order]

        # 计算置信度
        confidence = 0.9 if any(is_first_name_map) else 0.5

        return AuthorNameParts(
            raw_string=name,
            name_parts=parts,
            detected_order=order_enum,
            is_first_name_map=is_first_name_map,
            confidence=confidence
        )

    def batch_detect_orders(self, names):
        """批量检测 / Пакетное определение"""
        return [self.detect_name_order(n) for n in names]

    def parse_author_list(self, authors):
        """解析作者列表，返回ParsedAuthor对象列表"""
        results = []
        for surname, first, middle, is_first in parse_authors(authors, self.surname_db):
            results.append(ParsedAuthor(
                surname=surname,
                given_name=first,
                middle_name=middle,
                order=NameOrder.SURNAME_FIRST
            ))
        return results


def create_name_order_detector(surname_db=None):
    """工厂函数 / Фабричная функция"""
    return NameOrderDetector(surname_db)
