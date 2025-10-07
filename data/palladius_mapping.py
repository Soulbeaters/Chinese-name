# -*- coding: utf-8 -*-
"""
帕拉迪俄语转写库 / База транслитерации Палладия
中文→俄语转写 / Китайский→русская транслитерация
基于标准帕拉迪系统 / На основе стандартной системы Палладия
"""

try:
    from pypinyin import lazy_pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False


# 拼音→俄语帕拉迪转写映射表 / Таблица соответствий пиньинь→Палладий
PINYIN_TO_RUSSIAN = {
    # 声母 / Инициали
    'a': 'а', 'ai': 'ай', 'an': 'ань', 'ang': 'ан', 'ao': 'ао',
    'ba': 'ба', 'bai': 'бай', 'ban': 'бань', 'bang': 'бан', 'bao': 'бао',
    'bei': 'бэй', 'ben': 'бэнь', 'beng': 'бэн', 'bi': 'би', 'bian': 'бянь',
    'biao': 'бяо', 'bie': 'бе', 'bin': 'бинь', 'bing': 'бин', 'bo': 'бо', 'bu': 'бу',

    'ca': 'ца', 'cai': 'цай', 'can': 'цань', 'cang': 'цан', 'cao': 'цао',
    'ce': 'цэ', 'cen': 'цэнь', 'ceng': 'цэн', 'cha': 'ча', 'chai': 'чай',
    'chan': 'чань', 'chang': 'чан', 'chao': 'чао', 'che': 'чэ', 'chen': 'чэнь',
    'cheng': 'чэн', 'chi': 'чи', 'chong': 'чун', 'chou': 'чоу', 'chu': 'чу',
    'chua': 'чуа', 'chuai': 'чуай', 'chuan': 'чуань', 'chuang': 'чуан', 'chui': 'чуй',
    'chun': 'чунь', 'chuo': 'чо', 'ci': 'цы', 'cong': 'цун', 'cou': 'цоу', 'cu': 'цу',
    'cuan': 'цуань', 'cui': 'цуй', 'cun': 'цунь', 'cuo': 'цо',

    'da': 'да', 'dai': 'дай', 'dan': 'дань', 'dang': 'дан', 'dao': 'дао',
    'de': 'дэ', 'dei': 'дэй', 'den': 'дэнь', 'deng': 'дэн', 'di': 'ди',
    'dia': 'дя', 'dian': 'дянь', 'diao': 'дяо', 'die': 'де', 'ding': 'дин',
    'diu': 'дю', 'dong': 'дун', 'dou': 'доу', 'du': 'ду', 'duan': 'дуань',
    'dui': 'дуй', 'dun': 'дунь', 'duo': 'до',

    'e': 'э', 'ei': 'эй', 'en': 'энь', 'eng': 'эн', 'er': 'эр',

    'fa': 'фа', 'fan': 'фань', 'fang': 'фан', 'fei': 'фэй', 'fen': 'фэнь',
    'feng': 'фэн', 'fo': 'фо', 'fou': 'фоу', 'fu': 'фу',

    'ga': 'га', 'gai': 'гай', 'gan': 'гань', 'gang': 'ган', 'gao': 'гао',
    'ge': 'гэ', 'gei': 'гэй', 'gen': 'гэнь', 'geng': 'гэн', 'gong': 'гун',
    'gou': 'гоу', 'gu': 'гу', 'gua': 'гуа', 'guai': 'гуай', 'guan': 'гуань',
    'guang': 'гуан', 'gui': 'гуй', 'gun': 'гунь', 'guo': 'го',

    'ha': 'ха', 'hai': 'хай', 'han': 'хань', 'hang': 'хан', 'hao': 'хао',
    'he': 'хэ', 'hei': 'хэй', 'hen': 'хэнь', 'heng': 'хэн', 'hong': 'хун',
    'hou': 'хоу', 'hu': 'ху', 'hua': 'хуа', 'huai': 'хуай', 'huan': 'хуань',
    'huang': 'хуан', 'hui': 'хуй', 'hun': 'хунь', 'huo': 'хо',

    'ji': 'цзи', 'jia': 'цзя', 'jian': 'цзянь', 'jiang': 'цзян', 'jiao': 'цзяо',
    'jie': 'цзе', 'jin': 'цзинь', 'jing': 'цзин', 'jiong': 'цзюн', 'jiu': 'цзю',
    'ju': 'цзюй', 'juan': 'цзюань', 'jue': 'цзюэ', 'jun': 'цзюнь',

    'ka': 'ка', 'kai': 'кай', 'kan': 'кань', 'kang': 'кан', 'kao': 'као',
    'ke': 'кэ', 'kei': 'кэй', 'ken': 'кэнь', 'keng': 'кэн', 'kong': 'кун',
    'kou': 'коу', 'ku': 'ку', 'kua': 'куа', 'kuai': 'куай', 'kuan': 'куань',
    'kuang': 'куан', 'kui': 'куй', 'kun': 'кунь', 'kuo': 'ко',

    'la': 'ла', 'lai': 'лай', 'lan': 'лань', 'lang': 'лан', 'lao': 'лао',
    'le': 'лэ', 'lei': 'лэй', 'leng': 'лэн', 'li': 'ли', 'lia': 'ля',
    'lian': 'лянь', 'liang': 'лян', 'liao': 'ляо', 'lie': 'ле', 'lin': 'линь',
    'ling': 'лин', 'liu': 'лю', 'long': 'лун', 'lou': 'лоу', 'lu': 'лу',
    'luan': 'луань', 'lue': 'люэ', 'lun': 'лунь', 'luo': 'ло', 'lv': 'люй',

    'ma': 'ма', 'mai': 'май', 'man': 'мань', 'mang': 'ман', 'mao': 'мао',
    'me': 'мэ', 'mei': 'мэй', 'men': 'мэнь', 'meng': 'мэн', 'mi': 'ми',
    'mian': 'мянь', 'miao': 'мяо', 'mie': 'ме', 'min': 'минь', 'ming': 'мин',
    'miu': 'мю', 'mo': 'мо', 'mou': 'моу', 'mu': 'му',

    'na': 'на', 'nai': 'най', 'nan': 'нань', 'nang': 'нан', 'nao': 'нао',
    'ne': 'нэ', 'nei': 'нэй', 'nen': 'нэнь', 'neng': 'нэн', 'ni': 'ни',
    'nian': 'нянь', 'niang': 'нян', 'niao': 'няо', 'nie': 'не', 'nin': 'нинь',
    'ning': 'нин', 'niu': 'ню', 'nong': 'нун', 'nou': 'ноу', 'nu': 'ну',
    'nuan': 'нуань', 'nue': 'нюэ', 'nun': 'нунь', 'nuo': 'но', 'nv': 'нюй',

    'o': 'о', 'ou': 'оу',

    'pa': 'па', 'pai': 'пай', 'pan': 'пань', 'pang': 'пан', 'pao': 'пао',
    'pei': 'пэй', 'pen': 'пэнь', 'peng': 'пэн', 'pi': 'пи', 'pian': 'пянь',
    'piao': 'пяо', 'pie': 'пе', 'pin': 'пинь', 'ping': 'пин', 'po': 'по', 'pou': 'поу', 'pu': 'пу',

    'qi': 'ци', 'qia': 'ця', 'qian': 'цянь', 'qiang': 'цян', 'qiao': 'цяо',
    'qie': 'це', 'qin': 'цинь', 'qing': 'цин', 'qiong': 'цюн', 'qiu': 'цю',
    'qu': 'цюй', 'quan': 'цюань', 'que': 'цюэ', 'qun': 'цюнь',

    'ran': 'жань', 'rang': 'жан', 'rao': 'жао', 're': 'жэ', 'ren': 'жэнь',
    'reng': 'жэн', 'ri': 'жи', 'rong': 'жун', 'rou': 'жоу', 'ru': 'жу',
    'rua': 'жуа', 'ruan': 'жуань', 'rui': 'жуй', 'run': 'жунь', 'ruo': 'жо',

    'sa': 'са', 'sai': 'сай', 'san': 'сань', 'sang': 'сан', 'sao': 'сао',
    'se': 'сэ', 'sen': 'сэнь', 'seng': 'сэн', 'sha': 'ша', 'shai': 'шай',
    'shan': 'шань', 'shang': 'шан', 'shao': 'шао', 'she': 'шэ', 'shei': 'шэй',
    'shen': 'шэнь', 'sheng': 'шэн', 'shi': 'ши', 'shou': 'шоу', 'shu': 'шу',
    'shua': 'шуа', 'shuai': 'шуай', 'shuan': 'шуань', 'shuang': 'шуан', 'shui': 'шуй',
    'shun': 'шунь', 'shuo': 'шо', 'si': 'сы', 'song': 'сун', 'sou': 'соу',
    'su': 'су', 'suan': 'суань', 'sui': 'суй', 'sun': 'сунь', 'suo': 'со',

    'ta': 'та', 'tai': 'тай', 'tan': 'тань', 'tang': 'тан', 'tao': 'тао',
    'te': 'тэ', 'tei': 'тэй', 'teng': 'тэн', 'ti': 'ти', 'tian': 'тянь',
    'tiao': 'тяо', 'tie': 'те', 'ting': 'тин', 'tong': 'тун', 'tou': 'тоу',
    'tu': 'ту', 'tuan': 'туань', 'tui': 'туй', 'tun': 'тунь', 'tuo': 'то',

    'wa': 'ва', 'wai': 'вай', 'wan': 'вань', 'wang': 'ван', 'wei': 'вэй',
    'wen': 'вэнь', 'weng': 'вэн', 'wo': 'во', 'wu': 'у',

    'xi': 'си', 'xia': 'ся', 'xian': 'сянь', 'xiang': 'сян', 'xiao': 'сяо',
    'xie': 'се', 'xin': 'синь', 'xing': 'син', 'xiong': 'сюн', 'xiu': 'сю',
    'xu': 'сюй', 'xuan': 'сюань', 'xue': 'сюэ', 'xun': 'сюнь',

    'ya': 'я', 'yan': 'янь', 'yang': 'ян', 'yao': 'яо', 'ye': 'е',
    'yi': 'и', 'yin': 'инь', 'ying': 'ин', 'yo': 'ё', 'yong': 'юн',
    'you': 'ю', 'yu': 'юй', 'yuan': 'юань', 'yue': 'юэ', 'yun': 'юнь',

    'za': 'цза', 'zai': 'цзай', 'zan': 'цзань', 'zang': 'цзан', 'zao': 'цзао',
    'ze': 'цзэ', 'zei': 'цзэй', 'zen': 'цзэнь', 'zeng': 'цзэн', 'zha': 'чжа',
    'zhai': 'чжай', 'zhan': 'чжань', 'zhang': 'чжан', 'zhao': 'чжао', 'zhe': 'чжэ',
    'zhei': 'чжэй', 'zhen': 'чжэнь', 'zheng': 'чжэн', 'zhi': 'чжи', 'zhong': 'чжун',
    'zhou': 'чжоу', 'zhu': 'чжу', 'zhua': 'чжуа', 'zhuai': 'чжуай', 'zhuan': 'чжуань',
    'zhuang': 'чжуан', 'zhui': 'чжуй', 'zhun': 'чжунь', 'zhuo': 'чжо', 'zi': 'цзы',
    'zong': 'цзун', 'zou': 'цзоу', 'zu': 'цзу', 'zuan': 'цзуань', 'zui': 'цзуй',
    'zun': 'цзунь', 'zuo': 'цзо',
}


def to_russian(text: str) -> str:
    """
    中文→俄语帕拉迪转写 / Китайский→русская транслитерация Палладия

    Examples:
        >>> to_russian('马嘉星')
        'Ма Цзясин'
        >>> to_russian('李明')
        'Ли Мин'
    """
    if not PYPINYIN_AVAILABLE:
        return text

    # 获取拼音
    pinyin_list = lazy_pinyin(text, style=Style.NORMAL)

    # 转换为俄语
    russian_parts = []
    for i, py in enumerate(pinyin_list):
        ru = PINYIN_TO_RUSSIAN.get(py.lower(), py)
        # 首字母大写
        if i == 0:
            ru = ru.capitalize()
        russian_parts.append(ru)

    return ''.join(russian_parts)


def to_russian_spaced(text: str) -> str:
    """
    中文→俄语（带空格）/ Китайский→русский (с пробелами)

    Examples:
        >>> to_russian_spaced('马嘉星')
        'Ма Цзя син'
    """
    if not PYPINYIN_AVAILABLE:
        return text

    pinyin_list = lazy_pinyin(text, style=Style.NORMAL)
    russian_parts = []

    for i, py in enumerate(pinyin_list):
        ru = PINYIN_TO_RUSSIAN.get(py.lower(), py)
        if i == 0:
            ru = ru.capitalize()
        russian_parts.append(ru)

    return ' '.join(russian_parts)


if __name__ == '__main__':
    if PYPINYIN_AVAILABLE:
        tests = ['马嘉星', '李明', '王芳', '张伟', '欧阳锋', '司马懿']
        print("帕拉迪转写测试:")
        for name in tests:
            print(f"{name} → {to_russian(name)}")
    else:
        print("请安装: pip install pypinyin")
