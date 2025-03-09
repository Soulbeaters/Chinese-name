# -*- coding: utf-8 -*-
import itertools
import logging
import re
import json
import os
from pathlib import Path
from collections import defaultdict

# Пытаемся импортировать различные библиотеки транслитерации
try:
    from pypinyin import pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False

# Попытка импортировать оригинальный модуль, если не удается, то импортировать мок-модуль
try:
    from common.models.names import Firstname
except ImportError:
    # Добавление текущего каталога в путь Python
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    # Импорт мок-модуля
    try:
        from mock_common.models.names import Firstname
    except ImportError:
        # Если мок-модуль также не существует, создаем простой класс Firstname
        class Firstname:
            def __init__(self, name=""):
                self.name = name
                self.people_count = 100
        
        # Создаем мок объект-менеджер как статический атрибут
        class FirstnameManager:
            def in_bulk(self, names):
                return {name: Firstname(name) for name in names}
        
        # Устанавливаем статический атрибут objects
        Firstname.objects = FirstnameManager()

logger = logging.getLogger("common.utils")

W_RE = re.compile(r'\W', re.U)
SEP_RE = re.compile(r'[.,;\s+]')
LASTNAME_WITH_PREFIX_RE = re.compile(
    r'((?:\b(?:d[aieu]|l[aeio]|las|v[ao]n|der|d[ae]l|della|dos|te[rn]|zu|д[аеиую]|л[аеия]|лас|фон|ван|дер|д[ае]ль?|делла|дос|цу|те[рн])\s+)+\w+)',
    re.U | re.I)
MIDDLENAME_WITH_SUFFIX_RE = re.compile(r'(\w+\s+(?:оглы|[гк]ызы|заде|ogh?l[iu]|[gk][iu]z[iu]|zade))\b', re.U | re.I)
INITIALS_RE = re.compile(r'\b(\w|([jy][aeiou]|s?ch|мл|jr|ts|[kpstz]h))\b', re.U | re.I)
PATRONYM_SUFFIX_RU = re.compile(r'\w+(ич|вна|инична)\b', re.U | re.I)

# Добавление регулярных выражений для китайских иероглифов
# Диапазоны китайских иероглифов: основные (U+4E00-U+9FFF), расширение A (U+3400-U+4DBF), совместимые идеограммы (U+F900-U+FAFF)
CHINESE_CHAR_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')
CHINESE_NAME_RE = re.compile(r'^[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]{1,4}$')

# Определение базы данных распространенных китайских фамилий
# Включает: однословные фамилии, составные фамилии и их транслитерации на пиньинь и русский язык
CHINESE_SURNAMES = {
    # Распространенные однословные фамилии и их транслитерации
    '李': {'pinyin': 'li', 'palladius': 'ли', 'frequency': 95, 'region': ['全国']},
    '王': {'pinyin': 'wang', 'palladius': 'ван', 'frequency': 92, 'region': ['全国']},
    '张': {'pinyin': 'zhang', 'palladius': 'чжан', 'frequency': 90, 'region': ['全国']},
    '刘': {'pinyin': 'liu', 'palladius': 'лю', 'frequency': 85, 'region': ['全国']},
    '陈': {'pinyin': 'chen', 'palladius': 'чэнь', 'frequency': 80, 'region': ['全国', '华南']},
    '杨': {'pinyin': 'yang', 'palladius': 'ян', 'frequency': 77, 'region': ['全国', '西南']},
    '黄': {'pinyin': 'huang', 'palladius': 'хуан', 'frequency': 74, 'region': ['华南', '华东']},
    '赵': {'pinyin': 'zhao', 'palladius': 'чжао', 'frequency': 72, 'region': ['全国', '华北']},
    '吴': {'pinyin': 'wu', 'palladius': 'у', 'frequency': 70, 'region': ['华东', '华南']},
    '周': {'pinyin': 'zhou', 'palladius': 'чжоу', 'frequency': 69, 'region': ['华东', '华中']},
    '徐': {'pinyin': 'xu', 'palladius': 'сюй', 'frequency': 64, 'region': ['华东']},
    '孙': {'pinyin': 'sun', 'palladius': 'сунь', 'frequency': 63, 'region': ['华东', '华北']},
    '马': {'pinyin': 'ma', 'palladius': 'ма', 'frequency': 62, 'region': ['西北', '华北']},
    '朱': {'pinyin': 'zhu', 'palladius': 'чжу', 'frequency': 60, 'region': ['华东', '华中']},
    '胡': {'pinyin': 'hu', 'palladius': 'ху', 'frequency': 59, 'region': ['华中', '华东']},
    '郭': {'pinyin': 'guo', 'palladius': 'го', 'frequency': 58, 'region': ['华北', '华中']},
    '何': {'pinyin': 'he', 'palladius': 'хэ', 'frequency': 57, 'region': ['华南', '西南']},
    '高': {'pinyin': 'gao', 'palladius': 'гао', 'frequency': 56, 'region': ['华北', '东北']},
    '林': {'pinyin': 'lin', 'palladius': 'линь', 'frequency': 55, 'region': ['华南', '东南']},
    '罗': {'pinyin': 'luo', 'palladius': 'ло', 'frequency': 52, 'region': ['华南', '西南']},
    '郑': {'pinyin': 'zheng', 'palladius': 'чжэн', 'frequency': 51, 'region': ['华东', '华南']},
    '梁': {'pinyin': 'liang', 'palladius': 'лян', 'frequency': 50, 'region': ['华南', '西南']},
    '谢': {'pinyin': 'xie', 'palladius': 'се', 'frequency': 49, 'region': ['华南']},
    '宋': {'pinyin': 'song', 'palladius': 'сун', 'frequency': 48, 'region': ['华北', '华中']},
    '唐': {'pinyin': 'tang', 'palladius': 'тан', 'frequency': 47, 'region': ['华南', '华中']},
    '许': {'pinyin': 'xu', 'palladius': 'сюй', 'frequency': 46, 'region': ['华东']},
    '韩': {'pinyin': 'han', 'palladius': 'хань', 'frequency': 45, 'region': ['华北', '东北']},
    '冯': {'pinyin': 'feng', 'palladius': 'фэн', 'frequency': 44, 'region': ['华北']},
    '邓': {'pinyin': 'deng', 'palladius': 'дэн', 'frequency': 43, 'region': ['华南', '西南']},
    '曹': {'pinyin': 'cao', 'palladius': 'цао', 'frequency': 42, 'region': ['华北', '华东']},
    '彭': {'pinyin': 'peng', 'palladius': 'пэн', 'frequency': 41, 'region': ['华中', '华南']},
    '曾': {'pinyin': 'zeng', 'palladius': 'цзэн', 'frequency': 40, 'region': ['华南']},
    '肖': {'pinyin': 'xiao', 'palladius': 'сяо', 'frequency': 39, 'region': ['华南', '华东']},
    '田': {'pinyin': 'tian', 'palladius': 'тянь', 'frequency': 38, 'region': ['华北', '东北']},
    '董': {'pinyin': 'dong', 'palladius': 'дун', 'frequency': 37, 'region': ['华北', '华东']},
    '袁': {'pinyin': 'yuan', 'palladius': 'юань', 'frequency': 36, 'region': ['华中', '华东']},
    '潘': {'pinyin': 'pan', 'palladius': 'пань', 'frequency': 35, 'region': ['华东', '华南']},
    '蔡': {'pinyin': 'cai', 'palladius': 'цай', 'frequency': 34, 'region': ['华南', '华东']},
    
    # Распространенные составные фамилии и их транслитерации
    '欧阳': {'pinyin': 'ouyang', 'palladius': 'оуян', 'frequency': 15, 'region': ['华南']},
    '司马': {'pinyin': 'sima', 'palladius': 'сыма', 'frequency': 12, 'region': ['华北']},
    '诸葛': {'pinyin': 'zhuge', 'palladius': 'чжугэ', 'frequency': 11, 'region': ['华东']},
    '上官': {'pinyin': 'shangguan', 'palladius': 'шангуань', 'frequency': 10, 'region': ['华中']},
    '司徒': {'pinyin': 'situ', 'palladius': 'сыту', 'frequency': 9, 'region': ['华南']},
    '东方': {'pinyin': 'dongfang', 'palladius': 'дунфан', 'frequency': 8, 'region': ['华东']},
    '独孤': {'pinyin': 'dugu', 'palladius': 'дугу', 'frequency': 7, 'region': ['西北']},
    '慕容': {'pinyin': 'murong', 'palladius': 'жуйжун', 'frequency': 7, 'region': ['东北']},
    '夏侯': {'pinyin': 'xiahou', 'palladius': 'сяхоу', 'frequency': 6, 'region': ['华中']},
    '司空': {'pinyin': 'sikong', 'palladius': 'сыкун', 'frequency': 6, 'region': ['华北']},
    '尉迟': {'pinyin': 'yuchi', 'palladius': 'юйчи', 'frequency': 5, 'region': ['西北']},
    '皇甫': {'pinyin': 'huangfu', 'palladius': 'хуанфу', 'frequency': 5, 'region': ['华北']},
    '公孙': {'pinyin': 'gongsun', 'palladius': 'гунсунь', 'frequency': 5, 'region': ['华北']},
    '闻人': {'pinyin': 'wenren', 'palladius': 'вэньжэнь', 'frequency': 4, 'region': ['华东']},
    '令狐': {'pinyin': 'linghu', 'palladius': 'линху', 'frequency': 4, 'region': ['华北']}
}

# Добавление обратного отображения транслитераций пиньинь и системы Палладия
PINYIN_TO_SURNAME = defaultdict(list)
PALLADIUS_TO_SURNAME = defaultdict(list)

# Построение таблиц обратного отображения
for surname, transliterations in CHINESE_SURNAMES.items():
    pinyin = transliterations['pinyin']
    palladius = transliterations['palladius']
    PINYIN_TO_SURNAME[pinyin].append(surname)
    PALLADIUS_TO_SURNAME[palladius].append(surname)


def is_chinese_char(char):
    """
    Определяет, является ли символ китайским иероглифом
    
    :param str char: Один символ
    :return: Является ли символ китайским иероглифом
    :rtype: bool
    """
    if not char:
        return False
    
    # 使用Unicode范围检查
    code_point = ord(char)
    return (0x4E00 <= code_point <= 0x9FFF or  # CJK Unified Ideographs
            0x3400 <= code_point <= 0x4DBF or  # CJK Unified Ideographs Extension A
            0xF900 <= code_point <= 0xFAFF)    # CJK Compatibility Ideographs


def is_chinese_name(name):
    """
    Определяет, является ли строка китайским именем (состоит только из китайских иероглифов и имеет длину от 1 до 4)
    
    :param str name: Строка имени
    :return: Является ли строка китайским именем
    :rtype: bool
    """
    if not name:
        return False
    
    # 检查长度（中文名通常为2-4个字符）
    if len(name) > 4 or len(name) < 1:
        return False
    
    # 检查是否所有字符都是中文
    return all(is_chinese_char(char) for char in name)


def split_chinese_name(name):
    """
    Разделяет китайское имя на фамилию и имя
    
    :param str name: Китайское имя
    :return: Кортеж (фамилия, имя, отчество)
    :rtype: tuple
    """
    # Если пусто или не является китайским именем, возвращаем None
    if not name or not is_chinese_name(name):
        return None
    
    # Проверяем наличие имени в базе данных готовых имен
    if name in COMMON_CHINESE_FULL_NAMES:
        surname = COMMON_CHINESE_FULL_NAMES[name]['surname']
        given_name = COMMON_CHINESE_FULL_NAMES[name]['given_name']
        return (surname, given_name, '')
    
    # Проверяем, начинается ли с составной фамилии (2-3 иероглифа)
    for complex_surname in [s for s in CHINESE_SURNAMES.keys() if len(s) > 1]:
        if name.startswith(complex_surname):
            surname = complex_surname
            firstname = name[len(surname):]
            return (surname, firstname, '')
    
    # Проверяем, начинается ли с обычной фамилии (1 иероглиф)
    first_char = name[0]
    if first_char in CHINESE_SURNAMES:
        surname = first_char
        firstname = name[1:]
        return (surname, firstname, '')
    
    # Если фамилия не найдена, предполагаем, что первый иероглиф - фамилия
    return (name[0], name[1:], '')


def identify_transliterated_chinese_name(name):
    """
    Идентифицирует транслитерированное китайское имя (пиньинь или система Палладия)
    
    :param str name: Возможно транслитерированное китайское имя
    :return: Если идентифицировано как транслитерация китайского имени, возвращает кортеж (фамилия, имя, ''); иначе None
    :rtype: tuple | None
    """
    # Разделяем имя на части
    parts = [p for p in SEP_RE.split(name) if p]
    if not parts or len(parts) != 2:  # Пока поддерживаем только имена из двух частей
        return None
    
    # Вариант 1: Фамилия впереди, имя сзади (китайский порядок, например Li Ming)
    if parts[0] in PINYIN_TO_SURNAME:
        return (parts[0], parts[1], '')
    elif parts[0] in PALLADIUS_TO_SURNAME:
        return (parts[0], parts[1], '')
    
    # Вариант 2: Имя впереди, фамилия сзади (западный порядок, например Ming Li)
    if parts[1] in PINYIN_TO_SURNAME:
        return (parts[1], parts[0], '')
    elif parts[1] in PALLADIUS_TO_SURNAME:
        return (parts[1], parts[0], '')
    
    return None


def split_authors_string(authors_string):
    """
    Разделить строку с авторами на полные имена отдельных авторов

    :param str authors_string: строка авторов
    :return: пара: строка с полными именами; "и др." или False
    :rtype: (list(str), str | False)
    """
    # Обрезать пробельные символы
    authors_string = authors_string.strip()

    # Заменить "&" и "and" на запятые
    authors_string = re.sub(r'(\band\b|&)', ',', authors_string, flags=re.IGNORECASE)

    # Экранировать части составных фамилий и отчеств знаком #
    for pattern in (LASTNAME_WITH_PREFIX_RE, MIDDLENAME_WITH_SUFFIX_RE):
        for res in pattern.findall(authors_string):
            authors_string = re.sub(res, re.sub(r'\s+', '#', res), authors_string)

    # Выделить отдельно "и др."
    seps = [' ', ',', '(']
    add_et_al = False
    for suffix in ["и др.", "и др", "et al.", "et al", "с соавторами", "с соавторами."]:
        if authors_string.endswith(suffix) and (len(authors_string) == len(suffix) or authors_string[-(len(suffix) + 1)] in seps):
            authors_string = authors_string[:-(len(suffix) + 1)]
            add_et_al = suffix
            if not add_et_al.endswith("."):
                add_et_al += '.'
            break

    # Определить, запятой или точкой с запятой разделены имена разных авторов
    if ";" in authors_string and authors_string.count(";") >= (authors_string.count(",") - 1):
        authors_string_parts = authors_string.split(";")
    else:
        authors_string_parts = authors_string.split(",")

    # Перенести инициалы, которые были отделены запятой
    new_authors_string_parts = []
    for i, author in enumerate(authors_string_parts):
        initials = [y for y in [x.strip() for x in re.split(SEP_RE, author)] if re.sub(W_RE, '', y).isalpha()]
        if i >= 1 and len(initials) >= 1 and all(INITIALS_RE.match(x) for x in initials) and not INITIALS_RE.search(new_authors_string_parts[-1]):
            new_authors_string_parts[-1] += author
        else:
            new_authors_string_parts.append(author)
    authors_string_parts = new_authors_string_parts
    return authors_string_parts, add_et_al


def parse_author_name(author, order): # pylint: disable=too-many-branches
    """
    Разбить имя автора на тройку lastname-firstname-middlename с учётом вычисленного порядка имя-фамилия

    :param str author: полное имя автора
    :param int order: порядок. 1 - имена и инициалы идут после фамилии; 0 - фамилия между именами и инициалами; -1 - фамилия после имён и инициалов

    :return: кортеж (lastname, firstname, middlename)
    :rtype: tuple
    """
    # Сначала проверяем, является ли это китайским именем
    # Китайские имена не имеют пробелов, поэтому проверяем всю строку целиком
    author = author.strip()
    
    # Если это чисто китайское имя
    if is_chinese_name(author):
        return split_chinese_name(author)
    
    # Если это транслитерированное китайское имя (пиньинь или система Палладия)
    transliterated_result = identify_transliterated_chinese_name(author)
    if transliterated_result:
        return transliterated_result
    
    # Если это не китайское имя, используем существующую логику
    reverse = order >= 0

    names = [x for x in SEP_RE.split(author.strip()) if x]  # split the string by dots and whitespaces
    if not names:
        return None

    names = [name.replace("#", " ") for name in names]  # restore spaces instead of hashes

    if len(names) <= 3: # pylint: disable=too-many-nested-blocks
        last = names.pop(0 if reverse else -1)  # pop first or last item
        first = names.pop(0) if names else ""
        middle = names.pop() if names else ""
    else:
        last = []
        middle = ""
        if reverse:
            first = ""
            for i, name in enumerate(names):
                if last and (len(name) == 1 or i >= len(names) - 2):  # last is over
                    if not first:
                        first = name
                    else:  # first is over, remaining to middle; and add dots for initials
                        middle += name
                        if len(name) == 1 and len(names) - len(
                                last) - 1 > 1:  # add dot if this is not the single letter
                            middle += "."
                        elif i < len(names) - 1:
                            middle += " "
                else:
                    last.append(name)
        else:
            first = names.pop(0)
            flag_middle = True
            middles = []
            for name in names:
                if flag_middle and middles and len(name) > 1:
                    flag_middle = False
                if flag_middle:
                    middles.append(name)
                else:
                    last.append(name)
            for i, name in enumerate(middles):
                middle += name
                if len(name) == 1 and len(middles) > 1:
                    middle += "."
                elif i < len(middles) - 1:
                    middle += " "
        last = " ".join(last)
    return (last, first, middle)


def split_authors(authors_string): # pylint: disable=too-many-branches
    """
    Разделить строку, содержащую список авторов, на отдельных авторов и 
    распределить фамилии, имена и отчества/инициалы/отчества

    :param str authors_string: Строка с авторами, разделенная запятыми или точками с запятой
    :return: Список кортежей из фамилии, имени и отчества (и др.) каждого автора
    :rtype: list
    """
    res = []
    authors = split_authors_string(authors_string)
    for i, author in enumerate(authors, start=1):
        # Проверяем "et al."
        if author in ('et al.', 'и др.', 'et al', 'и др', 'et al.,', 'и др.,', '等'):
            res.append((author, '', ''))
            continue
            
        # 1. Первым делом проверяем, является ли имя китайским
        if is_chinese_name(author):
            surname, firstname, middlename = split_chinese_name(author)
            res.append((surname, firstname, middlename))
            continue
        
        # 2. Проверяем, является ли имя транслитерированным китайским именем
        chinese_transliterated = identify_transliterated_chinese_name(author)
        if chinese_transliterated:
            res.append(chinese_transliterated)
            continue
        
        # 3. Проверяем, является ли имя этническим китайским именем
        ethnic_name = process_ethnic_name(author)
        if ethnic_name:
            res.append(ethnic_name)
            continue
            
        # 4. Обработка смешанных китайско-латинских имен
        if any(is_chinese_char(c) for c in author):
            mixed_result = handle_mixed_script_name(author)
            if mixed_result:
                res.append(mixed_result)
                continue
                
        # 5. Определяем порядок китайских имен (если есть)
        # В случае, если имя не было распознано как китайское, но содержит китайские символы
        if any(is_chinese_char(c) for c in author):
            # Пытаемся обработать как редкую китайскую фамилию
            rare_result = handle_rare_surname(author)
            if rare_result:
                res.append(rare_result)
                continue
        
        # Если не китайское имя, используем стандартный алгоритм
        order = "western"
        if i <= min(3, len(authors)):
            author = author.replace('.', '. ')
            parts = [p for p in SEP_RE.split(author) if p]
            # Попытка определить порядок имен
            if parts and parts[0] in CHINESE_SURNAMES:
                order = "chinese"
                
        result = parse_author_name(author, order)
        res.append(result)
            
    # Обработка случая, когда только один автор и имя автора не удалось корректно разделить
    if len(res) == 1 and res[0][1] == '':
        author = authors[0]
        # Ищем известные шаблоны
        match = LASTNAME_WITH_PREFIX_RE.search(author)
        if match:
            lastname = match.group(1)
            firstname = author.replace(lastname, '').strip()
            # Удаляем возможные разделители
            firstname = re.sub(r'^[,;\s]+|[,;\s]+$', '', firstname)
            if firstname:
                return [(lastname, firstname, '')]
        # Проверяем, может ли имя быть обработано одной из новых функций
        for process_func in [handle_mixed_script_name, handle_rare_surname]:
            result = process_func(author)
            if result and result[1]:  # Проверяем, что имя не пустое
                return [result]
    
    return res


def export_chinese_surnames_to_json(file_path='chinese_surnames.json'):
    """
    Экспортировать данные о китайских фамилиях в файл JSON
    
    :param str file_path: Путь к файлу для сохранения
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(CHINESE_SURNAMES, f, ensure_ascii=False, indent=4)


def import_chinese_surnames_from_json(file_path='chinese_surnames.json'):
    """
    Импортировать данные о китайских фамилиях из файла JSON
    
    :param str file_path: Путь к файлу JSON
    :return: Импортированные данные о фамилиях
    :rtype: dict
    """
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Константы для систем транслитерации
TRANSLITERATION_PINYIN = 'pinyin'
TRANSLITERATION_PALLADIUS = 'palladius'
TRANSLITERATION_WADE_GILES = 'wade_giles'
TRANSLITERATION_YALE = 'yale'

# Отображение инициалей пиньинь в системе Палладия
PINYIN_INITIAL_TO_PALLADIUS = {
    'b': 'б', 'p': 'п', 'm': 'м', 'f': 'ф', 
    'd': 'д', 't': 'т', 'n': 'н', 'l': 'л',
    'g': 'г', 'k': 'к', 'h': 'х',
    'j': 'цз', 'q': 'ц', 'x': 'с',
    'zh': 'чж', 'ch': 'ч', 'sh': 'ш', 'r': 'ж',
    'z': 'цз', 'c': 'ц', 's': 'с',
    'y': 'й', 'w': 'в'
}

# Отображение финалей пиньинь в системе Палладия
PINYIN_FINAL_TO_PALLADIUS = {
    'a': 'а', 'o': 'о', 'e': 'э', 'i': 'и', 'u': 'у', 'ü': 'юй',
    'ai': 'ай', 'ei': 'эй', 'ao': 'ао', 'ou': 'оу',
    'an': 'ань', 'en': 'энь', 'ang': 'ан', 'eng': 'эн', 'ong': 'ун',
    'ia': 'я', 'ie': 'е', 'iao': 'яо', 'iu': 'ю',
    'ian': 'янь', 'in': 'инь', 'iang': 'ян', 'ing': 'ин', 'iong': 'юн',
    'ua': 'уа', 'uo': 'о', 'uai': 'уай', 'ui': 'уй',
    'uan': 'уань', 'un': 'унь', 'uang': 'уан', 'ueng': 'уэн',
    'üe': 'юэ', 'üan': 'юань', 'ün': 'юнь'
}

# Распространенные полные соответствия слогов пиньинь в системе Палладия
PINYIN_TO_PALLADIUS = {
    'li': 'ли', 'wang': 'ван', 'zhang': 'чжан', 'chen': 'чэнь', 'yang': 'ян',
    'liu': 'лю', 'huang': 'хуан', 'zhao': 'чжао', 'wu': 'у', 'zhou': 'чжоу',
    'xu': 'сюй', 'sun': 'сунь', 'hu': 'ху', 'zhu': 'чжу', 'gao': 'гао',
    'lin': 'линь', 'he': 'хэ', 'guo': 'го', 'ma': 'ма', 'luo': 'ло',
    'liang': 'лян', 'song': 'сун', 'zheng': 'чжэн', 'xie': 'се', 'tang': 'тан',
    'han': 'хань', 'cao': 'цао', 'feng': 'фэн', 'cheng': 'чэн', 'wei': 'вэй'
}

# Правила преобразования пиньинь в систему Уэйда-Джайлза
PINYIN_TO_WADE_GILES_RULES = {
    'b': 'p', 'p': "p'", 'd': 't', 't': "t'", 'g': 'k', 'k': "k'",
    'j': 'ch', 'q': "ch'", 'x': 'hs', 'zh': 'ch', 'ch': "ch'", 'z': 'ts',
    'c': "ts'", 'r': 'j', 'si': 'ssu', 'zi': 'tzu', 'ci': "tz'u"
}

# Распространенные полные соответствия слогов пиньинь в системе Уэйда-Джайлза
PINYIN_TO_WADE_GILES = {
    'li': 'li', 'wang': 'wang', 'zhang': 'chang', 'chen': "ch'en", 'yang': 'yang',
    'liu': 'liu', 'huang': 'huang', 'zhao': 'chao', 'wu': 'wu', 'zhou': 'chou',
    'xu': 'hsü', 'sun': 'sun', 'hu': 'hu', 'zhu': 'chu', 'gao': 'kao'
}

# Правила преобразования пиньинь в Йельскую систему
PINYIN_TO_YALE_RULES = {
    'j': 'j', 'q': 'ch', 'x': 'sy', 'zh': 'j', 'ch': 'ch', 'sh': 'sh',
    'z': 'dz', 'c': 'ts', 's': 's', 'r': 'r',
    'a': 'a', 'o': 'o', 'e': 'e', 'i': 'i', 'u': 'u', 'ü': 'yu'
}

# Распространенные полные соответствия слогов пиньинь в Йельской системе
PINYIN_TO_YALE = {
    'li': 'li', 'wang': 'wang', 'zhang': 'jang', 'chen': 'chen', 'yang': 'yang',
    'liu': 'lyou', 'huang': 'hwang', 'zhao': 'jaw', 'wu': 'wu', 'zhou': 'jou'
}

# Простое отображение китайских иероглифов в пиньинь (используется только если библиотека pypinyin недоступна)
HANZI_TO_PINYIN_DICT = {
    '李': 'li', '王': 'wang', '张': 'zhang', '陈': 'chen', '杨': 'yang',
    '刘': 'liu', '黄': 'huang', '赵': 'zhao', '吴': 'wu', '周': 'zhou',
    '徐': 'xu', '孙': 'sun', '胡': 'hu', '朱': 'zhu', '高': 'gao',
    '林': 'lin', '何': 'he', '郭': 'guo', '马': 'ma', '罗': 'luo',
    '梁': 'liang', '宋': 'song', '郑': 'zheng', '谢': 'xie', '唐': 'tang',
    '冯': 'feng', '邓': 'deng', '曹': 'cao', '彭': 'peng', '曾': 'zeng',
    '肖': 'xiao', '田': 'tian', '董': 'dong', '袁': 'yuan', '潘': 'pan',
    '蔡': 'cai', '欧阳': 'ouyang', '司马': 'sima', '诸葛': 'zhuge',
    '上官': 'shangguan', '闻人': 'wenren', '夏侯': 'xiahou', '独孤': 'dugu',
    '东方': 'dongfang', '令狐': 'linghu'
}

def hanzi_to_pinyin(text):
    """
    Преобразование китайских иероглифов в пиньинь
    
    :param str text: Входной китайский текст
    :return: Пиньинь
    :rtype: str
    """
    if not PYPINYIN_AVAILABLE:
        logger.warning("pypinyin не установлен, используется простое сопоставление")
        # Если библиотека pypinyin недоступна, используем простое отображение
        result = ''
        for char in text:
            if char in HANZI_TO_PINYIN_DICT:
                result += HANZI_TO_PINYIN_DICT[char] + ' '
            else:
                result += char + ' '
        return result.strip()
    
    # Используем библиотеку pypinyin
    result = pinyin(text, style=Style.NORMAL)
    return ' '.join([item[0] for item in result])

def hanzi_to_palladius(text):
    """
    Преобразование китайских иероглифов в систему Палладия (русская транслитерация)
    
    :param str text: Входной китайский текст
    :return: Транслитерация по системе Палладия
    :rtype: str
    """
    # Сначала преобразуем в пиньинь
    py = hanzi_to_pinyin(text).split()
    
    # Преобразуем пиньинь в систему Палладия согласно правилам
    result = []
    for syllable in py:
        if syllable in PINYIN_TO_PALLADIUS:
            result.append(PINYIN_TO_PALLADIUS[syllable])
        else:
            # Применяем правила транслитерации Палладия
            palladius = syllable
            # Заменяем инициали
            for py_initial, pal_initial in PINYIN_INITIAL_TO_PALLADIUS.items():
                if syllable.startswith(py_initial):
                    palladius = palladius.replace(py_initial, pal_initial, 1)
                    break
            
            # Заменяем финали
            for py_final, pal_final in PINYIN_FINAL_TO_PALLADIUS.items():
                if syllable.endswith(py_final):
                    palladius = palladius[:-len(py_final)] + pal_final
                    break
            
            result.append(palladius)
    
    return ' '.join(result)

def hanzi_to_wade_giles(text):
    """
    Преобразование китайских иероглифов в систему Уэйда-Джайлза
    
    :param str text: Входной китайский текст
    :return: Транслитерация по системе Уэйда-Джайлза
    :rtype: str
    """
    # Сначала преобразуем в пиньинь
    py = hanzi_to_pinyin(text).split()
    
    # Преобразуем пиньинь в систему Уэйда-Джайлза согласно правилам
    result = []
    for syllable in py:
        if syllable in PINYIN_TO_WADE_GILES:
            result.append(PINYIN_TO_WADE_GILES[syllable])
        else:
            # Применяем правила системы Уэйда-Джайлза
            wade_giles = syllable
            # Реализуем правила преобразования
            for py_sound, wg_sound in PINYIN_TO_WADE_GILES_RULES.items():
                wade_giles = wade_giles.replace(py_sound, wg_sound)
            
            result.append(wade_giles)
    
    return ' '.join(result)

def hanzi_to_yale(text):
    """
    Преобразование китайских иероглифов в Йельскую систему
    
    :param str text: Входной китайский текст
    :return: Транслитерация по Йельской системе
    :rtype: str
    """
    # Аналогично предыдущим функциям, реализуем Йельскую систему
    py = hanzi_to_pinyin(text).split()
    
    result = []
    for syllable in py:
        if syllable in PINYIN_TO_YALE:
            result.append(PINYIN_TO_YALE[syllable])
        else:
            # Применяем правила Йельской системы
            yale = syllable
            # Реализуем правила преобразования
            for py_sound, y_sound in PINYIN_TO_YALE_RULES.items():
                yale = yale.replace(py_sound, y_sound)
            
            result.append(yale)
    
    return ' '.join(result)

def transliterate_chinese_name(name, system=TRANSLITERATION_PINYIN):
    """
    Транслитерация китайского имени в указанную систему
    
    :param str name: Китайское имя
    :param str system: Система транслитерации (pinyin, palladius, wade_giles, yale)
    :return: Транслитерированное имя
    :rtype: str
    """
    if not is_chinese_name(name):
        return name
    
    # Разделяем на фамилию и имя
    surname, firstname, _ = split_chinese_name(name)
    
    # Транслитерируем в указанную систему
    if system == TRANSLITERATION_PINYIN:
        tr_surname = hanzi_to_pinyin(surname).title()
        tr_firstname = hanzi_to_pinyin(firstname).title()
    elif system == TRANSLITERATION_PALLADIUS:
        tr_surname = hanzi_to_palladius(surname).title()
        tr_firstname = hanzi_to_palladius(firstname).title()
    elif system == TRANSLITERATION_WADE_GILES:
        tr_surname = hanzi_to_wade_giles(surname).title()
        tr_firstname = hanzi_to_wade_giles(firstname).title()
    elif system == TRANSLITERATION_YALE:
        tr_surname = hanzi_to_yale(surname).title()
        tr_firstname = hanzi_to_yale(firstname).title()
    else:
        return name
    
    # Возвращаем в китайском порядке (фамилия + имя)
    return f"{tr_surname} {tr_firstname}"

def compare_transliterations(name, systems=None):
    """
    Сравнение различных систем транслитерации одного и того же китайского имени
    
    :param str name: Китайское имя или его транслитерация
    :param list systems: Список систем транслитерации для сравнения, по умолчанию все системы
    :return: Варианты имени в разных системах транслитерации
    :rtype: dict
    """
    if systems is None:
        systems = [TRANSLITERATION_PINYIN, TRANSLITERATION_PALLADIUS, 
                  TRANSLITERATION_WADE_GILES, TRANSLITERATION_YALE]
    
    result = {}
    
    # Если это китайское имя, транслитерируем напрямую
    if is_chinese_name(name):
        chinese_name = name
        for system in systems:
            result[system] = transliterate_chinese_name(chinese_name, system)
        result['original'] = chinese_name
        return result
    
    # Если это транслитерированное имя, пытаемся определить систему и преобразовать в китайские иероглифы
    # Это сложная задача, требующая эффективного обратного отображения
    # Для упрощения только определяем оригинальную систему
    original_system = detect_transliteration_system(name)
    if original_system:
        result['detected_system'] = original_system
        result[original_system] = name
        
        # Если можем преобразовать в китайские иероглифы, добавляем другие транслитерации
        chinese_name = transliteration_to_hanzi(name, original_system)
        if chinese_name:
            result['original'] = chinese_name
            for system in systems:
                if system != original_system:
                    result[system] = transliterate_chinese_name(chinese_name, system)
    
    return result

def detect_transliteration_system(name):
    """
    Определение системы транслитерации имени
    
    :param str name: Транслитерированное китайское имя
    :return: Определенная система транслитерации, None если не удалось определить
    :rtype: str
    """
    # Разделяем имя на части
    parts = [p for p in SEP_RE.split(name) if p]
    if not parts or len(parts) < 1 or len(parts) > 3:
        return None
    
    # Проверяем признаки системы Палладия
    palladius_features = ['ань', 'энь', 'инь', 'унь', 'юнь', 'чж', 'цз', 'ц']
    for part in parts:
        for feature in palladius_features:
            if feature in part.lower():
                return TRANSLITERATION_PALLADIUS
    
    # Проверяем признаки системы Уэйда-Джайлза
    wade_giles_features = ["p'", "t'", "k'", "ch'", "ts'", 'hs', 'ssu']
    for part in parts:
        for feature in wade_giles_features:
            if feature in part.lower():
                return TRANSLITERATION_WADE_GILES
    
    # Проверяем признаки Йельской системы
    yale_features = ['sywe', 'syw', 'syoo', 'jwe', 'jywe']
    for part in parts:
        for feature in yale_features:
            if feature in part.lower():
                return TRANSLITERATION_YALE
    
    # По умолчанию считаем, что это пиньинь (наиболее распространённая система)
    return TRANSLITERATION_PINYIN

def transliteration_to_hanzi(name, system=None):
    """
    Попытка преобразования транслитерированного имени обратно в китайские иероглифы
    
    :param str name: Транслитерированное имя
    :param str system: Система транслитерации, если None, определяется автоматически
    :return: Возможное написание китайскими иероглифами, None если преобразование невозможно
    :rtype: str
    """
    if system is None:
        system = detect_transliteration_system(name)
    
    if not system:
        return None
    
    # Разделение имени на части
    parts = [p for p in SEP_RE.split(name) if p]
    if not parts or len(parts) < 1 or len(parts) > 3:
        return None
    
    # Попытка преобразования фамилии (только для распространенных фамилий)
    surname_hanzi = None
    
    # Проверка порядка имени: фамилия+имя или имя+фамилия
    if len(parts) == 2:
        # Попытка использовать первую часть как фамилию
        if system == TRANSLITERATION_PINYIN and parts[0].lower() in PINYIN_TO_SURNAME:
            surname_hanzi = PINYIN_TO_SURNAME[parts[0].lower()]
            order = "chinese"  # Китайский порядок: фамилия впереди
        elif system == TRANSLITERATION_PALLADIUS and parts[0].lower() in PALLADIUS_TO_SURNAME:
            surname_hanzi = PALLADIUS_TO_SURNAME[parts[0].lower()]
            order = "chinese"
        # Попытка использовать последнюю часть как фамилию
        elif system == TRANSLITERATION_PINYIN and parts[-1].lower() in PINYIN_TO_SURNAME:
            surname_hanzi = PINYIN_TO_SURNAME[parts[-1].lower()]
            order = "western"  # Западный порядок: фамилия в конце
        elif system == TRANSLITERATION_PALLADIUS and parts[-1].lower() in PALLADIUS_TO_SURNAME:
            surname_hanzi = PALLADIUS_TO_SURNAME[parts[-1].lower()]
            order = "western"
        else:
            return None
        
        # Для простой реализации мы не преобразуем имя, только определяем фамилию
        # Полная функциональная система требует большой базы данных имен и сложных алгоритмов
        if order == "chinese":
            return surname_hanzi + "?"  # Фамилия впереди, имя неизвестно
        else:
            return "?" + surname_hanzi  # Имя неизвестно, фамилия в конце
    
    return None

# Словарь преобразования между упрощенными и традиционными иероглифами (упрощенная версия, только распространенные символы)
SIMPLIFIED_TO_TRADITIONAL = {
    '李': '李', '王': '王', '张': '張', '陈': '陳', '杨': '楊',
    '刘': '劉', '黄': '黃', '赵': '趙', '吴': '吳', '周': '周',
    '徐': '徐', '孙': '孫', '胡': '胡', '朱': '朱', '高': '高',
    '林': '林', '何': '何', '郭': '郭', '马': '馬', '罗': '羅',
    '梁': '梁', '宋': '宋', '郑': '鄭', '谢': '謝', '唐': '唐'
}

TRADITIONAL_TO_SIMPLIFIED = {v: k for k, v in SIMPLIFIED_TO_TRADITIONAL.items()}

def is_simplified_chinese(text):
    """
    检测文本是否使用简体中文字�?    
    :param str text: 中文文本
    :return: 是否为简体中�?    :rtype: bool
    """
    for char in text:
        if char in TRADITIONAL_TO_SIMPLIFIED and TRADITIONAL_TO_SIMPLIFIED[char] != char:
            return False
    return True

def is_traditional_chinese(text):
    """
    检测文本是否使用繁体中文字�?    
    :param str text: 中文文本
    :return: 是否为繁体中�?    :rtype: bool
    """
    for char in text:
        if char in SIMPLIFIED_TO_TRADITIONAL and SIMPLIFIED_TO_TRADITIONAL[char] != char:
            return False
    return True

def simplified_to_traditional(text):
    """
    将简体中文转换为繁体中文
    
    :param str text: 简体中文文�?    :return: 繁体中文文本
    :rtype: str
    """
    result = ''
    for char in text:
        if char in SIMPLIFIED_TO_TRADITIONAL:
            result += SIMPLIFIED_TO_TRADITIONAL[char]
        else:
            result += char
    return result

def traditional_to_simplified(text):
    """
    Преобразование традиционных китайских иероглифов в упрощенные
    
    :param str text: Текст с традиционными иероглифами
    :return: Текст с упрощенными иероглифами
    :rtype: str
    """
    result = ''
    for char in text:
        if char in TRADITIONAL_TO_SIMPLIFIED:
            result += TRADITIONAL_TO_SIMPLIFIED[char]
        else:
            result += char
    return result

# Модуль обработки этнических имен
ETHNIC_NAME_PATTERNS = {
    'tibetan': {
        'surnames': ['拉木', '次仁', '索朗', '丹增', '平措', '格桑', '多吉', '白玛', '洛桑', '旦增'],
        'pattern': r'(拉木|次仁|索朗|丹增|平措|格桑|多吉|白玛|洛桑|旦增)([^,;\s]+)'
    },
    'uyghur': {
        'surnames': ['艾买提', '买买提', '阿布都', '阿布力', '阿不都', '吐尔逊', '吐尔洪', '阿卜都'],
        'pattern': r'(艾买提|买买提|阿布都|阿布力|阿不都|吐尔逊|吐尔洪|阿卜都)([^,;\s]+)'
    },
    'mongolian': {
        'surnames': ['巴特尔', '乌力吉', '敖特根', '呼和', '钢巴特', '其其格', '铁木尔'],
        'pattern': r'(巴特尔|乌力吉|敖特根|呼和|钢巴特|其其格|铁木尔)([^,;\s]+)'
    }
}

def identify_ethnic_name(name):
    """
    Идентификация этнических имен
    
    :param str name: Имя
    :return: Идентифицированная этническая группа и разбор имени, None если это не этническое имя
    :rtype: tuple
    """
    if not name:
        return None
    
    for ethnic, info in ETHNIC_NAME_PATTERNS.items():
        pattern = re.compile(info['pattern'], re.U)
        match = pattern.match(name)
        if match:
            surname = match.group(1)
            firstname = match.group(2)
            return (ethnic, surname, firstname, '')
    
    return None

def process_ethnic_name(name):
    """
    Обработка этнических имен, извлечение фамилии и имени
    
    :param str name: Имя
    :return: Разложение имени (фамилия, имя, пусто), None если это не этническое имя
    :rtype: tuple
    """
    result = identify_ethnic_name(name)
    if result:
        return (result[1], result[2], '')
    return None

# Добавление функциональности для обработки модели ArticleAuthorship
    """
    Класс для проверки корректности обработки китайских имен в модели ArticleAuthorship
    """
    def __init__(self, article_authorship_model=None):
        """
        Инициализация проверки
        
        :param article_authorship_model: Экземпляр модели ArticleAuthorship, если None, используется мок-объект
        """
        self.model = article_authorship_model
        self.fixes_log = []
        
        # Если нет реальной модели, используем мок-объект
        if self.model is None:
            # Создаем мок-объект ArticleAuthorship
            class MockArticleAuthorship:
                def __init__(self):
                    self.authors = []
                
                def get_all_authors(self):
                    return self.authors
                
                def update_author(self, author_id, data):
                    for i, author in enumerate(self.authors):
                        if author['id'] == author_id:
                            self.authors[i].update(data)
                            return True
                    return False
            
            self.model = MockArticleAuthorship()
    
    def check_chinese_names(self, fix=False):
        """
        Проверка корректности обработки всех китайских имен в модели ArticleAuthorship
        
        :param bool fix: Автоматически исправлять найденные проблемы
        :return: Список проблем и (если fix=True) список исправленных проблем
        :rtype: tuple
        """
        issues = []
        fixed = []
        
        # Получение всех авторов
        authors = self.model.get_all_authors()
        
        for author in authors:
            # Проверка на китайское имя
            full_name = f"{author.get('lastname', '')} {author.get('firstname', '')} {author.get('middlename', '')}".strip()
            
            # Проверка наличия китайских символов
            has_chinese = any(is_chinese_char(c) for c in full_name)
            
            if has_chinese:
                # Повторный анализ китайского имени
                original_parts = (author.get('lastname', ''), 
                                 author.get('firstname', ''), 
                                 author.get('middlename', ''))
                
                # Повторный анализ полного имени
                new_parts = None
                
                # Проверка различных форматов имени
                possible_name_formats = [
                    full_name,  # Полное имя
                    f"{author.get('lastname', '')}{author.get('firstname', '')}",  # Фамилия+имя (без пробела)
                    author.get('lastname', ''),  # Только фамилия (для случаев с одним китайским полем)
                    author.get('firstname', '')  # Только имя (для случаев когда фамилия может быть в поле имени)
                ]
                
                for name_format in possible_name_formats:
                    # Пропуск пустых строк
                    if not name_format.strip():
                        continue
                    
                    # Проверка на чистое китайское имя
                    if is_chinese_name(name_format):
                        new_parts = split_chinese_name(name_format)
                        if new_parts:
                            break
                    
                    # Проверка на транслитерированное китайское имя
                    transliterated = identify_transliterated_chinese_name(name_format)
                    if transliterated:
                        new_parts = transliterated
                        break
                
                # Если анализ не удался, попробовать преобразовать традиционные иероглифы в упрощенные
                if not new_parts and any(is_traditional_chinese(c) for c in full_name):
                    simplified = traditional_to_simplified(full_name)
                    if is_chinese_name(simplified):
                        new_parts = split_chinese_name(simplified)
                
                # Если найден новый анализ, и он отличается от исходного
                if new_parts and new_parts != original_parts:
                    issue = {
                        'author_id': author.get('id'),
                        'author_name': full_name,
                        'original': original_parts,
                        'suggested': new_parts
                    }
                    issues.append(issue)
                    
                    # Если нужно исправить
                    if fix:
                        # Создание обновленных данных
                        update_data = {
                            'lastname': new_parts[0],
                            'firstname': new_parts[1],
                            'middlename': new_parts[2] if len(new_parts) > 2 else ''
                        }
                        
                        # Обновление информации об авторе
                        success = self.model.update_author(author.get('id'), update_data)
                        if success:
                            fixed.append(issue)
                            self.fixes_log.append(f"Fixed: {full_name} -> {new_parts[0]} {new_parts[1]} {new_parts[2]}")
        
        return {'issues_count': len(issues), 'fixed_count': len(fixed), 'issues': issues}
    
    def get_fixes_log(self):
        """
        Получить журнал исправлений
        
        :return: Журнал операций исправления
        :rtype: list
        """
        return self.fixes_log

# Функции пакетной обработки
def batch_process_chinese_names(names_list, output_format='tuple'):
    """
    Пакетная обработка китайских имен
    
    :param list names_list: Список имен для обработки
    :param str output_format: Формат вывода, может быть 'tuple' (кортеж имен) или 'dict' (словарь с детальной информацией)
    :return: Список результатов обработки
    :rtype: list
    """
    results = []
    
    for name in names_list:
        # Обработка чистых китайских имен
        if is_chinese_name(name):
            parts = split_chinese_name(name)
            if parts:
                if output_format == 'tuple':
                    results.append(parts)
                else:
                    results.append({
                        'original': name,
                        'lastname': parts[0],
                        'firstname': parts[1],
                        'middlename': parts[2] if len(parts) > 2 else '',
                        'type': 'pure_chinese'
                    })
                continue
        
        # Обработка транслитерированных имен
        for system in [TRANSLITERATION_PALLADIUS, TRANSLITERATION_WADE_GILES, TRANSLITERATION_YALE]:
            detected = detect_transliteration_system(name, system)
            if detected:
                if output_format == 'tuple':
                    results.append((detected.get('lastname', ''), 
                                  detected.get('firstname', ''), 
                                  detected.get('middlename', '')))
                else:
                    detected['original'] = name
                    detected['type'] = 'transliterated'
                    results.append(detected)
                break
        else:
            # Если не обнаружено, добавить None или пустую запись
            if output_format == 'tuple':
                results.append(None)
            else:
                results.append({
                    'original': name,
                    'lastname': '',
                    'firstname': '',
                    'middlename': '',
                    'type': 'unknown'
                })
    
    return results

def verify_chinese_name_processing(name, expected_result=None):
    """
    Проверка правильности обработки китайского имени
    
    :param str name: Имя для проверки
    :param tuple expected_result: Ожидаемый результат обработки, если None - не проверяется
    :return: Словарь с результатами проверки
    :rtype: dict
    """
    # Выполнение всех возможных методов обработки
    results = {}
    
    # Проверка, является ли имя китайским
    is_chinese = is_chinese_name(name)
    results['is_chinese'] = is_chinese
    
    # Попытка различных методов обработки
    chinese_result = split_chinese_name(name) if is_chinese else None
    transliterated_result = identify_transliterated_chinese_name(name)
    ethnic_result = process_ethnic_name(name)
    
    # Запись результатов
    results['chinese_split'] = chinese_result
    results['transliterated'] = transliterated_result
    results['ethnic'] = ethnic_result
    
    # Определение окончательного результата
    final_result = chinese_result or transliterated_result or ethnic_result
    results['final_result'] = final_result
    
    # Проверка результата
    if expected_result:
        results['matches_expected'] = (final_result == expected_result)
        results['expected'] = expected_result

def manual_correction_interface(name, corrected_parts):
    """
    Интерфейс для ручной коррекции разбора китайского имени
    
    :param str name: Исходное имя
    :param tuple corrected_parts: Вручную исправленные части имени (фамилия, имя, отчество)
    :return: Обновленный результат
    :rtype: tuple
    """
    # Проверка действительности коррекции
    if not corrected_parts or len(corrected_parts) != 3:
        return None
    
    # Запись ручной коррекции (может быть расширено до постоянного хранения)
    manual_correction = {
        'original': name,
        'corrected': corrected_parts
    }
    
    # В реальной реализации эту коррекцию можно добавить в базу данных или файл
    # Здесь просто возвращаем исправленный результат
    return corrected_parts

# Обработка редких фамилий
def handle_rare_surname(name):
    """
    Обработка очень редких китайских фамилий
    
    :param str name: Китайское имя
    :return: Результат обработки (фамилия, имя, отчество), None если невозможно определить
    :rtype: tuple
    """
    if not name or not is_chinese_name(name):
        return None
    
    # Используем вероятностный метод - большинство китайских фамилий состоит из одного иероглифа
    if len(name) >= 2:
        # Вероятность фамилии из одного иероглифа выше
        surname = name[0]
        given_name = name[1:]
        
        # Особый случай: если имя состоит из трех иероглифов, возможно это двусложная фамилия + односложное имя
        if len(name) == 3:
            # Проверяем, могут ли первые два иероглифа быть двусложной фамилией
            if is_likely_complex_surname(name[:2]):
                surname = name[:2]
                given_name = name[2:]
    
    else:
        # Одиночный иероглиф, возможно это только фамилия
        surname = name
        given_name = ""
    
    return (surname, given_name, '')

def is_likely_complex_surname(chars):
    """
    Определение вероятности того, что строка является сложной фамилией
    
    :param str chars: Строка для проверки
    :return: Является ли вероятной сложной фамилией
    :rtype: bool
    """
    # Проверка наличия в списке известных сложных фамилий
    for surname in [s for s in CHINESE_SURNAMES.keys() if len(s) > 1]:
        if chars.startswith(surname):
            return True
    
    # Проверка специфических шаблонов (может быть расширено)
    complex_patterns = [
        r'^[上少东西南北中]',  # Шангуань, Шаоси, Дунфан и т.д.
        r'^[司公皇独慕尉欧闻令]',  # Сыма, Гунсунь, Хуанфу и т.д.
    ]
    
    for pattern in complex_patterns:
        if re.match(pattern, chars):
            return True
    
    return False

# Обработка имен со смешанным латинским и китайским письмом
def handle_mixed_script_name(name):
    """
    Обработка имен, содержащих как латинские буквы, так и китайские иероглифы
    
    :param str name: Имя со смешанным письмом
    :return: Результат разбора (фамилия, имя, отчество)
    :rtype: tuple
    """
    if not name:
        return None
    
    # Разделение на части с иероглифами и не-иероглифами
    hanzi_parts = []
    latin_parts = []
    
    # Извлечение последовательностей китайских иероглифов и латинских букв
    current_type = None
    current_part = ""
    
    for char in name:
        is_hanzi = is_chinese_char(char)
        char_type = "hanzi" if is_hanzi else "latin"
        
        # Если тип изменился или встречен пробел, сохраняем текущую часть
        if char.isspace() or (current_type and current_type != char_type):
            if current_part:
                if current_type == "hanzi":
                    hanzi_parts.append(current_part)
                else:
                    latin_parts.append(current_part)
                current_part = ""
        
        # Пропускаем пробелы
        if char.isspace():
            continue
        
        # Добавляем символ к текущей части
        current_part += char
        current_type = char_type
    
    # Сохраняем последнюю часть
    if current_part:
        if current_type == "hanzi":
            hanzi_parts.append(current_part)
        else:
            latin_parts.append(current_part)
    
    # Анализируем результат на основе китайских и латинских частей
    result = None
    
    # Если есть китайские части, обрабатываем их в первую очередь
    if hanzi_parts:
        for part in hanzi_parts:
            if is_chinese_name(part):
                result = split_chinese_name(part)
                if result:
                    break
    
    # Если обработка китайских частей не удалась, пробуем латинские части
    if not result and latin_parts:
        # Пытаемся обработать как транслитерацию
        transliterated_name = " ".join(latin_parts)
        result = identify_transliterated_chinese_name(transliterated_name)
    
    # Если все еще не удалось, пробуем смешанную обработку
    if not result:
        # Извлекаем возможную фамилию
        surname = None
        firstname = ""
        
        # Проверяем, содержат ли китайские части известные фамилии
        for part in hanzi_parts:
            if part in CHINESE_SURNAMES or part[0] in CHINESE_SURNAMES:
                surname = part if part in CHINESE_SURNAMES else part[0]
                break
        
        # Если фамилия найдена, остальные части - имя
        if surname:
            # Собираем все не-фамильные части как имя
            remainder_parts = []
            for part in hanzi_parts + latin_parts:
                if part != surname and not part.startswith(surname):
                    remainder_parts.append(part)
            
            firstname = " ".join(remainder_parts)
            result = (surname, firstname, "")
        
        # Если не удалось найти фамилию, используем эвристический подход
        if not result:
            # Предположим, что первая часть - фамилия
            if hanzi_parts:
                surname = hanzi_parts[0]
                firstname = " ".join(hanzi_parts[1:] + latin_parts)
            else:
                surname = latin_parts[0]
                firstname = " ".join(latin_parts[1:])
            
            result = (surname, firstname, "")
    
    return result

def generate_possible_hanzi_combinations(name):
    """
    Генерация возможных комбинаций китайских иероглифов из транслитерированного имени
    
    :param str name: Транслитерированное имя
    :return: Список возможных комбинаций китайских иероглифов
    :rtype: list
    """
    # Этот метод требует предварительной обработки имени
    # и сопоставления с базой данных или словарем распространенных имен
    
    # Пример простой реализации:
    possible_combinations = []
    
    # Разделяем имя на части (предполагаем пробел как разделитель)
    parts = name.split()
    
    # Перебираем все возможные комбинации иероглифов
    for i in range(1, len(parts) + 1):
        for combination in itertools.combinations(parts, i):
            possible_combinations.append(' '.join(combination))
    
    return possible_combinations

# Распознавание и обработка японских кандзи
def detect_japanese_kanji(text):
    """
    Определение наличия японских кандзи (японских иероглифов) в тексте
    
    :param str text: Входной текст
    :return: Содержит ли текст специфические японские кандзи
    :rtype: bool
    """
    # Диапазоны японских кандзи
    JAPANESE_KANJI_RANGES = [
        (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
        (0x4E00, 0x9FFF),   # CJK Unified Ideographs
        (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
        (0x20000, 0x2A6DF), # CJK Unified Ideographs Extension B
        (0x2A700, 0x2B73F), # CJK Unified Ideographs Extension C
        (0x2B740, 0x2B81F), # CJK Unified Ideographs Extension D
        (0x2F800, 0x2FA1F)  # CJK Compatibility Ideographs Supplement
    ]
    
    # Характерные японские символы
    JAPANESE_SPECIFIC_CHARS = [
        '々', '〆', 'ヶ',  # Специальные японские символы
        '橋', '働', '総', '経',  # Характерные японские формы иероглифов
        'の', 'は', 'を', 'が'  # Японские каны
    ]
    
    # Проверка характерных японских символов
    for char in text:
        if char in JAPANESE_SPECIFIC_CHARS:
            return True
    
    # Проверка наличия каны (японской хираганы и катаканы)
    HIRAGANA_RANGE = (0x3040, 0x309F)
    KATAKANA_RANGE = (0x30A0, 0x30FF)
    
    for char in text:
        code = ord(char)
        if (HIRAGANA_RANGE[0] <= code <= HIRAGANA_RANGE[1] or
            KATAKANA_RANGE[0] <= code <= KATAKANA_RANGE[1]):
            return True
    
    return False

# Алгоритмы нечеткого сопоставления
def fuzzy_match_chinese_name(query, candidates, threshold=0.7):
    """
    Использование алгоритма нечеткого сопоставления для поиска наиболее подходящего китайского имени
    
    :param str query: Искомое имя
    :param list candidates: Список имен-кандидатов
    :param float threshold: Порог соответствия (0.0-1.0)
    :return: Наилучшее соответствие и его оценка
    :rtype: tuple
    """
    if not query or not candidates:
        return None, 0.0
    
    best_match = None
    best_score = 0.0
    
    # Получение пиньиня для запроса (если это китайский)
    query_pinyin = None
    if any(is_chinese_char(c) for c in query):
        if is_chinese_name(query):
            query_pinyin = hanzi_to_pinyin(query)
    else:
        query_pinyin = query.lower()  # Предполагаем, что не-китайский запрос уже в форме пиньинь
    
    for candidate in candidates:
        # Прямое сравнение
        if query == candidate:
            return candidate, 1.0
        
        # Вычисление оценки сходства
        score = 0.0
        
        # Если есть пиньинь, сравниваем сходство по пиньиню
        if query_pinyin:
            candidate_pinyin = None
            if is_chinese_name(candidate):
                candidate_pinyin = hanzi_to_pinyin(candidate)
            elif not any(is_chinese_char(c) for c in candidate):
                candidate_pinyin = candidate.lower()
            
            if candidate_pinyin:
                # Вычисление расстояния Левенштейна для пиньиня
                score = calculate_similarity(query_pinyin, candidate_pinyin)
        else:
            # Прямое вычисление сходства символов
            score = calculate_similarity(query, candidate)
        
        # Обновление лучшего соответствия
        if score > best_score:
            best_score = score
            best_match = candidate
    
    # Если лучшая оценка превышает порог, возвращаем соответствие
    if best_score >= threshold:
        return best_match, best_score
    
    return None, 0.0

def calculate_similarity(s1, s2):
    """
    Вычисление сходства между двумя строками (на основе расстояния Левенштейна)
    
    :param str s1: Первая строка
    :param str s2: Вторая строка
    :return: Оценка сходства (0.0-1.0)
    :rtype: float
    """
    # Реализация расстояния Левенштейна
    def levenshtein(a, b):
        if not a: return len(b)
        if not b: return len(a)
        
        # Инициализация матрицы
        matrix = [[0 for _ in range(len(b) + 1)] for _ in range(len(a) + 1)]
        
        # Заполнение матрицы
        for i in range(len(a) + 1):
            matrix[i][0] = i
        for j in range(len(b) + 1):
            matrix[0][j] = j
        
        for i in range(1, len(a) + 1):
            for j in range(1, len(b) + 1):
                cost = 0 if a[i-1] == b[j-1] else 1
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # Удаление
                    matrix[i][j-1] + 1,      # Вставка
                    matrix[i-1][j-1] + cost  # Замена
                )
        
        return matrix[len(a)][len(b)]
    
    # Вычисление расстояния Левенштейна
    distance = levenshtein(s1, s2)
    
    # Вычисление максимально возможного расстояния
    max_len = max(len(s1), len(s2))
    
    # Если обе строки пустые, возвращаем 1.0
    if max_len == 0:
        return 1.0
    
    # Возвращаем оценку сходства (1.0 означает полное совпадение)
    return 1.0 - (distance / max_len)

# Улучшенная функция split_authors с поддержкой новых возможностей
def split_authors(authors_string): # pylint: disable=too-many-branches
    """
    Разделить строку, содержащую список авторов, на отдельных авторов и 
    распределить фамилии, имена и отчества/инициалы/отчества

    :param str authors_string: Строка с авторами, разделенная запятыми или точками с запятой
    :return: Список кортежей из фамилии, имени и отчества (и др.) каждого автора
    :rtype: list
    """
    res = []
    authors = split_authors_string(authors_string)
    for i, author in enumerate(authors, start=1):
        # Проверяем "et al."
        if author in ('et al.', 'и др.', 'et al', 'и др', 'et al.,', 'и др.,', '等'):
            res.append((author, '', ''))
            continue
            
        # 1. Первым делом проверяем, является ли имя китайским
        if is_chinese_name(author):
            surname, firstname, middlename = split_chinese_name(author)
            res.append((surname, firstname, middlename))
            continue
        
        # 2. Проверяем, является ли имя транслитерированным китайским именем
        chinese_transliterated = identify_transliterated_chinese_name(author)
        if chinese_transliterated:
            res.append(chinese_transliterated)
            continue
        
        # 3. Проверяем, является ли имя этническим китайским именем
        ethnic_name = process_ethnic_name(author)
        if ethnic_name:
            res.append(ethnic_name)
            continue
            
        # 4. Обработка смешанных китайско-латинских имен
        if any(is_chinese_char(c) for c in author):
            mixed_result = handle_mixed_script_name(author)
            if mixed_result:
                res.append(mixed_result)
                continue
                
        # 5. Определяем порядок китайских имен (если есть)
        # В случае, если имя не было распознано как китайское, но содержит китайские символы
        if any(is_chinese_char(c) for c in author):
            # Пытаемся обработать как редкую китайскую фамилию
            rare_result = handle_rare_surname(author)
            if rare_result:
                res.append(rare_result)
                continue
        
        # Если не китайское имя, используем стандартный алгоритм
        order = "western"
        if i <= min(3, len(authors)):
            author = author.replace('.', '. ')
            parts = [p for p in SEP_RE.split(author) if p]
            # Попытка определить порядок имен
            if parts and parts[0] in CHINESE_SURNAMES:
                order = "chinese"
                
        result = parse_author_name(author, order)
        res.append(result)
            
    # Обработка случая, когда только один автор и имя автора не удалось корректно разделить
    if len(res) == 1 and res[0][1] == '':
        author = authors[0]
        # Ищем известные шаблоны
        match = LASTNAME_WITH_PREFIX_RE.search(author)
        if match:
            lastname = match.group(1)
            firstname = author.replace(lastname, '').strip()
            # Удаляем возможные разделители
            firstname = re.sub(r'^[,;\s]+|[,;\s]+$', '', firstname)
            if firstname:
                return [(lastname, firstname, '')]
        # Проверяем, может ли имя быть обработано одной из новых функций
        for process_func in [handle_mixed_script_name, handle_rare_surname]:
            result = process_func(author)
            if result and result[1]:  # Проверяем, что имя не пустое
                return [result]
    
    return res

# Словарь распространенных полных китайских имен
COMMON_CHINESE_FULL_NAMES = {
    '李明': {'surname': '李', 'given_name': '明'},
    '王小红': {'surname': '王', 'given_name': '小红'},
    '张三': {'surname': '张', 'given_name': '三'},
    '欧阳修': {'surname': '欧阳', 'given_name': '修'},
    '司马光': {'surname': '司马', 'given_name': '光'},
    '诸葛亮': {'surname': '诸葛', 'given_name': '亮'},
    '李白': {'surname': '李', 'given_name': '白'},
    '杜甫': {'surname': '杜', 'given_name': '甫'},
    '王维': {'surname': '王', 'given_name': '维'},
    '陈独秀': {'surname': '陈', 'given_name': '独秀'}
}



