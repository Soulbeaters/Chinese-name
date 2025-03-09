# -*- coding: utf-8 -*-
import itertools
import logging
import re
import json
import os
from pathlib import Path

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
    '李': {'pinyin': 'Li', 'palladius': 'Ли'},
    '王': {'pinyin': 'Wang', 'palladius': 'Ван'},
    '张': {'pinyin': 'Zhang', 'palladius': 'Чжан'},
    '刘': {'pinyin': 'Liu', 'palladius': 'Лю'},
    '陈': {'pinyin': 'Chen', 'palladius': 'Чэнь'},
    '杨': {'pinyin': 'Yang', 'palladius': 'Ян'},
    '黄': {'pinyin': 'Huang', 'palladius': 'Хуан'},
    '赵': {'pinyin': 'Zhao', 'palladius': 'Чжао'},
    '吴': {'pinyin': 'Wu', 'palladius': 'У'},
    '周': {'pinyin': 'Zhou', 'palladius': 'Чжоу'},
    '徐': {'pinyin': 'Xu', 'palladius': 'Сюй'},
    '孙': {'pinyin': 'Sun', 'palladius': 'Сунь'},
    '马': {'pinyin': 'Ma', 'palladius': 'Ма'},
    '朱': {'pinyin': 'Zhu', 'palladius': 'Чжу'},
    '胡': {'pinyin': 'Hu', 'palladius': 'Ху'},
    '郭': {'pinyin': 'Guo', 'palladius': 'Го'},
    '何': {'pinyin': 'He', 'palladius': 'Хэ'},
    '高': {'pinyin': 'Gao', 'palladius': 'Гао'},
    '林': {'pinyin': 'Lin', 'palladius': 'Линь'},
    '罗': {'pinyin': 'Luo', 'palladius': 'Ло'},
    
    # Распространенные составные фамилии и их транслитерации
    '欧阳': {'pinyin': 'Ouyang', 'palladius': 'Оуян'},
    '司马': {'pinyin': 'Sima', 'palladius': 'Сыма'},
    '上官': {'pinyin': 'Shangguan', 'palladius': 'Шангуань'},
    '诸葛': {'pinyin': 'Zhuge', 'palladius': 'Чжугэ'},
    '司徒': {'pinyin': 'Situ', 'palladius': 'Сыту'},
    '东方': {'pinyin': 'Dongfang', 'palladius': 'Дунфан'},
    '独孤': {'pinyin': 'Dugu', 'palladius': 'Дугу'},
    '慕容': {'pinyin': 'Murong', 'palladius': 'Мужун'},
    '公孙': {'pinyin': 'Gongsun', 'palladius': 'Гунсунь'},
    '宇文': {'pinyin': 'Yuwen', 'palladius': 'Юйвэнь'},
    '仲孙': {'pinyin': 'Zhongsun', 'palladius': 'Чжунсунь'},
    '司空': {'pinyin': 'Sikong', 'palladius': 'Сыкун'},
    '澹台': {'pinyin': 'Tantai', 'palladius': 'Таньтай'},
    '公冶': {'pinyin': 'Gongye', 'palladius': 'Гунъе'},
    '闻人': {'pinyin': 'Wenren', 'palladius': 'Вэньжэнь'},
}

# Добавление обратного отображения транслитераций пиньинь и системы Палладия
PINYIN_TO_SURNAME = {}
PALLADIUS_TO_SURNAME = {}

# Построение таблиц обратного отображения
for surname, transliterations in CHINESE_SURNAMES.items():
    pinyin = transliterations['pinyin']
    palladius = transliterations['palladius']
    
    if pinyin not in PINYIN_TO_SURNAME:
        PINYIN_TO_SURNAME[pinyin] = []
    PINYIN_TO_SURNAME[pinyin].append(surname)
    
    if palladius not in PALLADIUS_TO_SURNAME:
        PALLADIUS_TO_SURNAME[palladius] = []
    PALLADIUS_TO_SURNAME[palladius].append(surname)


def is_chinese_char(char):
    """
    Определяет, является ли символ китайским иероглифом
    
    :param str char: Один символ
    :return: Является ли символ китайским иероглифом
    :rtype: bool
    """
    return bool(CHINESE_CHAR_RE.match(char))


def is_chinese_name(name):
    """
    Определяет, является ли строка китайским именем (состоит только из китайских иероглифов и имеет длину от 1 до 4)
    
    :param str name: Строка имени
    :return: Является ли строка китайским именем
    :rtype: bool
    """
    return bool(CHINESE_NAME_RE.match(name))


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
    
    # Проверяем, начинается ли с составной фамилии (2 иероглифа)
    if len(name) >= 2:
        for complex_surname in [s for s in CHINESE_SURNAMES.keys() if len(s) > 1]:
            if name.startswith(complex_surname):
                surname = complex_surname
                firstname = name[len(surname):]
                return (surname, firstname, '')
    
    # По умолчанию берем первый иероглиф как фамилию, остальные как имя
    surname = name[0]
    firstname = name[1:] if len(name) > 1 else ''
    
    return (surname, firstname, '')


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
    """Разделяет строку ``authors_string`` в список триплетов. Точки из инициалов удаляются.
    >>> split_authors("I.S.Udvarhelyi")
    [('Udvarhelyi', 'I', 'S')]
    >>> split_authors("Epstein, K P")
    [('Epstein', 'K', 'P')]
    >>> split_authors("Kane E")
    [('Kane', 'E', '')]
    >>> split_authors("D.D. Golomazov et al.")
    [('Golomazov', 'D', 'D'), ('et al.', '', '')]
    >>> split_authors("Monica Olvera de la Cruz")
    [('de la Cruz', 'Monica', 'Olvera')]
    >>> split_authors("Monica Olvera Valdez Marquez Perez")
    [('Valdez Marquez Perez', 'Monica', 'Olvera')]
    >>> split_authors("Elena Belenkaya, Maxim Khodachenko")
    [('Belenkaya', 'Elena', ''), ('Khodachenko', 'Maxim', '')]
    >>> split_authors("Belenkaya E.; Khodachenko M.") # split by semicolon
    [('Belenkaya', 'E', ''), ('Khodachenko', 'M', '')]
    >>> split_authors("李明")
    [('李', '明', '')]
    >>> split_authors("王小红, 张大明")
    [('王', '小红', ''), ('张', '大明', '')]
    >>> split_authors("欧阳修")
    [('欧阳', '修', '')]
    >>> split_authors("Li Ming")
    [('Li', 'Ming', '')]
    >>> split_authors("Ming Li") # западный порядок: имя впереди, фамилия сзади
    [('Li', 'Ming', '')]
    >>> split_authors("Ван Сяохун") # транслитерация по системе Палладия
    [('Ван', 'Сяохун', '')]
    """
    # Проверяем, состоит ли строка полностью из китайских иероглифов (без знаков пунктуации)
    if all(is_chinese_char(c) or c.isspace() for c in authors_string):
        # Для строк, состоящих только из китайских иероглифов, пробуем разделить по пробелам
        if ' ' in authors_string:
            parts = [p.strip() for p in authors_string.split(' ') if p.strip()]
            authors = [split_chinese_name(part) for part in parts]
            return [a for a in authors if a]
    
    # Для смешанных строк или строк не на китайском языке используем существующую логику
    # Разделить authors_string на части
    authors_string_parts, add_et_al = split_authors_string(authors_string)

    # Пробуем идентифицировать каждое имя автора как китайское
    authors = []
    for part in authors_string_parts:
        part = part.strip()
        # Проверяем, является ли это чисто китайским именем
        if is_chinese_name(part):
            chinese_name_parts = split_chinese_name(part)
            if chinese_name_parts:
                authors.append(chinese_name_parts)
                continue
        
        # Проверяем, является ли это транслитерированным китайским именем
        transliterated_result = identify_transliterated_chinese_name(part)
        if transliterated_result:
            authors.append(transliterated_result)
            continue

    # Если не определены китайские имена или определены только частично, обрабатываем оставшуюся часть существующей логикой
    if not authors or len(authors) < len(authors_string_parts):
        # Находим уже обработанные части
        processed_parts = [p.strip() for a in authors for p in authors_string_parts if split_chinese_name(p.strip()) == a or identify_transliterated_chinese_name(p.strip()) == a]
        
        # Обрабатываем необработанные части
        remaining_parts = [p for p in authors_string_parts if p.strip() not in processed_parts]
        
        if remaining_parts:
            # Обрабатываем оставшуюся часть существующей логикой
            # Найти имена авторов в базе имен
            all_names = itertools.chain.from_iterable(SEP_RE.split(names.upper()) for names in remaining_parts)
            names_found = [k for k, v in Firstname.objects.in_bulk(all_names).items() if v.people_count >= 30]

            # Определить порядок имя-фамилия для первого автора отдельно и совокупный для всей группы авторов, кроме первого
            non_increasing = lambda l: all(x >= y for x, y in zip(l, l[1:]))
            non_decreasing = lambda l: all(x <= y for x, y in zip(l, l[1:]))
            name_lastname_order = lambda l: int(non_decreasing(l)) - int(non_increasing(l))

            cumulative_order = 0
            first_order = None

            for fullname in remaining_parts:
                names = [x.upper() for x in SEP_RE.split(fullname) if x]
                non_initial_names = [x for x in names if len(re.sub(W_RE, '', x)) > 1 and not INITIALS_RE.match(x)]
                if not non_initial_names:
                    continue
                if names[0] != non_initial_names[0]:
                    order = -1
                elif len(names) > 1 and len(non_initial_names) > 1 and names[1] != non_initial_names[1]:
                    order = -1
                elif len(non_initial_names) > 3 and all(len(name) > 2 for name in names):
                    order = -1
                else:
                    force_surname = []
                    if len(non_initial_names) == 1:
                        force_surname = non_initial_names[0]
                    elif len(non_initial_names) == len(names) == 3: # Перед отчеством должно идти имя
                        patronym_map = [bool(PATRONYM_SUFFIX_RU.match(name)) for name in names]
                        if sum([int(x) for x in patronym_map]) == 1:
                            if patronym_map[1]:
                                force_surname = names[2]
                            if patronym_map[2]:
                                force_surname = names[0]
                    names_map = [(name in names_found and name not in force_surname) or (len(re.sub(W_RE, '', name)) == 1 or INITIALS_RE.match(name)) for name in names]
                    order = name_lastname_order([bool(firstname) for firstname in names_map])
                if first_order is None:
                    first_order = order
                cumulative_order += order

            # Cчитаем совокупный порядок без первого автора
            if first_order is not None:
                cumulative_order -= first_order
                # Разбить имя каждого автора на тройки
                western_authors = [x for x in [parse_author_name(remaining_parts[0], first_order)] + [parse_author_name(author, cumulative_order) for author in remaining_parts[1:]] if x]
                authors.extend(western_authors)

    # Добавить "и др." обратно, если он был выделен
    if add_et_al:
        authors.append((add_et_al, '', ''))
    return authors


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
