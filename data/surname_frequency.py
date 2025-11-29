# -*- coding: utf-8 -*-
"""
中文姓氏频率数据 / Chinese Surname Frequency Data
基于2020年中国人口普查数据 / Based on 2020 China Census Data

用于姓氏消歧和顺序判断 / For surname disambiguation and order detection
"""

# 中文姓氏频率排名（Top 100）/ Chinese Surname Frequency Ranking (Top 100)
# 数据来源：2020年中国人口普查 / Source: 2020 China Census
# 格式：{拼音: 排名} / Format: {pinyin: rank}
SURNAME_FREQUENCY_RANK = {
    'wang': 1,      # 王
    'li': 2,        # 李
    'zhang': 3,     # 张
    'liu': 4,       # 刘
    'chen': 5,      # 陈
    'yang': 6,      # 杨
    'huang': 7,     # 黄
    'zhao': 8,      # 赵
    'wu': 9,        # 吴
    'zhou': 10,     # 周
    'xu': 11,       # 徐
    'sun': 12,      # 孙
    'ma': 13,       # 马
    'zhu': 14,      # 朱
    'hu': 15,       # 胡
    'guo': 16,      # 郭
    'he': 17,       # 何
    'gao': 18,      # 高
    'lin': 19,      # 林
    'luo': 20,      # 罗
    'zheng': 21,    # 郑
    'liang': 22,    # 梁
    'xie': 23,      # 谢
    'song': 24,     # 宋
    'tang': 25,     # 唐
    'xu': 26,       # 许
    'deng': 27,     # 邓
    'han': 28,      # 韩
    'feng': 29,     # 冯
    'cao': 30,      # 曹
    'peng': 31,     # 彭
    'zeng': 32,     # 曾
    'xiao': 33,     # 肖
    'tian': 34,     # 田
    'dong': 35,     # 董
    'pan': 36,      # 潘
    'yuan': 37,     # 袁
    'cai': 38,      # 蔡
    'jiang': 39,    # 蒋
    'yu': 40,       # 余
    'du': 41,       # 杜
    'ye': 42,       # 叶
    'cheng': 43,    # 程
    'wei': 44,      # 魏
    'su': 45,       # 苏
    'lu': 46,       # 卢
    'ding': 47,     # 丁
    'ren': 48,      # 任
    'shen': 49,     # 沈
    'yao': 50,      # 姚
    'lu': 51,       # 陆
    'jiang': 52,    # 姜
    'cui': 53,      # 崔
    'tan': 54,      # 谭
    'liao': 55,     # 廖
    'fan': 56,      # 范
    'wang': 57,     # 汪
    'shi': 58,      # 石
    'jin': 59,      # 金
    'wei': 60,      # 韦
    'jia': 61,      # 贾
    'xia': 62,      # 夏
    'fu': 63,       # 傅
    'fang': 64,     # 方
    'zou': 65,      # 邹
    'xiong': 66,    # 熊
    'bai': 67,      # 白
    'meng': 68,     # 孟
    'qin': 69,      # 秦
    'qiu': 70,      # 邱
    'hou': 71,      # 侯
    'jiang': 72,    # 江
    'yin': 73,      # 尹
    'xue': 74,      # 薛
    'yan': 75,      # 阎
    'duan': 76,     # 段
    'lei': 77,      # 雷
    'long': 78,     # 龙
    'li': 79,       # 黎
    'shi': 80,      # 史
    'tao': 81,      # 陶
    'he': 82,       # 贺
    'gu': 83,       # 顾
    'mao': 84,      # 毛
    'hao': 85,      # 郝
    'gong': 86,     # 龚
    'shao': 87,     # 邵
    'wan': 88,      # 万
    'qian': 89,     # 钱
    'yan': 90,      # 严
    'fu': 91,       # 覃
    'wu': 92,       # 武
    'dai': 93,      # 戴
    'mo': 94,       # 莫
    'kong': 95,     # 孔
    'xiang': 96,    # 向
    'chang': 97,    # 常
}


def get_surname_frequency_rank(surname_pinyin: str) -> int:
    """
    获取姓氏频率排名 / Get surname frequency rank

    Args:
        surname_pinyin: 姓氏拼音 / Surname pinyin (lowercase)

    Returns:
        int: 排名（1-100），如果不在Top 100则返回999 / Rank (1-100), returns 999 if not in Top 100
    """
    surname_lower = surname_pinyin.lower().strip()
    return SURNAME_FREQUENCY_RANK.get(surname_lower, 999)


def compare_surname_frequency(surname1: str, surname2: str) -> dict:
    """
    比较两个姓氏的频率 / Compare frequency of two surnames

    用于处理双姓氏歧义情况，如"Li Wei"中Li和Wei都可能是姓氏
    For handling dual-surname ambiguity, e.g., both Li and Wei could be surnames in "Li Wei"

    Args:
        surname1: 第一个姓氏拼音 / First surname pinyin
        surname2: 第二个姓氏拼音 / Second surname pinyin

    Returns:
        dict: {
            'more_common': str,     # 更常见的姓氏 / More common surname
            'rank1': int,           # 姓氏1排名 / Rank of surname1
            'rank2': int,           # 姓氏2排名 / Rank of surname2
            'rank_diff': int,       # 排名差异 / Rank difference
            'confidence': float     # 置信度 (0.0-1.0) / Confidence
        }
    """
    rank1 = get_surname_frequency_rank(surname1)
    rank2 = get_surname_frequency_rank(surname2)

    # 计算排名差异 / Calculate rank difference
    rank_diff = abs(rank1 - rank2)

    # 确定更常见的姓氏 / Determine more common surname
    if rank1 < rank2:
        more_common = surname1.lower()
    elif rank2 < rank1:
        more_common = surname2.lower()
    else:
        more_common = None  # 相同频率 / Same frequency

    # 计算置信度 / Calculate confidence
    # 排名差异越大，置信度越高 / Larger rank difference → higher confidence
    if rank_diff == 0:
        confidence = 0.0
    elif rank_diff >= 50:
        confidence = 0.9
    elif rank_diff >= 30:
        confidence = 0.8
    elif rank_diff >= 20:
        confidence = 0.7
    elif rank_diff >= 10:
        confidence = 0.6
    else:
        confidence = 0.4

    return {
        'more_common': more_common,
        'rank1': rank1,
        'rank2': rank2,
        'rank_diff': rank_diff,
        'confidence': confidence
    }


# 测试 / Test
if __name__ == '__main__':
    print("中文姓氏频率测试 / Chinese Surname Frequency Test")
    print("=" * 60)

    # 测试单个姓氏排名 / Test individual surname rank
    test_surnames = ['wang', 'li', 'zhang', 'zhao', 'unknown']
    print("\n姓氏频率排名 / Surname Frequency Rank:")
    for surname in test_surnames:
        rank = get_surname_frequency_rank(surname)
        print(f"  {surname}: {rank}")

    # 测试姓氏频率比较 / Test surname frequency comparison
    print("\n姓氏频率比较 / Surname Frequency Comparison:")
    comparisons = [
        ('li', 'wei'),      # 李(2) vs 魏(44)
        ('wang', 'li'),     # 王(1) vs 李(2)
        ('zhang', 'liu'),   # 张(3) vs 刘(4)
    ]

    for s1, s2 in comparisons:
        result = compare_surname_frequency(s1, s2)
        print(f"\n  {s1} vs {s2}:")
        print(f"    More common: {result['more_common']}")
        print(f"    Ranks: {result['rank1']} vs {result['rank2']}")
        print(f"    Rank difference: {result['rank_diff']}")
        print(f"    Confidence: {result['confidence']:.2f}")
