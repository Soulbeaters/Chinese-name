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
    is_non_chinese: bool = False  # 是否为非中文姓氏 / Не китайская фамилия


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


def _clean_name_string(name_string):
    """
    清洗姓名字符串 / Очистка строки имени
    处理无效字符、连字符等 / Обработка невалидных символов, дефисов
    """
    # 去除首尾空白 / Удаление пробелов
    cleaned = name_string.strip()

    # 去除开头的无效字符（如 -ZH 的开头破折号）/ Удаление невалидных символов в начале
    cleaned = re.sub(r'^[^\w\u4e00-\u9fff]+', '', cleaned, flags=re.U)

    # 处理连字符姓名：Tian-Ye → Tian Ye / Обработка имен с дефисом
    # 但保留单字母连字符（如A-B）/ Но сохранить односимвольные с дефисом
    def replace_hyphen(match):
        parts = match.group(0).split('-')
        # 如果都是多字母单词，替换为空格 / Если многобуквенные слова, заменить на пробел
        if all(len(p) > 1 for p in parts):
            return ' '.join(parts)
        return match.group(0)

    cleaned = re.sub(r'(\w{2,})-(\w{2,})', replace_hyphen, cleaned, flags=re.U)

    return cleaned


def detect_order(name_string, surname_db=None):
    """
    检测姓名顺序 / Определение порядка имени
    返回: 1(姓-名), 0(未知), -1(名-姓) / Возвращает: 1, 0, -1

    改进策略 / Улучшенная стратегия:
    1. 中国学者署名规范识别 / Распознавание норм китайских ученых
    2. 使用姓氏数据库判断位置 / Использование базы фамилий
    3. 结合名字特征判断 / Комбинация с характеристиками имен
    4. 多重证据综合判断 / Комплексная оценка
    """
    # 在清洗前检查连字符模式 / Проверка дефиса до очистки
    original_parts = name_string.strip().split()
    has_hyphen_in_original = any('-' in part for part in original_parts)

    # 规则2: 连字符复合名格式 / Правило 2: Имя с дефисом
    # "Rui-Chen Song" → 名-名 姓 (连字符在前，姓在后)
    # "Wu Bing-Ru" → 姓 名-名 (连字符在后，姓在前)
    if has_hyphen_in_original and len(original_parts) >= 2 and surname_db and hasattr(surname_db, 'is_known_surname'):
        first_has_hyphen = '-' in original_parts[0]
        last_has_hyphen = '-' in original_parts[-1]

        # 检查姓氏位置（使用原始部分）
        first_is_sur = surname_db.is_known_surname(original_parts[0].upper().replace('-', ''))
        last_is_sur = surname_db.is_known_surname(original_parts[-1].upper().replace('-', ''))

        if first_has_hyphen and not last_has_hyphen and last_is_sur:
            # "Sheng-Lan Xu" 模式：名-名 姓
            return -1  # GIVEN_NAME_FIRST
        elif not first_has_hyphen and last_has_hyphen and first_is_sur:
            # "Wu Bing-Ru" 模式：姓 名-名
            return 1  # SURNAME_FIRST

    # 清洗输入 / Очистка входа
    name_string = _clean_name_string(name_string)

    names = [x.upper() for x in NAME_SEP_RE.split(name_string.strip()) if x]
    if not names:
        return 0

    if len(names) == 1:
        return 0  # 单个词无法判断

    # 规则1: 缩写名字格式 - "Zhang L." / Правило 1: Сокращенное имя
    # 中国学者习惯: [姓氏] [名字缩写.] 格式 100% 是姓-名顺序
    # Китайские ученые: [фамилия] [инициал.]
    if len(names) == 2:
        second_part = names[1]
        # 检查第二部分是否为缩写 (单字母+点，或两字母+点)
        is_abbreviation = (len(second_part) <= 3 and
                          second_part.endswith('.') and
                          second_part[0].isalpha())

        if is_abbreviation and surname_db and hasattr(surname_db, 'is_known_surname'):
            # 如果第一部分是已知姓氏，确定为姓-名格式
            if surname_db.is_known_surname(names[0]):
                return 1  # SURNAME_FIRST

    # 判断每个部分是否为名字 / Определение, является ли каждая часть именем
    is_name = lambda n: (_NAMES.get(n, 0) >= 30 or
                        INITIALS_RE.match(n) or
                        PATRONYM_RE.search(n) or
                        len(re.sub(W_RE, '', n)) == 1)

    name_map = [is_name(n) for n in names]

    # 新增：检查姓氏位置 / Проверка позиции фамилии
    first_is_surname = False
    last_is_surname = False

    if surname_db and hasattr(surname_db, 'is_known_surname'):
        first_is_surname = surname_db.is_known_surname(names[0])
        last_is_surname = surname_db.is_known_surname(names[-1])

    # 综合判断逻辑 / Комплексная логика
    # 1. 如果第一个是姓，最后一个不是姓 → 姓-名
    if first_is_surname and not last_is_surname:
        return 1

    # 2. 如果最后一个是姓，第一个不是姓 → 名-姓
    if last_is_surname and not first_is_surname:
        return -1

    # 3. 如果两个都是姓，看名字特征
    if first_is_surname and last_is_surname:
        # 如果中间有明显的名字特征，第一个应该是姓
        if len(names) > 2 and any(name_map[1:-1]):
            return 1
        # 如果第二个部分像名字，第一个是姓
        if len(names) >= 2 and name_map[1]:
            return 1
        # 默认返回未确定
        return 0

    # 4. 如果都不是已知姓氏，可能是非中文姓氏
    # 使用原有名字特征判断逻辑 / Использование характеристик имен
    if not first_is_surname and not last_is_surname:
        # 都不是中文姓氏，可能是外国姓名
        # 使用名字特征判断
        if not any(name_map):
            return 0  # 无法判断，标记为非中文
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
    # 清洗输入 / Очистка входа
    author = _clean_name_string(author)

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
    # 清洗输入 / Очистка входа
    authors_string = _clean_name_string(authors_string)

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
        # 清洗输入 / Очистка входа
        cleaned_name = _clean_name_string(name)

        order = detect_order(name, self.surname_db)
        parts = [x for x in NAME_SEP_RE.split(cleaned_name.strip()) if x]

        # 判断每个部分是否为名字
        is_first_name_map = [self._is_given_name(p) for p in parts]

        # 转换为NameOrder枚举
        order_enum = {1: NameOrder.SURNAME_FIRST, 0: NameOrder.UNDETERMINED,
                      -1: NameOrder.GIVEN_NAME_FIRST}[order]

        # 检查是否为非中文姓氏 / Проверка на не китайскую фамилию
        is_non_chinese = False
        if parts and len(parts) >= 2 and self.surname_db and hasattr(self.surname_db, 'is_known_surname'):
            # 如果第一个和最后一个部分都不是已知中文姓氏，标记为非中文
            # (这两个位置是姓氏可能出现的地方)
            first_is_chinese = self.surname_db.is_known_surname(parts[0])
            last_is_chinese = self.surname_db.is_known_surname(parts[-1])
            if not first_is_chinese and not last_is_chinese and order_enum == NameOrder.UNDETERMINED:
                is_non_chinese = True

        # 计算置信度
        if is_non_chinese:
            confidence = 0.3  # 非中文姓氏，低置信度
        elif any(is_first_name_map):
            confidence = 0.9
        else:
            confidence = 0.5

        return AuthorNameParts(
            raw_string=name,
            name_parts=parts,
            detected_order=order_enum,
            is_first_name_map=is_first_name_map,
            confidence=confidence,
            is_non_chinese=is_non_chinese
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
