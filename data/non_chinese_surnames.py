# -*- coding: utf-8 -*-
"""
非中文姓氏排除列表 / Список исключений нек итайских фамилий
Exclusion list of non-Chinese surnames (Japanese, Korean, European, etc.)

中文注释: 用于排除日文、韩文、欧美等非中文姓氏,提高中文作者识别准确率
Русский комментарий: Для исключения японских, корейских, европейских и других нек итайских фамилий
"""

# 日文姓氏 / Японские фамилии
# Japanese surnames
# 来源: Crossref数据分析 + 日本常见姓氏
JAPANESE_SURNAMES = {
    # 极高频 (>100次) / Очень высокая частота
    'ito',          # 伊藤 (196次)
    'kato',         # 加藤 (190次)
    'yoshida',      # 吉田 (151次)
    'yamada',       # 山田 (129次)
    'mizuno',       # 水野 (163次)

    # 高频 (50-100次) / Высокая частота
    'tanaka',       # 田中 (90次)
    'saito',        # 斋藤 (90次)
    'sato',         # 佐藤 (81次)
    'ishii',        # 石井 (99次)
    'inoue',        # 井上 (74次)
    'sasaki',       # 佐佐木 (61次)
    'oda',          # 小田 (62次)
    'ikeda',        # 池田 (63次)
    'nagai',        # 永井 (63次)

    # 中高频 (30-50次) / Средне-высокая частота
    'fujita',       # 藤田 (48次)
    'akiyama',      # 秋山 (54次)
    'oyama',        # 大山 (60次)
    'okino',        # 沖野 (44次)
    'ogawa',        # 小川 (40次)
    'adachi',       # 足立 (40次)
    'ohyama',       # 大山 (40次)
    'suzuki',       # 铃木 (43次)
    'goto',         # 后藤 (34次)
    'yokota',       # 横田 (34次)
    'kimura',       # 木村 (36次)
    'kikuchi',      # 菊池 (36次)

    # 中频 (20-30次) / Средняя частота
    'matsuda',      # 松田 (43次)
    'kaneko',       # 金子 (51次)
    'kokudo',       # 小久户 (51次)
    'koyama',       # 小山 (51次)
    'murata',       # 村田 (34次)
    'takagi',       # 高木 (35次)
    'hatano',       # 波多野 (35次)
    'maeda',        # 前田 (24次)
    'hayashi',      # 林 (24次) - 注意:中文也有林姓
    'shoji',        # 庄司 (24次)
    'oshima',       # 大岛 (22次)
    'shibata',      # 柴田 (22次)
    'shimizu',      # 清水 (19次)
    'wada',         # 和田 (19次)
    'mishima',      # 三岛 (18次)
    'aoki',         # 青木 (26次)
    'harada',       # 原田 (26次)

    # 其他常见日文姓氏 / Другие распространенные японские фамилии
    'watanabe',     # 渡边
    'nakamura',     # 中村
    'kobayashi',    # 小林
    'yamamoto',     # 山本
    'takahashi',    # 高桥
    'mori',         # 森 (33次)
    'ueda',         # 上田 (20次)
    'fujii',        # 藤井 (27次)
    'eguchi',       # 江口 (27次)
    'takeda',       # 武田 (28次)
    'nakao ka',     # 中冈 (28次)
    'mukai',        # 向井 (22次)
    'inaba',        # 稻叶 (20次)
    'ozaki',        # 尾崎 (20次)
    'sakai',        # 酒井 (20次)
    'kurita',       # 栗田 (20次)
    'deguchi',      # 出口 (20次)
    'niwa',         # 丹羽 (45次)
    'asada',        # 浅田 (48次)
    'machida',      # 町田 (47次)
    'ibata',        # 伊波田 (47次)
    'hada',         # 波田 (49次)
    'hase',         # 长谷 (49次)
    'ueno',         # 上野 (18次)
    'okada',        # 冈田
    'matsumoto',    # 松本
    'imai',         # 今井
    'hashimoto',    # 桥本
    'sasada',       # 笹田 (53次)
    'terada',       # 寺田 (101次)
    'honma',        # 本间 (46次)
    'kino',         # 木野 (46次)
    'miyata',       # 宫田 (109次)
    'morino',       # 森野 (121次)
    'tazaki',       # 田崎 (43次)
    'tsuruta',      # 鹤田 (85次)
    'omura',        # 大村 (84次)
    'tawara',       # 田原 (56次)
    'gunji',        # 郡司 (56次)
    'iwakiri',      # 岩切 (56次)
    'tazaki',       # 田崎 (43次)
    'sugioka',      # 杉冈 (40次)
    'tada',         # 多田 (39次)
    'shiomi',       # 盐见 (32次)
    'kofuji',       # 小富士 (32次)
    'kubo',         # 久保 (32次)
    'kojima',       # 小岛 (33次)
    'sunami',       # 须波见 (28次)
    'koiso',        # 小矶
    'toma',         # 当间 (27次)
    'abe',          # 安倍 (43次)
    'yoko ta',      # 横田
    'uchino',       # 内野 (34次)
    'tohjima',      # 东岛 (34次)
    'saigo',        # 西乡 (19次)
    'masetti',      # (19次) - 可能非日文
    'taya',         # 田谷 (19次)
    'ichida',       # 市田 (27次)
    'morise',       # 森濑 (27次)
    'atari',        # 中 (26次)
    'imamura',      # 今村 (23次)
    'hoshino',      # 星野 (23次)
    'ehara',        # 江原 (23次)
    'okawa',        # 大川
}

# 韩文姓氏 / Корейские фамилии
# Korean surnames
# 来源: Crossref数据分析 + 韩国常见姓氏
KOREAN_SURNAMES = {
    # 极高频 / Очень высокая частота
    'kim',          # 金 (韩语) - 注意与中文"金"区分
    'choi',         # 崔 (186次) - 韩语拼写
    'jung',         # 郑 (117次)
    'cho',          # 赵 (110次)
    'yoon',         # 尹 (130次)
    'hwang',        # 黄 (75次) - 韩语拼写

    # 高频 / Высокая частота
    'jeong',        # 郑 (72次)
    'jeon',         # 全 (39次)
    'seo',          # 徐 (55次) - 韩语拼写
    'kwon',         # 权 (40次)
    'shin',         # 申 (40次)
    'jang',         # 张 (58次) - 韩语拼写
    'byun',         # 边 (58次)
    'moon',         # 文 (40次)
    'ryu',          # 柳 (37次)
    'yoo',          # 刘 (37次) - 韩语拼写

    # 中频 / Средняя частота
    'chung',        # 郑 (46次) - 变体
    'ahn',          # 安 (25次)
    'ko',           # 高 (27次) - 韩语拼写
    'son',          # 孙 (21次) - 韩语拼写

    # 其他常见韩文姓氏 / Другие корейские фамилии
    # 注意: han和song已移除，因为是中韩共享姓氏 / Примечание: han и song удалены как общие фамилии
    'lee',          # 李 (韩语) - 733次,但需谨慎
    'park',         # 朴
    'kang',         # 姜
    'lim',          # 林 - 韩语拼写
    # 'han',        # 韩 - 已移除(中韩共享) / Удалено (общая фамилия)
    'oh',           # 吴
    # 'song',       # 宋 - 已移除(中韩共享) / Удалено (общая фамилия)
    'baek',         # 白
    'nam',          # 南
    'ha',           # 河 (23次)
    'jo',           # 赵 (19次)
}

# 欧美姓氏 (高频) / Европейские и американские фамилии (высокочастотные)
# European/American surnames (high frequency)
# 来源: Crossref数据中频率>100的明显欧美姓氏
EUROPEAN_SURNAMES = {
    # 德语姓氏 / Немецкие фамилии
    'kramer',       # 309次
    'müller',       # 180次
    'wagner',       # 146次
    'fischer',      # 135次
    'mueller',      # 44次 - müller变体
    'weber',        # 62次
    'meyer',        # 107次
    'kaiser',       # 74次
    'berger',       # 71次
    'meier',        # 38次
    'bauer',        # 32次
    'klein',        # 56次
    'richter',      # 55次
    'huber',        # 90次
    'neumann',      # 47次
    'jansen',       # 52次
    'janssen',      # 51次
    'schmidt',
    'schneider',
    'schulz',
    'becker',
    'hoffmann',
    'koch',
    'schäfer',      # 30次
    'büttner',      # 33次
    'hahn',         # 33次
    'jäger',        # 32次
    'keller',       # 34次
    'könig',        # 18次
    'lehmann',      # 20次
    'maier',        # 25次
    'mayer',        # 22次
    'geyer',        # 54次
    'krause',       # 58次
    'weiler',       # 23次
    'buchner',      # 66次
    'büchner',      # 46次
    'baumann',      # 24次
    'sommer',       # 34次
    'hutter',       # 35次
    'unger',        # 19次
    'gerber',       # 19次
    'hauser',       # 19次
    'hübner',       # 19次
    'reiter',       # 19次
    'junge',        # 56次
    'weller',       # 34次
    'hofer',        # 36次
    'mahler',       # 36次
    'krug',         # 31次
    'hansen',       # 31次
    'lohmann',      # 39次
    'wörner',       # 18次
    'hammer',       # 26次
    'sutter',       # 26次
    'urban',        # 28次
    'warneke',      # 36次
    'maurer',       # 37次
    'kessler',      # 38次

    # 意大利语姓氏 / Итальянские фамилии
    'rossi',        # 70次
    'romano',       # 52次
    'ferrari',      # 42次
    'ricci',        # 51次
    'moreno',       # 73次
    'russo',
    'bruno',
    'gallo',
    'costa',
    'marino',
    'greco',
    'romano',
    'maggi',        # 62次
    'gatto',        # 22次

    # 法语姓氏 / Французские фамилии
    'moreau',       # 111次
    'bernard',
    'dubois',
    'martin',
    'durand',
    'petit',
    'robert',
    'richard',
    'simon',        # 169次
    'perrin',       # 37次
    'robin',        # 26次

    # 英语姓氏 / Английские фамилии
    'smith',
    'johnson',      # 51次
    'williams',
    'brown',
    'jones',
    'miller',       # 58次
    'davis',
    'wilson',       # 64次
    'moore',        # 40次
    'taylor',       # 80次
    'anderson',
    'thomas',
    'jackson',
    'white',        # 38次
    'harris',
    'martin',
    'thompson',
    'king',         # 54次
    'young',        # 139次
    'allen',        # 57次
    'walker',
    'baker',        # 38次
    'chapman',      # 51次
    'newman',       # 48次
    'turner',       # 29次
    'cooper',       # 21次
    'warren',       # 21次
    'cameron',      # 21次
    'ryan',         # 24次
    'farmer',       # 24次
    'mason',        # 29次
    'kerr',         # 72次
    'fisher',       # 30次
    'byrne',        # 24次
    'pearson',      # 28次
    'morgan',       # 27次
    'gilmore',      # 27次
    'rowe',         # 23次
    'dawson',       # 23次

    # 西班牙语/葡萄牙语姓氏 / Испанские/португальские фамилии
    'garcia',
    'martinez',
    'rodriguez',
    'lopez',
    'gonzalez',
    'perez',
    'sanchez',
    'fernandez',
    'silva',        # 40次
    'pereira',      # 30次
    'ribeiro',      # 30次
    'sousa',        # 57次
    'almeida',      # 27次
    'salgado',      # 27次
    'vieira',       # 25次

    # 北欧姓氏 / Скандинавские фамилии
    'jensen',       # 35次
    'olsen',        # 36次
    'nielsen',      # 24次
    'jonsson',      # 57次
    'jönsson',      # 22次
    'larsson',      # 22次
    'nilsson',      # 28次
    'olsson',       # 23次
    'johansson',

    # 荷兰语姓氏 / Нидерландские фамилии
    'de jong',
    'de vries',
    'van den berg',
    'van dijk',
    'jansen',
    'bakker',       # 27次

    # 其他欧洲姓氏 / Другие европейские фамилии
    'kowalski',     # 波兰
    'novak',        # 捷克/斯洛伐克
    'kovacs',       # 匈牙利
    'popov',        # 俄罗斯
    'ivanov',       # 俄罗斯
    'petrov',       # 俄罗斯
    'levin',        # 72次 - 可能是俄罗斯或犹太姓氏
    'cohen',        # 86次 - 犹太姓氏
    'levitan',      # 29次

    # 混合/复合姓氏的组成部分 / Компоненты смешанных фамилий
    'schweizer',    # 瑞士姓氏 (Liang Schweizer)
    'adrianov',     # 俄罗斯姓氏 (MA Adrianov)
    'lamberty',     # 德/法姓氏 (Bond-Lamberty)
    'bond',         # 英姓氏 (Bond-Lamberty)

    # 补充遗漏的外国姓氏 / Дополнительные иностранные фамилии
    'graikou',      # 希腊姓氏
    'jeha',         # 阿拉伯姓氏
    'helmy',        # 阿拉伯姓氏
    'baldetorp',    # 北欧姓氏
    'nguyen',       # 越南姓氏（高频！）
    'ivanenkov',    # 俄罗斯姓氏
    'blaiszik',     # 波兰/犹太姓氏
    'huybrechs',    # 荷兰姓氏
    'prather',      # 英文姓氏
    'stappers',     # 荷兰姓氏
    'bowen',        # 威尔士姓氏
    'sears',        # 英文姓氏
    'gotzkow',      # 德国姓氏
    'brumpton',     # 英文姓氏
    'finlay',       # 苏格兰姓氏
    'aydi',         # 阿拉伯姓氏
    'kankare',      # 芬兰姓氏
    'barr',         # 英文姓氏
    'teh',          # 马来西亚姓氏
    'karamehmetoglu', # 土耳其姓氏
    'poulter',      # 英文姓氏
    'cappellaro',   # 意大利姓氏
    'melin',        # 瑞典姓氏
    'riu',          # 加泰罗尼亚姓氏

    # 2025年优化补充 - 基于v5.0误判案例分析
    # 越南姓氏 / Vietnamese surnames
    'phan',         # 潘 - 越南高频姓氏
    'tran',         # 陈 - 越南第二大姓
    'le',           # 黎 - 越南常见姓
    'hoang',        # 黄 - 越南姓氏
    'vu',           # 武 - 越南姓氏
    'dao',          # 道 - 越南姓氏
    'ngo',          # 吴 - 越南姓氏（与中文吴不同拼写）

    # 法国姓氏补充 / French surnames
    'brillault',    # 法国姓氏

    # 犹太/德国姓氏 / Jewish/German surnames
    'rosenbloom',   # 犹太姓氏（玫瑰之花）

    # 英美姓氏补充 / English/American surnames
    'simpson',      # 英国姓氏
    'baron',        # 英国贵族姓氏
}

# 印度姓氏 / Индийские фамилии
INDIAN_SURNAMES = {
    'kumar',        # 228次
    'khan',         # 168次
    'sharma',       # 106次
    'singh',
    'patel',
    'gupta',
    'verma',        # 24次
    'jain',         # 40次
    'mehta',        # 42次
    'mishra',       # 58次
    'joshi',        # 33次
    'desai',        # 44次
    'iyer',         # 28次
    'saha',         # 28次
    'basu',         # 40次
    'bose',         # 39次
    'dutta',        # 41次
    'goswami',      # 29次
    'narayan',      # 47次
    'tiwari',       # 26次
    'misra',        # 26次
    'rana',         # 26次
    'raza',         # 25次
    'amin',         # 27次
}

# 合并所有非中文姓氏 / Объединение всех нек итайских фамилий
# Combine all non-Chinese surnames
# 注意：韩文姓氏已移除，因为绝大多数是中韩共享的汉字姓氏 / Примечание: корейские фамилии удалены, т.к. большинство - общие ханьские фамилии
ALL_NON_CHINESE_SURNAMES = (
    JAPANESE_SURNAMES |
    # KOREAN_SURNAMES |  # 已移除！大部分是中韩共享姓氏 / Удалено! Большинство - общие фамилии
    EUROPEAN_SURNAMES |
    INDIAN_SURNAMES
)


def is_non_chinese_surname(surname: str) -> bool:
    """
    判断是否为非中文姓氏 / Проверка, является ли фамилия нек итайской
    Check if a surname is non-Chinese

    中文: 检查姓氏是否在非中文姓氏排除列表中
    Русский: Проверка, находится ли фамилия в списке исключений

    Args:
        surname (str): 待检查的姓氏(拼音形式)
                       Фамилия для проверки (в пиньинь)

    Returns:
        bool: True表示是非中文姓氏,应排除
              True означает, что это нек итайская фамилия, должна быть исключена

    Examples:
        >>> is_non_chinese_surname('ito')
        True
        >>> is_non_chinese_surname('zhang')
        False
    """
    return surname.lower().strip() in ALL_NON_CHINESE_SURNAMES


def get_surname_origin(surname: str) -> str:
    """
    获取姓氏的可能来源 / Получить возможное происхождение фамилии
    Get the possible origin of a surname

    Returns:
        str: 'Japanese' / 'Korean' / 'European' / 'Indian' / 'Unknown'
    """
    surname_lower = surname.lower().strip()

    if surname_lower in JAPANESE_SURNAMES:
        return 'Japanese'
    elif surname_lower in KOREAN_SURNAMES:
        return 'Korean'
    elif surname_lower in EUROPEAN_SURNAMES:
        return 'European'
    elif surname_lower in INDIAN_SURNAMES:
        return 'Indian'
    else:
        return 'Unknown'


if __name__ == '__main__':
    print("=" * 60)
    print("非中文姓氏排除列表测试 / Тестирование списка исключений")
    print("=" * 60)

    print("\n统计信息 / Статистика:")
    print("-" * 60)
    print(f"日文姓氏数量 / Японских фамилий: {len(JAPANESE_SURNAMES)}")
    print(f"韩文姓氏数量 / Корейских фамилий: {len(KOREAN_SURNAMES)}")
    print(f"欧美姓氏数量 / Европейских фамилий: {len(EUROPEAN_SURNAMES)}")
    print(f"印度姓氏数量 / Индийских фамилий: {len(INDIAN_SURNAMES)}")
    print(f"总计 / Всего: {len(ALL_NON_CHINESE_SURNAMES)}")

    print("\n测试用例 / Тестовые примеры:")
    print("-" * 60)
    test_cases = [
        ('ito', True, 'Japanese'),
        ('kim', True, 'Korean'),
        ('smith', True, 'European'),
        ('kumar', True, 'Indian'),
        ('zhang', False, 'Unknown'),
        ('li', False, 'Unknown'),
        ('wang', False, 'Unknown'),
    ]

    for surname, expected_non_chinese, expected_origin in test_cases:
        is_non_chinese = is_non_chinese_surname(surname)
        origin = get_surname_origin(surname)
        status = 'PASS' if is_non_chinese == expected_non_chinese else 'FAIL'
        print(f"[{status}] {surname:10} -> 非中文: {is_non_chinese:5} 来源: {origin:10} (预期: {expected_origin})")
