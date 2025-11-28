# -*- coding: utf-8 -*-
"""
拼音音节数据库 / Pinyin Syllables Database
包含所有合法的无声调拼音音节（~400个）
用于v7.0算法的拼音合法性检测

作者 / Author: Ma Jiaxin
日期 / Date: 2025-11-28
"""

# 完整的汉语拼音音节表（无声调）
# Complete Mandarin Chinese Pinyin Syllables (without tones)
# 参考GB/T 16159-2012《汉语拼音正词法基本规则》

PINYIN_SYLLABLES = {
    # 单韵母 / Single Finals
    'a', 'o', 'e', 'ai', 'ei', 'ao', 'ou', 'an', 'en', 'ang', 'eng', 'er',

    # b-
    'ba', 'bo', 'bai', 'bei', 'bao', 'ban', 'ben', 'bang', 'beng', 'bi', 'bie', 'biao', 'bian', 'bin', 'bing',

    # p-
    'pa', 'po', 'pai', 'pei', 'pao', 'pou', 'pan', 'pen', 'pang', 'peng', 'pi', 'pie', 'piao', 'pian', 'pin', 'ping',

    # m-
    'ma', 'mo', 'me', 'mai', 'mei', 'mao', 'mou', 'man', 'men', 'mang', 'meng', 'mi', 'mie', 'miao', 'miu', 'mian', 'min', 'ming',

    # f-
    'fa', 'fo', 'fei', 'fou', 'fan', 'fen', 'fang', 'feng',

    # d-
    'da', 'de', 'dai', 'dei', 'dao', 'dou', 'dan', 'den', 'dang', 'deng', 'di', 'die', 'diao', 'diu', 'dian', 'ding',

    # t-
    'ta', 'te', 'tai', 'tao', 'tou', 'tan', 'tang', 'teng', 'ti', 'tie', 'tiao', 'tian', 'ting',

    # n-
    'na', 'ne', 'nai', 'nei', 'nao', 'nou', 'nan', 'nen', 'nang', 'neng', 'ni', 'nie', 'niao', 'niu', 'nian', 'nin', 'niang', 'ning', 'nong', 'nu', 'nuo', 'nuan', 'nv', 'nve', 'nü', 'nüe',

    # l-
    'la', 'le', 'lai', 'lei', 'lao', 'lou', 'lan', 'lang', 'leng', 'li', 'lia', 'lie', 'liao', 'liu', 'lian', 'lin', 'liang', 'ling', 'long', 'lu', 'luo', 'luan', 'lun', 'lv', 'lve', 'lü', 'lüe',

    # g-
    'ga', 'ge', 'gai', 'gei', 'gao', 'gou', 'gan', 'gen', 'gang', 'geng', 'gong', 'gu', 'gua', 'guo', 'guai', 'gui', 'guan', 'gun', 'guang',

    # k-
    'ka', 'ke', 'kai', 'kao', 'kou', 'kan', 'ken', 'kang', 'keng', 'kong', 'ku', 'kua', 'kuo', 'kuai', 'kui', 'kuan', 'kun', 'kuang',

    # h-
    'ha', 'he', 'hai', 'hei', 'hao', 'hou', 'han', 'hen', 'hang', 'heng', 'hong', 'hu', 'hua', 'huo', 'huai', 'hui', 'huan', 'hun', 'huang',

    # j-
    'ji', 'jia', 'jie', 'jiao', 'jiu', 'jian', 'jin', 'jiang', 'jing', 'jiong', 'ju', 'jue', 'juan', 'jun',

    # q-
    'qi', 'qia', 'qie', 'qiao', 'qiu', 'qian', 'qin', 'qiang', 'qing', 'qiong', 'qu', 'que', 'quan', 'qun',

    # x-
    'xi', 'xia', 'xie', 'xiao', 'xiu', 'xian', 'xin', 'xiang', 'xing', 'xiong', 'xu', 'xue', 'xuan', 'xun',

    # zh-
    'zha', 'zhe', 'zhi', 'zhai', 'zhei', 'zhao', 'zhou', 'zhan', 'zhen', 'zhang', 'zheng', 'zhong', 'zhu', 'zhua', 'zhuo', 'zhuai', 'zhui', 'zhuan', 'zhun', 'zhuang',

    # ch-
    'cha', 'che', 'chi', 'chai', 'chao', 'chou', 'chan', 'chen', 'chang', 'cheng', 'chong', 'chu', 'chua', 'chuo', 'chuai', 'chui', 'chuan', 'chun', 'chuang',

    # sh-
    'sha', 'she', 'shi', 'shai', 'shei', 'shao', 'shou', 'shan', 'shen', 'shang', 'sheng', 'shu', 'shua', 'shuo', 'shuai', 'shui', 'shuan', 'shun', 'shuang',

    # r-
    'ra', 're', 'ri', 'rao', 'rou', 'ran', 'ren', 'rang', 'reng', 'rong', 'ru', 'rua', 'ruo', 'rui', 'ruan', 'run',

    # z-
    'za', 'ze', 'zi', 'zai', 'zei', 'zao', 'zou', 'zan', 'zen', 'zang', 'zeng', 'zong', 'zu', 'zuo', 'zui', 'zuan', 'zun',

    # c-
    'ca', 'ce', 'ci', 'cai', 'cao', 'cou', 'can', 'cen', 'cang', 'ceng', 'cong', 'cu', 'cuo', 'cui', 'cuan', 'cun',

    # s-
    'sa', 'se', 'si', 'sai', 'sao', 'sou', 'san', 'sen', 'sang', 'seng', 'song', 'su', 'suo', 'sui', 'suan', 'sun',

    # y-
    'ya', 'yo', 'ye', 'yai', 'yao', 'you', 'yan', 'yang', 'yong', 'yi', 'yin', 'ying', 'yu', 'yue', 'yuan', 'yun',

    # w-
    'wa', 'wo', 'wai', 'wei', 'wan', 'wen', 'wang', 'weng', 'wu',
}

# 常见中文名字音节（高频）
# Common Chinese Given Name Syllables (High Frequency)
# 用于微调：这些音节在名字中出现时加一点权重
COMMON_GIVEN_NAME_SYLLABLES = {
    'jun', 'hua', 'wei', 'yang', 'xin', 'ming', 'jie', 'ting', 'yue', 'qi',
    'yu', 'xiang', 'jia', 'yun', 'fang', 'lei', 'tao', 'li', 'ping', 'jing',
    'bin', 'feng', 'hong', 'rong', 'xia', 'lin', 'han', 'ran', 'zhi', 'cheng',
    'bo', 'kai', 'hao', 'nan', 'hui', 'yan', 'chen', 'guang', 'peng', 'dong',
}

def is_valid_pinyin_syllable(syllable: str) -> bool:
    """
    检查单个音节是否是合法拼音

    Args:
        syllable: 音节字符串（小写）

    Returns:
        bool: 是否是合法拼音音节
    """
    return syllable.lower() in PINYIN_SYLLABLES


def is_common_given_name_syllable(syllable: str) -> bool:
    """
    检查音节是否是常见名字音节

    Args:
        syllable: 音节字符串（小写）

    Returns:
        bool: 是否是常见名字音节
    """
    return syllable.lower() in COMMON_GIVEN_NAME_SYLLABLES


# 导出
__all__ = [
    'PINYIN_SYLLABLES',
    'COMMON_GIVEN_NAME_SYLLABLES',
    'is_valid_pinyin_syllable',
    'is_common_given_name_syllable',
]
