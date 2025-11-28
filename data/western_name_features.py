# -*- coding: utf-8 -*-
"""
西方姓名特征库 / Western Name Features Database
用于v7.0算法识别西方姓氏

作者 / Author: Ma Jiaxin
日期 / Date: 2025-11-28
"""

import re

# 典型西方姓氏后缀
# Typical Western Surname Suffixes
WESTERN_SURNAME_SUFFIXES = {
    # 英语/德语 English/German
    'son', 'sen',  # Johnson, Hansen, Anderson
    'man', 'mann',  # Friedman, Friedemann, Hoffmann
    'berg', 'burg',  # Goldberg, Bloomberg, Hamburg
    'stein', 'stain',  # Einstein, Bernstein
    'feld', 'field',  # Greenfeld, Springfield
    'wood', 'ward',  # Sherwood, Howard
    'land',  # Iceland, Sutherland

    # 斯拉夫语 Slavic
    'ov', 'ova', 'ev', 'eva',  # Ivanov, Smirnova, Medvedev
    'sky', 'ski', 'ska', 'cki',  # Kowalski, Nowak
    'vich', 'vitch', 'vic',  # Petrovich
    'enko', 'ov', 'uk',  # Shevchenko (Ukrainian)

    # 芬兰语 Finnish
    'inen', 'nen',  # Savolainen, Virtanen

    # 法语 French
    'ard', 'chard',  # Desrichard, Bernard
    'eau', 'ault',  # Moreau, Renault
    'ier', 'iere',  # Mercier

    # 意大利语 Italian
    'ini', 'ino',  # Rossini, Valentino
    'elli', 'ello',  # Gabrielli
    'otti', 'otto',  # Mariotti

    # 西班牙语/葡萄牙语 Spanish/Portuguese
    'ez', 'es',  # Rodriguez, Lopez, Fernandes
    'os', 'as',  # Santos, Pereira

    # 其他 Others
    'is', 'os',  # Alexis (希腊 Greek)
    'ian', 'yan',  # Armenian surnames
}

# 西方姓氏中常见的辅音组合（非拼音模式）
# Common consonant clusters in Western names (non-Pinyin patterns)
WESTERN_CONSONANT_PATTERNS = [
    r'sch',  # Schwartz, Schumacher (德语 German)
    r'tsch',  # Deutsch (德语 German)
    r'ck',  # Mick, Patrick
    r'cz',  # Czarnecki (波兰 Polish)
    r'dz',  # Dzhokhar
    r'th',  # Smith, Thatcher (在拼音中th极少)
    r'gh',  # Hugh, Vaughan
    r'ph',  # Stephen, Christopher
    r'gn',  # Giannis (希腊 Greek)
    r'kh',  # Mikhail (俄语 Russian)
    r'shch',  # Shcherbakov (俄语 Russian)
    r'str',  # Strauss
    r'spr',  # Springer
]

# 拉丁扩展字符（非ASCII a-z）
# Latin Extended Characters (non-ASCII a-z)
LATIN_EXTENDED_CHARS = set('äöüñçåøæœéèêëïîàâ')


def has_western_suffix(token: str) -> bool:
    """
    检查token是否有典型西方姓氏后缀

    Args:
        token: 待检查的token（已小写）

    Returns:
        bool: 是否含有西方姓氏后缀
    """
    token_lower = token.lower()

    for suffix in WESTERN_SURNAME_SUFFIXES:
        if token_lower.endswith(suffix):
            # 排除误判：如果后缀前面太短（<2字符），可能是巧合
            if len(token_lower) > len(suffix) + 1:
                return True

    return False


def has_western_consonant_cluster(token: str) -> bool:
    """
    检查token是否含有典型西方辅音组合

    Args:
        token: 待检查的token（已小写）

    Returns:
        bool: 是否含有西方辅音组合
    """
    token_lower = token.lower()

    for pattern in WESTERN_CONSONANT_PATTERNS:
        if re.search(pattern, token_lower):
            return True

    return False


def has_latin_extended_chars(token: str) -> bool:
    """
    检查token是否含有拉丁扩展字符

    Args:
        token: 待检查的token

    Returns:
        bool: 是否含有拉丁扩展字符
    """
    token_lower = token.lower()
    return any(char in LATIN_EXTENDED_CHARS for char in token_lower)


def is_likely_western_name(token: str) -> bool:
    """
    综合判断token是否可能是西方姓名

    Args:
        token: 待检查的token

    Returns:
        bool: 是否可能是西方姓名
    """
    return (
        has_western_suffix(token) or
        has_western_consonant_cluster(token) or
        has_latin_extended_chars(token)
    )


# 从测试数据中提取的高频西方姓氏（Top 3000）
# 这里先放一个小样本，后续可以从Crossref/ORCID数据离线生成
COMMON_WESTERN_SURNAMES = {
    # 英语 English (Top 100)
    'smith', 'johnson', 'williams', 'brown', 'jones', 'miller', 'davis', 'garcia',
    'rodriguez', 'wilson', 'martinez', 'anderson', 'taylor', 'thomas', 'hernandez',
    'moore', 'martin', 'jackson', 'thompson', 'white', 'lopez', 'lee', 'gonzalez',
    'harris', 'clark', 'lewis', 'robinson', 'walker', 'perez', 'hall', 'young',
    'allen', 'sanchez', 'wright', 'king', 'scott', 'green', 'baker', 'adams',
    'nelson', 'hill', 'ramirez', 'campbell', 'mitchell', 'roberts', 'carter',
    'phillips', 'evans', 'turner', 'torres', 'parker', 'collins', 'edwards',
    'stewart', 'flores', 'morris', 'nguyen', 'murphy', 'rivera', 'cook', 'rogers',

    # 德语 German
    'mueller', 'muller', 'schmidt', 'schneider', 'fischer', 'weber', 'meyer',
    'wagner', 'becker', 'schulz', 'hoffmann', 'koch', 'richter', 'klein',
    'wolf', 'schroeder', 'neumann', 'schwartz',

    # 法语 French
    'martin', 'bernard', 'dubois', 'thomas', 'robert', 'richard', 'petit',
    'durand', 'leroy', 'moreau', 'simon', 'laurent', 'lefebvre', 'michel',
    'garcia', 'david', 'bertrand', 'roux', 'vincent', 'fournier', 'morel',

    # 意大利语 Italian
    'rossi', 'russo', 'ferrari', 'esposito', 'bianchi', 'romano', 'colombo',
    'ricci', 'marino', 'greco', 'bruno', 'gallo', 'conti', 'de luca',

    # 西班牙语 Spanish
    'fernandez', 'gonzalez', 'rodriguez', 'lopez', 'martinez', 'sanchez',
    'perez', 'martin', 'gomez', 'ruiz', 'hernandez', 'jimenez', 'diaz',

    # 俄语 Russian
    'ivanov', 'smirnov', 'kuznetsov', 'popov', 'vasiliev', 'petrov', 'sokolov',
    'mikhailov', 'fedorov', 'morozov', 'volkov', 'alekseev', 'lebedev',

    # 波兰语 Polish
    'kowalski', 'wisniewski', 'dabrowski', 'lewandowski', 'wojcik', 'kaminski',
    'kowalczyk', 'zielinski', 'szymanski', 'wozniak',

    # 芬兰语 Finnish
    'korhonen', 'virtanen', 'makinen', 'nieminen', 'makela', 'hamalainen',
    'laine', 'heikkinen', 'koskinen', 'jarvinen',

    # 荷兰语 Dutch
    'jong', 'jansen', 'vries', 'berg', 'dijk', 'bakker', 'janssen', 'visser',
    'smit', 'meijer', 'boer', 'mulder', 'groot', 'bos', 'vos', 'peters',

    # 从错误案例中提取的
    'savolainen', 'desrichard', 'friedemann', 'aberson', 'lukyanenko',
    'rutherford', 'verhoeven', 'santtila', 'mignard', 'adjodah', 'tonello',
    'congedo', 'cillo', 'vatakis', 'marttila',
}


def is_common_western_surname(token: str) -> bool:
    """
    检查token是否是常见西方姓氏

    Args:
        token: 待检查的token（已小写）

    Returns:
        bool: 是否是常见西方姓氏
    """
    return token.lower() in COMMON_WESTERN_SURNAMES


# 导出
__all__ = [
    'WESTERN_SURNAME_SUFFIXES',
    'WESTERN_CONSONANT_PATTERNS',
    'LATIN_EXTENDED_CHARS',
    'COMMON_WESTERN_SURNAMES',
    'has_western_suffix',
    'has_western_consonant_cluster',
    'has_latin_extended_chars',
    'is_likely_western_name',
    'is_common_western_surname',
]
