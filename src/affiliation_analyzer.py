# -*- coding: utf-8 -*-
"""
机构信息分析器 / Affiliation Analyzer
用于v7.0算法判断作者机构是否为中国机构

作者 / Author: Ma Jiaxin
日期 / Date: 2025-11-28
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class AffiliationInfo:
    """机构信息 / Affiliation Information"""
    is_chinese: bool = False
    country: Optional[str] = None
    confidence: float = 0.0


# 中国机构关键词
CHINESE_KEYWORDS = {
    # 国家名
    'china', 'p.r. china', 'p. r. china', 'peoples republic of china',
    'people\'s republic of china', '中国', '中华人民共和国',

    # 城市（拼音）
    'beijing', 'shanghai', 'guangzhou', 'shenzhen', 'hangzhou', 'nanjing',
    'wuhan', 'chengdu', 'xi\'an', 'xian', 'tianjin', 'chongqing', 'suzhou',
    'changsha', 'harbin', 'dalian', 'qingdao', 'jinan', 'zhengzhou', 'hefei',

    # 城市（中文）
    '北京', '上海', '广州', '深圳', '杭州', '南京', '武汉', '成都',
    '西安', '天津', '重庆', '苏州', '长沙', '哈尔滨', '大连', '青岛',

    # 省份（拼音）
    'sichuan', 'zhejiang', 'jiangsu', 'guangdong', 'shandong', 'henan',
    'hubei', 'hunan', 'anhui', 'fujian', 'liaoning', 'heilongjiang',
    'shaanxi', 'yunnan', 'guizhou', 'jiangxi', 'shanxi',

    # 省份（中文）
    '四川', '浙江', '江苏', '广东', '山东', '河南', '湖北', '湖南',
    '安徽', '福建', '辽宁', '黑龙江', '陕西', '云南', '贵州', '江西',

    # 著名大学（英文）
    'tsinghua', 'peking university', 'peking univ', 'pku',
    'fudan', 'zhejiang university', 'zju',
    'shanghai jiao tong', 'sjtu', 'shanghai jiaotong',
    'nanjing university', 'nju',
    'university of science and technology of china', 'ustc',
    'harbin institute of technology', 'hit',
    'xi\'an jiaotong', 'xjtu', 'xian jiaotong',
    'beihang', 'buaa',
    'tongji', 'renmin', 'nankai', 'tianjin university',
    'wuhan university', 'whu',
    'sichuan university', 'scu',
    'sun yat-sen', 'sysu',
    'huazhong',

    # 著名大学（中文）
    '清华', '北大', '复旦', '浙大', '上海交通', '交大', '南京大学',
    '中国科学技术大学', '中科大', '哈工大', '西安交通', '北航',
    '同济', '人大', '南开', '天津大学', '武汉大学', '武大',

    # 研究院所
    'chinese academy of sciences', 'cas', '中国科学院', '中科院',
    'academy of sciences',
}

# 非中国国家关键词
NON_CHINESE_COUNTRIES = {
    'usa', 'united states', 'u.s.a', 'america',
    'uk', 'united kingdom', 'england', 'scotland', 'wales',
    'germany', 'deutschland',
    'france',
    'japan', 'tokyo', 'osaka', 'kyoto',
    'korea', 'seoul', 'south korea',
    'canada', 'toronto', 'montreal', 'vancouver',
    'australia', 'sydney', 'melbourne',
    'italy', 'rome', 'milan',
    'spain', 'madrid', 'barcelona',
    'russia', 'moscow',
    'netherlands', 'amsterdam',
    'sweden', 'stockholm',
    'switzerland', 'zurich',
    'singapore',
    'india', 'delhi', 'mumbai',
    'brazil', 'sao paulo',
}


def analyze_affiliation(affiliation: str) -> Optional[AffiliationInfo]:
    """
    分析机构信息，判断是否为中国机构

    Args:
        affiliation: 机构字符串

    Returns:
        AffiliationInfo or None
    """
    if not affiliation or not isinstance(affiliation, str):
        return None

    affil_lower = affiliation.lower().strip()

    if not affil_lower:
        return None

    # 检查中国关键词
    chinese_matches = 0
    for keyword in CHINESE_KEYWORDS:
        if keyword in affil_lower:
            chinese_matches += 1

    # 检查非中国国家关键词
    non_chinese_matches = 0
    matched_country = None
    for keyword in NON_CHINESE_COUNTRIES:
        if keyword in affil_lower:
            non_chinese_matches += 1
            if not matched_country:
                matched_country = keyword

    # 决策
    if chinese_matches > 0 and non_chinese_matches == 0:
        # 只有中国关键词 → 中国机构
        confidence = min(0.3 + chinese_matches * 0.1, 0.9)
        return AffiliationInfo(is_chinese=True, country='China', confidence=confidence)

    elif non_chinese_matches > 0 and chinese_matches == 0:
        # 只有非中国关键词 → 非中国机构
        confidence = min(0.3 + non_chinese_matches * 0.1, 0.9)
        return AffiliationInfo(is_chinese=False, country=matched_country, confidence=confidence)

    elif chinese_matches > non_chinese_matches:
        # 中国关键词更多 → 中国机构（可能性大）
        confidence = 0.6
        return AffiliationInfo(is_chinese=True, country='China', confidence=confidence)

    elif non_chinese_matches > chinese_matches:
        # 非中国关键词更多 → 非中国机构
        confidence = 0.6
        return AffiliationInfo(is_chinese=False, country=matched_country, confidence=confidence)

    else:
        # 无法判断
        return None


# 测试
if __name__ == '__main__':
    test_cases = [
        "Tsinghua University, Beijing, China",
        "Department of Physics, MIT, Cambridge, MA, USA",
        "Jilin University, Changchun, China",
        "University of Helsinki, Finland",
        "",
        None,
    ]

    for affil in test_cases:
        result = analyze_affiliation(affil)
        print(f"Affiliation: {affil}")
        if result:
            print(f"  Is Chinese: {result.is_chinese}, Country: {result.country}, Conf: {result.confidence:.2f}")
        else:
            print(f"  Result: None")
        print()
