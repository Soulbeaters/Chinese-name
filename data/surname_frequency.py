# -*- coding: utf-8 -*-
"""
Chinese surname frequency helpers used for surname disambiguation.

This module intentionally keeps two parallel data sources:

1. `SURNAME_FREQUENCY_RANK`
   Legacy rank-based frequency list used by the existing `rank_gap` rule.
   Unknown surnames fall back to rank `999`, preserving baseline behavior.

2. `SURNAME_FREQUENCY_SHARE_RAW`
   The 2013 "400 most common surnames in China" table referenced from:
   https://en.wikipedia.org/wiki/List_of_common_Chinese_surnames
   (Wikipedia cites the Fuxi Institution ranking and reports "% of pop.").

For the share-based rule the algorithm only sees romanized pinyin, not the
underlying Han character. We therefore aggregate same-pinyin surnames into a
single `pinyin -> total population share` index.
"""

from collections import defaultdict


# Legacy rank-based frequency list used by the original v8.0 rule.
# Unknown surnames are mapped to rank 999 by `get_surname_frequency_rank()`.
SURNAME_FREQUENCY_RANK = {
    'wang': 1,
    'li': 2,
    'zhang': 3,
    'liu': 4,
    'chen': 5,
    'yang': 6,
    'huang': 7,
    'zhao': 8,
    'wu': 9,
    'zhou': 10,
    'xu': 11,
    'sun': 12,
    'ma': 13,
    'zhu': 14,
    'hu': 15,
    'guo': 16,
    'he': 17,
    'gao': 18,
    'lin': 19,
    'luo': 20,
    'zheng': 21,
    'liang': 22,
    'xie': 23,
    'song': 24,
    'tang': 25,
    'deng': 27,
    'han': 28,
    'feng': 29,
    'cao': 30,
    'peng': 31,
    'zeng': 32,
    'xiao': 33,
    'tian': 34,
    'dong': 35,
    'pan': 36,
    'yuan': 37,
    'cai': 38,
    'jiang': 39,
    'yu': 40,
    'du': 41,
    'ye': 42,
    'cheng': 43,
    'wei': 44,
    'su': 45,
    'lu': 46,
    'ding': 47,
    'ren': 48,
    'shen': 49,
    'yao': 50,
    'lu': 51,
    'jiang': 52,
    'cui': 53,
    'tan': 54,
    'liao': 55,
    'fan': 56,
    'wang': 57,
    'shi': 58,
    'jin': 59,
    'wei': 60,
    'jia': 61,
    'xia': 62,
    'fu': 63,
    'fang': 64,
    'zou': 65,
    'xiong': 66,
    'bai': 67,
    'meng': 68,
    'qin': 69,
    'qiu': 70,
    'hou': 71,
    'jiang': 72,
    'yin': 73,
    'xue': 74,
    'yan': 75,
    'duan': 76,
    'lei': 77,
    'long': 78,
    'li': 79,
    'shi': 80,
    'tao': 81,
    'he': 82,
    'gu': 83,
    'mao': 84,
    'hao': 85,
    'gong': 86,
    'shao': 87,
    'wan': 88,
    'qian': 89,
    'yan': 90,
    'fu': 91,
    'wu': 92,
    'dai': 93,
    'mo': 94,
    'kong': 95,
    'xiang': 96,
    'chang': 97,
}


# Raw 400-surname share table, normalized to ASCII pinyin. Duplicates are
# preserved here on purpose and aggregated later by pinyin.
SURNAME_FREQUENCY_SHARE_RAW = [
    (1, 'wang', 7.17), (2, 'li', 7.0), (3, 'zhang', 6.74), (4, 'liu', 5.1), (5, 'chen', 4.61),
    (6, 'yang', 3.22), (7, 'huang', 2.45), (8, 'wu', 2.0), (9, 'zhao', 2.0), (10, 'zhou', 1.9),
    (11, 'xu', 1.45), (12, 'sun', 1.38), (13, 'ma', 1.29), (14, 'zhu', 1.28), (15, 'hu', 1.16),
    (16, 'lin', 1.13), (17, 'guo', 1.13), (18, 'he', 1.06), (19, 'gao', 1.0), (20, 'luo', 0.95),
    (21, 'zheng', 0.93), (22, 'liang', 0.85), (23, 'xie', 0.76), (24, 'song', 0.7), (25, 'tang', 0.69),
    (26, 'xu', 0.66), (27, 'deng', 0.62), (28, 'feng', 0.62), (29, 'han', 0.61), (30, 'cao', 0.6),
    (31, 'zeng', 0.58), (32, 'peng', 0.58), (33, 'xiao', 0.56), (34, 'cai', 0.53), (35, 'pan', 0.52),
    (36, 'tian', 0.52), (37, 'dong', 0.51), (38, 'yuan', 0.5), (39, 'yu', 0.48), (40, 'yu', 0.48),
    (41, 'ye', 0.48), (42, 'jiang', 0.48), (43, 'du', 0.47), (44, 'su', 0.46), (45, 'wei', 0.45),
    (46, 'cheng', 0.45), (47, 'lu', 0.45), (48, 'ding', 0.43), (49, 'shen', 0.41), (50, 'ren', 0.41),
    (51, 'yao', 0.4), (52, 'lu', 0.4), (53, 'fu', 0.4), (54, 'zhong', 0.4), (55, 'jiang', 0.39),
    (56, 'cui', 0.38), (57, 'tan', 0.38), (58, 'liao', 0.37), (59, 'fan', 0.36), (60, 'wang', 0.36),
    (61, 'lu', 0.36), (62, 'jin', 0.35), (63, 'shi', 0.34), (64, 'dai', 0.34), (65, 'jia', 0.33),
    (66, 'wei', 0.32), (67, 'xia', 0.32), (68, 'qiu', 0.32), (69, 'fang', 0.31), (70, 'hou', 0.3),
    (71, 'zou', 0.3), (72, 'xiong', 0.29), (73, 'meng', 0.29), (74, 'qin', 0.29), (75, 'bai', 0.28),
    (76, 'jiang', 0.28), (77, 'yan', 0.27), (78, 'xue', 0.26), (79, 'yin', 0.26), (80, 'duan', 0.24),
    (81, 'lei', 0.24), (82, 'li', 0.22), (83, 'shi', 0.21), (84, 'long', 0.21), (85, 'tao', 0.21),
    (86, 'he', 0.21), (87, 'gu', 0.2), (88, 'mao', 0.2), (89, 'hao', 0.2), (90, 'gong', 0.2),
    (91, 'shao', 0.2), (92, 'wan', 0.19), (93, 'qian', 0.19), (94, 'yan', 0.19), (95, 'lai', 0.18),
    (96, 'qin', 0.18), (97, 'hong', 0.18), (98, 'wu', 0.18), (99, 'mo', 0.18), (100, 'kong', 0.17),
    (101, 'tang', 0.17), (102, 'xiang', 0.17), (103, 'chang', 0.16), (104, 'wen', 0.16), (105, 'kang', 0.16),
    (106, 'shi', 0.15), (107, 'wen', 0.15), (108, 'niu', 0.15), (109, 'fan', 0.15), (110, 'ge', 0.15),
    (111, 'xing', 0.14), (112, 'an', 0.13), (113, 'qi', 0.13), (114, 'yi', 0.13), (115, 'qiao', 0.13),
    (116, 'wu', 0.13), (117, 'pang', 0.13), (118, 'yan', 0.12), (119, 'ni', 0.12), (120, 'zhuang', 0.12),
    (121, 'nie', 0.12), (122, 'zhang', 0.12), (123, 'lu', 0.11), (124, 'yue', 0.11), (125, 'zhai', 0.11),
    (126, 'yin', 0.11), (127, 'zhan', 0.11), (128, 'shen', 0.11), (129, 'ou', 0.11), (130, 'geng', 0.11),
    (131, 'guan', 0.1), (132, 'lan', 0.1), (133, 'jiao', 0.1), (134, 'yu', 0.1), (135, 'zuo', 0.1),
    (136, 'liu', 0.1), (137, 'gan', 0.095), (138, 'zhu', 0.09), (139, 'bao', 0.087), (140, 'ning', 0.083),
    (141, 'shang', 0.082), (142, 'fu', 0.082), (143, 'shu', 0.082), (144, 'ruan', 0.082), (145, 'ke', 0.08),
    (146, 'ji', 0.08), (147, 'mei', 0.079), (148, 'tong', 0.079), (149, 'ling', 0.078), (150, 'bi', 0.078),
    (151, 'shan', 0.076), (152, 'ji', 0.076), (153, 'pei', 0.076), (154, 'huo', 0.075), (155, 'tu', 0.075),
    (156, 'cheng', 0.075), (157, 'miao', 0.075), (158, 'gu', 0.075), (159, 'sheng', 0.074), (160, 'qu', 0.074),
    (161, 'weng', 0.073), (162, 'ran', 0.073), (163, 'luo', 0.073), (164, 'lan', 0.072), (165, 'lu', 0.072),
    (166, 'you', 0.071), (167, 'xin', 0.07), (168, 'jin', 0.069), (169, 'ouyang', 0.068), (170, 'guan', 0.065),
    (171, 'chai', 0.065), (172, 'meng', 0.062), (173, 'bao', 0.062), (174, 'hua', 0.061), (175, 'yu', 0.061),
    (176, 'qi', 0.061), (177, 'pu', 0.056), (178, 'fang', 0.056), (179, 'teng', 0.055), (180, 'qu', 0.055),
    (181, 'rao', 0.055), (182, 'xie', 0.053), (183, 'mu', 0.053), (184, 'ai', 0.052), (185, 'you', 0.052),
    (186, 'yang', 0.05), (187, 'shi', 0.05), (188, 'mu', 0.048), (189, 'nong', 0.047), (190, 'si', 0.044),
    (191, 'zhuo', 0.043), (192, 'gu', 0.043), (193, 'ji', 0.043), (194, 'miao', 0.043), (195, 'jian', 0.043),
    (196, 'che', 0.043), (197, 'xiang', 0.043), (198, 'lian', 0.043), (199, 'lu', 0.042), (200, 'mai', 0.041),
    (201, 'chu', 0.041), (202, 'lou', 0.04), (203, 'dou', 0.04), (204, 'qi', 0.04), (205, 'cen', 0.039),
    (206, 'jing', 0.039), (207, 'dang', 0.039), (208, 'gong', 0.039), (209, 'fei', 0.039), (210, 'bu', 0.038),
    (211, 'leng', 0.038), (212, 'yan', 0.038), (213, 'xi', 0.036), (214, 'wei', 0.036), (215, 'mi', 0.035),
    (216, 'bai', 0.035), (217, 'zong', 0.034), (218, 'qu', 0.033), (219, 'gui', 0.033), (220, 'quan', 0.033),
    (221, 'tong', 0.033), (222, 'ying', 0.033), (223, 'zang', 0.032), (224, 'min', 0.032), (225, 'gou', 0.032),
    (226, 'wu', 0.032), (227, 'bian', 0.032), (228, 'bian', 0.032), (229, 'ji', 0.032), (230, 'shi', 0.031),
    (231, 'he', 0.031), (232, 'qiu', 0.03), (233, 'luan', 0.03), (234, 'sui', 0.03), (235, 'shang', 0.03),
    (236, 'diao', 0.03), (237, 'sha', 0.03), (238, 'rong', 0.029), (239, 'wu', 0.029), (240, 'kou', 0.029),
    (241, 'sang', 0.028), (242, 'lang', 0.028), (243, 'zhen', 0.027), (244, 'cong', 0.027), (245, 'zhong', 0.027),
    (246, 'yu', 0.026), (247, 'ao', 0.026), (248, 'gong', 0.026), (249, 'ming', 0.026), (250, 'she', 0.025),
    (251, 'chi', 0.025), (252, 'zha', 0.025), (253, 'ma', 0.025), (254, 'yuan', 0.025), (255, 'chi', 0.024),
    (256, 'kuang', 0.024), (257, 'guan', 0.023), (258, 'feng', 0.023), (259, 'tan', 0.023), (260, 'kuang', 0.023),
    (261, 'ju', 0.023), (262, 'hui', 0.022), (263, 'jing', 0.022), (264, 'yue', 0.022), (265, 'ji', 0.021),
    (266, 'yu', 0.021), (267, 'xu', 0.021), (268, 'nan', 0.021), (269, 'ban', 0.021), (270, 'chu', 0.021),
    (271, 'yuan', 0.02), (272, 'li', 0.02), (273, 'yan', 0.02), (274, 'chu', 0.02), (275, 'yan', 0.02),
    (276, 'lao', 0.019), (277, 'chen', 0.019), (278, 'xi', 0.017), (279, 'pi', 0.017), (280, 'su', 0.017),
    (281, 'xian', 0.017), (282, 'lin', 0.017), (283, 'lou', 0.017), (284, 'pan', 0.017), (285, 'man', 0.016),
    (286, 'wen', 0.016), (287, 'wei', 0.016), (289, 'li', 0.016), (289, 'yi', 0.016), (290, 'tong', 0.015),
    (291, 'ou', 0.015), (292, 'gao', 0.015), (293, 'hai', 0.015), (294, 'kan', 0.015), (295, 'hua', 0.015),
    (296, 'quan', 0.014), (297, 'qiang', 0.014), (298, 'shuai', 0.014), (299, 'tu', 0.014), (300, 'dou', 0.014),
    (301, 'piao', 0.014), (302, 'ge', 0.014), (303, 'lian', 0.014), (304, 'lian', 0.014), (305, 'yu', 0.014),
    (306, 'jing', 0.013), (307, 'zu', 0.013), (308, 'qi', 0.013), (309, 'ba', 0.013), (310, 'feng', 0.013),
    (311, 'zhi', 0.013), (312, 'qing', 0.013), (313, 'guo', 0.013), (314, 'di', 0.013), (315, 'ping', 0.013),
    (316, 'ji', 0.012), (317, 'suo', 0.012), (318, 'xuan', 0.012), (319, 'jin', 0.012), (320, 'xiang', 0.012),
    (321, 'chu', 0.012), (322, 'men', 0.012), (323, 'yun', 0.012), (324, 'rong', 0.012), (325, 'jing', 0.011),
    (326, 'lai', 0.011), (327, 'hu', 0.011), (328, 'chao', 0.011), (329, 'rui', 0.011), (330, 'du', 0.011),
    (331, 'pu', 0.011), (332, 'que', 0.011), (333, 'pu', 0.011), (334, 'ge', 0.011), (335, 'fu', 0.011),
    (336, 'lu', 0.011), (337, 'bo', 0.011), (338, 'di', 0.011), (339, 'yong', 0.01), (340, 'gu', 0.01),
    (341, 'yang', 0.01), (342, 'a', 0.01), (343, 'wu', 0.01), (344, 'mu', 0.01), (345, 'qiu', 0.01),
    (346, 'qi', 0.01), (347, 'xiu', 0.01), (348, 'tai', 0.01), (349, 'he', 0.01), (350, 'hang', 0.01),
    (351, 'kuang', 0.0094), (352, 'na', 0.0093), (353, 'su', 0.0093), (354, 'xian', 0.0092), (355, 'yin', 0.0091),
    (356, 'lu', 0.0091), (357, 'long', 0.009), (358, 'ru', 0.009), (359, 'zhu', 0.0089), (360, 'zhan', 0.0088),
    (361, 'mu', 0.0086), (362, 'wei', 0.0084), (363, 'yu', 0.0084), (364, 'yin', 0.0084), (365, 'kang', 0.0083),
    (366, 'ji', 0.0082), (367, 'gong', 0.0082), (368, 'ha', 0.0081), (369, 'zhan', 0.0079), (370, 'bin', 0.0077),
    (371, 'rong', 0.0076), (372, 'gou', 0.0076), (373, 'mao', 0.0076), (374, 'li', 0.0076), (375, 'yu', 0.0074),
    (376, 'hu', 0.0074), (377, 'ju', 0.0074), (378, 'jie', 0.0073), (379, 'gan', 0.0072), (380, 'dan', 0.0072),
    (381, 'wei', 0.0071), (382, 'ye', 0.0071), (383, 'si', 0.007), (384, 'yuan', 0.0069), (385, 'shu', 0.0068),
    (386, 'tan', 0.0068), (387, 'yi', 0.0067), (388, 'xin', 0.0067), (389, 'zhan', 0.0067), (390, 'yin', 0.0067),
    (391, 'zan', 0.0066), (392, 'zhi', 0.0065), (393, 'xing', 0.0065), (394, 'feng', 0.0064), (395, 'zhi', 0.0064),
    (396, 'heng', 0.0063), (397, 'fu', 0.0063), (398, 'yao', 0.006), (399, 'bi', 0.006), (400, 'you', 0.006),
]


def _build_share_index(raw_rows):
    share_map = defaultdict(float)
    for _rank, pinyin, share in raw_rows:
        share_map[pinyin] += share
    return {pinyin: round(total, 4) for pinyin, total in share_map.items()}


SURNAME_FREQUENCY_SHARE = _build_share_index(SURNAME_FREQUENCY_SHARE_RAW)


def get_surname_frequency_rank(surname_pinyin: str) -> int:
    """Return legacy frequency rank, or 999 if the surname is missing."""
    surname_lower = surname_pinyin.lower().strip()
    return SURNAME_FREQUENCY_RANK.get(surname_lower, 999)


def get_surname_frequency_share(surname_pinyin: str) -> float:
    """Return aggregated population share for a surname pinyin, or 0.0."""
    surname_lower = surname_pinyin.lower().strip()
    return SURNAME_FREQUENCY_SHARE.get(surname_lower, 0.0)


def compare_surname_frequency(surname1: str, surname2: str) -> dict:
    """
    Compare two surnames using the legacy rank-gap logic.

    This helper is kept intact for baseline reproduction and older code paths.
    """
    rank1 = get_surname_frequency_rank(surname1)
    rank2 = get_surname_frequency_rank(surname2)
    rank_diff = abs(rank1 - rank2)

    if rank1 < rank2:
        more_common = surname1.lower()
    elif rank2 < rank1:
        more_common = surname2.lower()
    else:
        more_common = None

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
        'confidence': confidence,
    }


def compare_surname_frequency_share(surname1: str, surname2: str) -> dict:
    """
    Compare two surnames using aggregated population share.

    Returns a compact summary used by the new `share_ratio` rule.
    """
    share1 = get_surname_frequency_share(surname1)
    share2 = get_surname_frequency_share(surname2)

    if share1 > share2:
        more_common = surname1.lower()
    elif share2 > share1:
        more_common = surname2.lower()
    else:
        more_common = None

    if share1 > 0.0 and share2 > 0.0:
        share_ratio = max(share1, share2) / min(share1, share2)
    elif share1 > 0.0 or share2 > 0.0:
        share_ratio = float('inf')
    else:
        share_ratio = 1.0

    return {
        'more_common': more_common,
        'share1': share1,
        'share2': share2,
        'share_ratio': share_ratio,
        'share_diff': abs(share1 - share2),
        'has_share1': share1 > 0.0,
        'has_share2': share2 > 0.0,
    }


if __name__ == '__main__':
    print("Chinese Surname Frequency Test")
    print("=" * 60)

    print("\nSurname Frequency Rank:")
    for surname in ['wang', 'li', 'zhang', 'zhao', 'unknown']:
        print(f"  {surname}: {get_surname_frequency_rank(surname)}")

    print("\nSurname Population Share:")
    for surname in ['wang', 'wei', 'yu', 'he', 'unknown']:
        print(f"  {surname}: {get_surname_frequency_share(surname):.4f}%")

    print("\nRank Comparison:")
    for s1, s2 in [('li', 'wei'), ('wang', 'li'), ('zhang', 'liu')]:
        result = compare_surname_frequency(s1, s2)
        print(f"  {s1} vs {s2}: {result}")

    print("\nShare Comparison:")
    for s1, s2 in [('wang', 'wei'), ('lu', 'xing'), ('yuan', 'hong')]:
        result = compare_surname_frequency_share(s1, s2)
        print(f"  {s1} vs {s2}: {result}")
