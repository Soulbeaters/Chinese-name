# -*- coding: utf-8 -*-
"""
中国学术机构关键词数据库
Chinese Academic Institution Keywords Database

用途 / Назначение:
识别机构信息中的中国学术单位，用于姓氏位置判断
Identify Chinese academic institutions in affiliation strings for surname position inference

中文注释：完整的中国机构关键词库
Русский комментарий: Полная база ключевых слов китайских учреждений
"""

# 顶尖大学（C9联盟 + 双一流）/ Ведущие университеты (C9 League + Double First-Class)
TOP_UNIVERSITIES = {
    # C9联盟 / C9 League
    'tsinghua', 'tsinghua university', 'qinghua',
    'peking university', 'pku', 'beijing university', 'beida',
    'fudan', 'fudan university',
    'shanghai jiao tong', 'shanghai jiaotong', 'sjtu',
    'zhejiang university', 'zju',
    'nanjing university', 'nju',
    'university of science and technology of china', 'ustc', 'zhongkeda',
    'harbin institute of technology', 'harbin institute', 'hit',
    'xi\'an jiaotong', 'xjtu', 'xi\'an jiao tong',

    # 其他985/211大学 / Другие университеты 985/211
    'beihang', 'buaa', 'beijing university of aeronautics',
    'beijing normal', 'bnu',
    'beijing institute of technology', 'bit',
    'renmin university', 'ruc', 'people\'s university',
    'nankai', 'nankai university',
    'tianjin university', 'tju',
    'huazhong university of science and technology', 'hust',
    'wuhan university', 'whu',
    'sun yat-sen', 'zhongshan university', 'sysu',
    'south china university of technology', 'scut',
    'xiamen university', 'xmu',
    'shandong university', 'sdu',
    'jilin university', 'jlu',
    'sichuan university', 'scu',
    'tongji', 'tongji university',
    'southeast university', 'seu',
    'dalian university of technology', 'dlut',
    'chongqing university', 'cqu',
    'lanzhou university', 'lzu',
    'northeastern university', 'neu', 'dongbei',
    'northwestern polytechnical', 'nwpu',
    'central south university', 'csu',
    'hunan university', 'hnu',
    'suzhou university', 'soochow',
}

# 科研机构 / Научно-исследовательские институты
RESEARCH_INSTITUTES = {
    'chinese academy of sciences', 'cas',
    'chinese academy of engineering', 'cae',
    'china institute of atomic energy', 'ciae',
    'institute of physics', 'iop',
    'institute of chemistry', 'iccas',
    'institute of computing technology', 'ict',
    'institute of automation cas', 'ia cas',  # 更精确匹配，避免误匹配"california"
    'institute of biophysics', 'ibp',
    'shanghai institute',
    'beijing institute',
    'guangzhou institute',
    'shenzhen institute',
}

# 省份和城市（主要科研城市）/ Провинции и города (основные научные центры)
CITIES_AND_PROVINCES = {
    # 直辖市 / Города центрального подчинения
    'beijing', 'peking',
    'shanghai',
    'tianjin',
    'chongqing',

    # 主要科研城市 / Основные научные города
    'nanjing', 'nanking',
    'hangzhou',
    'wuhan',
    'xi\'an', 'xian',
    'chengdu',
    'guangzhou', 'canton',
    'shenzhen',
    'suzhou',
    'hefei',
    'changsha',
    'harbin',
    'dalian',
    'qingdao',
    'jinan',
    'zhengzhou',
    'kunming',
    'lanzhou',
    'urumqi',

    # 省份 / Провинции
    'guangdong', 'canton',
    'jiangsu',
    'zhejiang',
    'shandong',
    'sichuan',
    'hubei',
    'hunan',
    'shaanxi', 'shanxi',
    'heilongjiang',
    'liaoning',
    'anhui',
    'fujian',
    'yunnan',
    'gansu',
}

# 国家标识 / Национальные идентификаторы
COUNTRY_IDENTIFIERS = {
    'china', 'chinese',
    'p.r. china', 'pr china',
    'people\'s republic of china',
    'prc',
    'mainland china',
    'p. r. china',
}

# 医院和医学院 / Больницы и медицинские институты
MEDICAL_INSTITUTIONS = {
    'peking union medical college', 'pumc',
    'capital medical university',
    'china medical university',
    'southern medical university',
    'shanghai medical',
    'beijing hospital',
    'chinese people\'s liberation army',
    'pla hospital',
}

# 理工类院校 / Технические институты
TECH_UNIVERSITIES = {
    'beijing institute of technology',
    'harbin engineering university',
    'nanjing university of aeronautics',
    'beijing university of posts and telecommunications',
    'xidian university',
    'beijing jiaotong university',
}

# 师范类院校 / Педагогические университеты
NORMAL_UNIVERSITIES = {
    'beijing normal university',
    'east china normal university', 'ecnu',
    'northeast normal university',
    'central china normal university',
    'south china normal university',
    'shaanxi normal university',
}

# 农林类院校 / Сельскохозяйственные и лесные университеты
AGRICULTURAL_UNIVERSITIES = {
    'china agricultural university', 'cau',
    'nanjing agricultural university',
    'northwest agriculture and forestry',
}

# 合并所有关键词 / Объединение всех ключевых слов
ALL_CHINESE_INSTITUTION_KEYWORDS = (
    TOP_UNIVERSITIES |
    RESEARCH_INSTITUTES |
    CITIES_AND_PROVINCES |
    COUNTRY_IDENTIFIERS |
    MEDICAL_INSTITUTIONS |
    TECH_UNIVERSITIES |
    NORMAL_UNIVERSITIES |
    AGRICULTURAL_UNIVERSITIES
)

# 转换为排序列表（便于调试）/ Преобразование в отсортированный список (для отладки)
ALL_KEYWORDS_LIST = sorted(ALL_CHINESE_INSTITUTION_KEYWORDS)


def is_chinese_institution(affiliation: str) -> bool:
    """
    判断是否为中国机构 / Проверка, является ли учреждением Китая
    Check if an affiliation string indicates a Chinese institution

    Args:
        affiliation: 机构信息字符串 / Строка с информацией об учреждении

    Returns:
        bool: 是否为中国机构 / Является ли китайским учреждением

    Examples:
        >>> is_chinese_institution("Tsinghua University, Beijing, China")
        True
        >>> is_chinese_institution("Harvard University, USA")
        False
        >>> is_chinese_institution("Shanghai Jiao Tong University")
        True
    """
    if not affiliation:
        return False

    affiliation_lower = affiliation.lower()

    return any(keyword in affiliation_lower for keyword in ALL_CHINESE_INSTITUTION_KEYWORDS)


def get_matched_keywords(affiliation: str) -> list:
    """
    获取匹配的关键词列表 / Получение списка совпавших ключевых слов
    Get list of matched keywords from an affiliation string

    Args:
        affiliation: 机构信息字符串

    Returns:
        list: 匹配的关键词列表

    Examples:
        >>> get_matched_keywords("Tsinghua University, Beijing, China")
        ['beijing', 'china', 'chinese', 'tsinghua', 'tsinghua university']
    """
    if not affiliation:
        return []

    affiliation_lower = affiliation.lower()

    matched = [kw for kw in ALL_CHINESE_INSTITUTION_KEYWORDS if kw in affiliation_lower]
    return sorted(matched)


def get_institution_confidence(affiliation: str) -> float:
    """
    计算机构置信度（基于匹配关键词数量和质量）
    Вычисление уровня уверенности (на основе количества и качества совпавших ключевых слов)
    Calculate confidence score based on number and quality of matched keywords

    Args:
        affiliation: 机构信息字符串

    Returns:
        float: 置信度 (0.0-1.0)

    Confidence levels:
        0.90-1.00: 匹配顶尖大学 / Совпадение с ведущим университетом
        0.75-0.90: 匹配多个关键词 / Совпадение с несколькими ключевыми словами
        0.60-0.75: 仅匹配国家标识 / Совпадение только с национальным идентификатором
    """
    if not affiliation:
        return 0.0

    matched = get_matched_keywords(affiliation)

    if not matched:
        return 0.0

    # 检查是否匹配顶尖大学 / Проверка совпадения с ведущим университетом
    if any(kw in TOP_UNIVERSITIES for kw in matched):
        return 0.90

    # 检查是否匹配科研机构 / Проверка совпадения с НИИ
    if any(kw in RESEARCH_INSTITUTES for kw in matched):
        return 0.85

    # 多个关键词匹配 / Несколько совпадений
    if len(matched) >= 3:
        return 0.80

    if len(matched) == 2:
        return 0.75

    # 仅匹配国家标识 / Только национальный идентификатор
    if all(kw in COUNTRY_IDENTIFIERS for kw in matched):
        return 0.65

    # 单一关键词 / Одно ключевое слово
    return 0.70


if __name__ == '__main__':
    print("=" * 80)
    print("中国机构关键词数据库 / Chinese Institution Keywords Database")
    print("=" * 80)

    print(f"\n总关键词数 / Total keywords: {len(ALL_CHINESE_INSTITUTION_KEYWORDS)}")

    print(f"\n分类统计 / Category statistics:")
    print(f"  顶尖大学 / Top universities: {len(TOP_UNIVERSITIES)}")
    print(f"  科研机构 / Research institutes: {len(RESEARCH_INSTITUTES)}")
    print(f"  城市省份 / Cities & provinces: {len(CITIES_AND_PROVINCES)}")
    print(f"  国家标识 / Country identifiers: {len(COUNTRY_IDENTIFIERS)}")
    print(f"  医学机构 / Medical institutions: {len(MEDICAL_INSTITUTIONS)}")
    print(f"  理工院校 / Tech universities: {len(TECH_UNIVERSITIES)}")
    print(f"  师范院校 / Normal universities: {len(NORMAL_UNIVERSITIES)}")
    print(f"  农林院校 / Agricultural universities: {len(AGRICULTURAL_UNIVERSITIES)}")

    # 测试案例 / Тестовые случаи
    print(f"\n测试案例 / Test cases:")
    print("-" * 80)

    test_cases = [
        "Tsinghua University, Beijing, China",
        "Department of Computer Science, Peking University",
        "Chinese Academy of Sciences, Shanghai Institute of Technical Physics",
        "Harvard University, Cambridge, MA, USA",
        "University of California, Berkeley",
        "Shanghai Jiao Tong University",
        "Zhejiang University, Hangzhou",
        "Unknown University, China"
    ]

    for affiliation in test_cases:
        is_cn = is_chinese_institution(affiliation)
        matched = get_matched_keywords(affiliation)
        confidence = get_institution_confidence(affiliation)

        print(f"\n  {affiliation}")
        print(f"    是否中国机构 / Is Chinese: {is_cn}")
        print(f"    匹配关键词 / Matched: {matched}")
        print(f"    置信度 / Confidence: {confidence:.2f}")

    print("\n" + "=" * 80)
    print(f"完成 / Complete")
    print("=" * 80)
