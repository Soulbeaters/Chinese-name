# -*- coding: utf-8 -*-
"""
v8.0中文姓氏位置识别算法 / v8.0 Chinese Surname Position Identifier

核心改进 / Key Improvements:
1. Fellegi-Sunter风格打分框架 (Fellegi-Sunter style scoring framework)
2. 批量一致性调整 (Batch consistency adjustment)
3. 单音节优化 (Single syllable optimization)
4. 数据源特定策略 (Source-specific strategies)

作者: Ma Jiaxin
日期: 2025-11-29
"""

import re
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.surname_pinyin_db import is_surname_pinyin, get_surname_from_pinyin
from data.surname_frequency import get_surname_frequency_rank
from data.western_name_features import (
    has_western_suffix,
    has_western_consonant_cluster,
    has_latin_extended_chars,
    is_likely_western_name,
    is_common_western_surname,
)
from src.pinyin_validator import is_valid_pinyin_name
from src.affiliation_analyzer import analyze_affiliation, AffiliationInfo
from src.config_v8 import (
    get_config,
    SourceConfig,
    CHINESE_FEATURE_WEIGHTS,
    WESTERN_FEATURE_WEIGHTS,
    MIXED_FEATURE_WEIGHTS,
    sigmoid,
)


# ========== 数据结构 Data Structures ==========

@dataclass
class Token:
    """Token信息 / Token information"""
    raw: str              # 原始字符串
    norm: str             # 小写规范化
    ascii: str            # 去除变音符
    is_initial: bool      # 是否是缩写
    has_diacritics: bool  # 是否含变音符
    char_script: str      # 字符集: LATIN/CJK/CYRILLIC


@dataclass
class ParsedName:
    """解析后的姓名 / Parsed name"""
    tokens: List[Token]
    first_idx: int  # 第一个非缩写token的索引
    last_idx: int   # 最后一个非缩写token的索引


@dataclass
class Features:
    """特征集 / Feature set"""
    # 基本信息
    token_count: int = 0
    has_initials: bool = False

    # 中文姓氏
    first_is_cn_surname: bool = False
    last_is_cn_surname: bool = False

    # 西方姓氏
    first_is_west_surname: bool = False
    last_is_west_surname: bool = False

    # 拼音合法性
    first_pinyin_ok: bool = False
    last_pinyin_ok: bool = False
    first_pinyin_syllables: int = 0
    last_pinyin_syllables: int = 0

    # 机构
    cn_affiliation: bool = False
    west_affiliation: bool = False


@dataclass
class NameDecision:
    """姓名决策结果 / Name decision result"""
    order: str                     # "family_first" | "given_first" | "unknown"
    confidence: float              # [0.0, 1.0]
    mode: str                      # "CHINESE" | "WESTERN" | "MIXED"
    reason_codes: List[str] = field(default_factory=list)  # 推理代码列表


@dataclass
class NameRecord:
    """姓名记录 / Name record"""
    record_id: str
    source: str = "DEFAULT"          # CROSSREF / ORCID / ISTINA
    person_id: Optional[str] = None
    publication_id: Optional[str] = None
    name_raw: str = ""
    affiliation_raw: Optional[str] = None
    lang_hint: Optional[str] = None


# ========== 辅助函数 Utility Functions ==========

def strip_diacritics(s: str) -> str:
    """去除变音符 / Remove diacritics"""
    import unicodedata
    nfd = unicodedata.normalize('NFD', s)
    return ''.join(c for c in nfd if not unicodedata.combining(c))


def detect_script(s: str) -> str:
    """检测字符集 / Detect character script"""
    if re.search(r'[\u4e00-\u9fff]', s):
        return "CJK"
    if re.search(r'[\u0400-\u04ff]', s):
        return "CYRILLIC"
    return "LATIN"


# ========== 模块1: 预处理与分词 Module 1: Preprocessing ==========

def preprocess_name(name_raw: str) -> ParsedName:
    """
    预处理姓名并分词
    Preprocess and tokenize name

    Args:
        name_raw: 原始姓名字符串

    Returns:
        ParsedName对象
    """
    # 1. 正规化
    s = name_raw.strip()
    s = re.sub(r'[,\(\)\[\]]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # 2. 分词
    rough_tokens = s.split()

    tokens = []
    for t in rough_tokens:
        norm = t.strip()
        if not norm:
            continue

        ascii_form = strip_diacritics(norm.lower())
        is_initial = bool(re.fullmatch(r'[A-Z](\.[A-Z])*\.?', norm))
        has_diacritics = (norm.lower() != ascii_form)
        char_script = detect_script(norm)

        tokens.append(Token(
            raw=norm,
            norm=norm.lower(),
            ascii=ascii_form,
            is_initial=is_initial,
            has_diacritics=has_diacritics,
            char_script=char_script
        ))

    # 3. 确定首尾索引（排除缩写）
    non_initial_indices = [i for i, t in enumerate(tokens) if not t.is_initial]

    if len(non_initial_indices) >= 2:
        first_idx = non_initial_indices[0]
        last_idx = non_initial_indices[-1]
    elif len(tokens) >= 2:
        first_idx = 0
        last_idx = len(tokens) - 1
    else:
        first_idx = -1
        last_idx = -1

    return ParsedName(
        tokens=tokens,
        first_idx=first_idx,
        last_idx=last_idx
    )


# ========== 模块2: 模式识别 Module 2: Mode Detection ==========

def detect_mode(
    record: NameRecord,
    parsed: ParsedName,
    cfg: SourceConfig
) -> str:
    """
    检测姓名文化模式
    Detect name cultural mode

    Returns:
        "CHINESE" | "WESTERN" | "MIXED"
    """
    if parsed.first_idx < 0 or parsed.last_idx < 0:
        return "MIXED"

    score_cn = 0.0
    score_west = 0.0

    first = parsed.tokens[parsed.first_idx]
    last = parsed.tokens[parsed.last_idx]

    # === 中文证据 Chinese Evidence ===

    # CN1: CJK字符
    if any(tok.char_script == "CJK" for tok in parsed.tokens):
        score_cn += 0.9

    # CN2: 中文姓氏
    if is_surname_pinyin(first.ascii):
        score_cn += 0.4
    if is_surname_pinyin(last.ascii):
        score_cn += 0.2

    # CN3: 拼音合法性
    for tok in [first, last]:
        is_valid, syl_count, _ = is_valid_pinyin_name(tok.ascii)
        if is_valid and 2 <= syl_count <= 3:
            score_cn += 0.2

    # CN4: 中国机构
    if record.affiliation_raw:
        affil_info = analyze_affiliation(record.affiliation_raw)
        if affil_info and affil_info.is_chinese:
            score_cn += 0.4

    # === 西方证据 Western Evidence ===

    # W1: 西方姓氏后缀
    for tok in [first, last]:
        if has_western_suffix(tok.ascii):
            score_west += 0.5

    # W2: 变音符
    if any(tok.has_diacritics for tok in parsed.tokens):
        score_west += 0.3

    # W3: 西方常见姓氏
    if is_common_western_surname(last.ascii):
        score_west += 0.5

    # W4: 辅音簇
    for tok in [first, last]:
        if has_western_consonant_cluster(tok.ascii):
            score_west += 0.3

    # === 数据源先验 Source Prior ===
    if record.source in ("CROSSREF", "ORCID", "crossref", "orcid"):
        score_west += 0.2
    if record.source in ("ISTINA", "istina", "ИСТИНА"):
        score_cn += 0.2

    # === 模式判定 Mode Decision ===
    if score_cn >= score_west + 0.3 and score_cn >= 0.5:
        return "CHINESE"
    if score_west >= score_cn + 0.3 and score_west >= 0.5:
        return "WESTERN"
    return "MIXED"


# ========== 模块3: 特征提取 Module 3: Feature Extraction ==========

def extract_features(
    record: NameRecord,
    parsed: ParsedName,
    cfg: SourceConfig,
    mode: str
) -> Features:
    """
    提取特征
    Extract features

    Args:
        record: 姓名记录
        parsed: 解析后的姓名
        cfg: 配置
        mode: 模式

    Returns:
        Features对象
    """
    f = Features()

    if parsed.first_idx < 0 or parsed.last_idx < 0:
        return f

    tokens = parsed.tokens
    first = tokens[parsed.first_idx]
    last = tokens[parsed.last_idx]

    f.token_count = len(tokens)
    f.has_initials = any(t.is_initial for t in tokens)

    # 机构分析
    if record.affiliation_raw:
        affil_info = analyze_affiliation(record.affiliation_raw)
        if affil_info:
            f.cn_affiliation = affil_info.is_chinese
            f.west_affiliation = not affil_info.is_chinese and bool(affil_info.country)

    # 中文姓氏
    f.first_is_cn_surname = is_surname_pinyin(first.ascii)
    f.last_is_cn_surname = is_surname_pinyin(last.ascii)

    # 西方姓氏
    f.first_is_west_surname = is_common_western_surname(first.ascii) or is_likely_western_name(first.ascii)
    f.last_is_west_surname = is_common_western_surname(last.ascii) or is_likely_western_name(last.ascii)

    # 拼音合法性
    is_valid_first, syl_first, _ = is_valid_pinyin_name(first.ascii)
    is_valid_last, syl_last, _ = is_valid_pinyin_name(last.ascii)

    f.first_pinyin_ok = is_valid_first
    f.last_pinyin_ok = is_valid_last
    f.first_pinyin_syllables = syl_first
    f.last_pinyin_syllables = syl_last

    return f


# ========== 模块4: 决策引擎 Module 4: Decision Engine ==========

def decide_chinese(
    record: NameRecord,
    parsed: ParsedName,
    f: Features,
    cfg: SourceConfig
) -> NameDecision:
    """
    Chinese模式决策
    Chinese mode decision

    Args:
        record: 姓名记录
        parsed: 解析后的姓名
        f: 特征
        cfg: 配置

    Returns:
        NameDecision对象
    """
    # 先验分数
    score_fam = cfg.chinese_prior_fam
    score_giv = cfg.chinese_prior_giv
    reasons = []

    first_token = parsed.tokens[parsed.first_idx]
    last_token = parsed.tokens[parsed.last_idx]

    # === 特征1: 姓氏位置证据 ===

    if f.first_is_cn_surname and not f.last_is_cn_surname:
        score_fam += CHINESE_FEATURE_WEIGHTS["CN_SURNAME_FIRST_ONLY"]
        reasons.append("CN_SURNAME_FIRST_ONLY")

    if f.last_is_cn_surname and not f.first_is_cn_surname:
        score_giv += CHINESE_FEATURE_WEIGHTS["CN_SURNAME_LAST_ONLY"]
        reasons.append("CN_SURNAME_LAST_ONLY")

    # 双姓逻辑
    if f.first_is_cn_surname and f.last_is_cn_surname:
        # ISTINA数据源: 强制family_first (俄中数据以中文顺序为主)
        if record.source in ("ISTINA", "istina", "ИСТИНА"):
            score_fam += CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_DEFAULT"]
            reasons.append("CN_SURNAME_DOUBLE_DEFAULT_FAM_ISTINA")
        else:
            # 其他数据源: 使用频率逻辑
            r_first = get_surname_frequency_rank(first_token.ascii)
            r_last = get_surname_frequency_rank(last_token.ascii)

            if r_first and r_last and abs(r_first - r_last) > 20:
                if r_last < r_first:  # last更常见
                    score_giv += CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"]
                    reasons.append(f"CN_SURNAME_DOUBLE_FREQ_LAST({r_last}<{r_first})")
                else:  # first更常见
                    score_fam += CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"]
                    reasons.append(f"CN_SURNAME_DOUBLE_FREQ_FIRST({r_first}<{r_last})")
            else:
                # 频率差距不大,默认family_first
                score_fam += CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_DEFAULT"]
                reasons.append("CN_SURNAME_DOUBLE_DEFAULT_FAM")

    # === 特征2: 拼音名字模式 ===

    if f.first_pinyin_ok and 2 <= f.first_pinyin_syllables <= 3:
        score_giv += CHINESE_FEATURE_WEIGHTS["FIRST_VALID_PY_NAME"]
        reasons.append(f"FIRST_VALID_PY_NAME({f.first_pinyin_syllables}syl)")

    if f.last_pinyin_ok and 2 <= f.last_pinyin_syllables <= 3:
        score_fam += CHINESE_FEATURE_WEIGHTS["LAST_VALID_PY_NAME"]
        reasons.append(f"LAST_VALID_PY_NAME({f.last_pinyin_syllables}syl)")

    # === 特征3: 单音节优化 (v8.0新增) ===

    if f.first_pinyin_ok and f.first_pinyin_syllables == 1:
        score_giv += CHINESE_FEATURE_WEIGHTS["FIRST_SINGLE_SYLLABLE"]
        reasons.append("FIRST_SINGLE_SYLLABLE")

    if f.last_pinyin_ok and f.last_pinyin_syllables == 1:
        score_fam += CHINESE_FEATURE_WEIGHTS["LAST_SINGLE_SYLLABLE"]
        reasons.append("LAST_SINGLE_SYLLABLE")

    # === 特征4: 机构证据 ===

    if f.cn_affiliation:
        score_fam += CHINESE_FEATURE_WEIGHTS["CN_AFFILIATION"]
        score_giv += CHINESE_FEATURE_WEIGHTS["CN_AFFILIATION"]
        reasons.append("CN_AFFILIATION")

    # === 特征5: 两token特殊处理 ===

    if f.token_count == 2 and f.last_is_cn_surname and not f.first_is_cn_surname:
        if record.source in ("CROSSREF", "ORCID", "crossref", "orcid"):
            score_giv += CHINESE_FEATURE_WEIGHTS["TWO_TOKENS_CN_SURNAME_LAST"]
            reasons.append("TWO_TOKENS_CN_SURNAME_LAST_INTL")
        else:
            score_giv += CHINESE_FEATURE_WEIGHTS["TWO_TOKENS_SINGLE_SYLLABLE"]
            reasons.append("TWO_TOKENS_CN_SURNAME_LAST_ISTINA")

    # === 决策 ===

    delta = score_fam - score_giv

    if abs(delta) < cfg.threshold_cn_unknown:
        return NameDecision(
            order="unknown",
            confidence=0.5,
            mode="CHINESE",
            reason_codes=reasons + ["DELTA_SMALL_CN"]
        )

    if delta > 0:
        conf = min(sigmoid(delta), 0.95)
        return NameDecision("family_first", conf, "CHINESE", reasons)
    else:
        conf = min(sigmoid(-delta), 0.95)
        return NameDecision("given_first", conf, "CHINESE", reasons)


def decide_western(
    record: NameRecord,
    parsed: ParsedName,
    f: Features,
    cfg: SourceConfig
) -> NameDecision:
    """
    Western模式决策
    Western mode decision
    """
    score_fam = cfg.western_prior_fam
    score_giv = cfg.western_prior_giv
    reasons = []

    # === 特征1: 西方姓氏证据 ===

    if f.last_is_west_surname:
        score_giv += WESTERN_FEATURE_WEIGHTS["WEST_SURNAME_LAST"]
        reasons.append("WEST_SURNAME_LAST")

    if f.first_is_west_surname and not f.last_is_west_surname:
        score_fam += WESTERN_FEATURE_WEIGHTS["WEST_SURNAME_FIRST"]
        reasons.append("WEST_SURNAME_FIRST")

    # === 特征2: 中文证据（反向） ===

    if f.first_is_cn_surname and f.cn_affiliation:
        score_fam += WESTERN_FEATURE_WEIGHTS["CN_SURNAME_FIRST_WITH_CN_AFFIL"]
        reasons.append("CN_SURNAME_FIRST_WITH_CN_AFFIL")

    if f.last_is_cn_surname and f.cn_affiliation:
        score_giv += WESTERN_FEATURE_WEIGHTS["CN_SURNAME_LAST_WITH_CN_AFFIL"]
        reasons.append("CN_SURNAME_LAST_WITH_CN_AFFIL")

    # === 特征3: 默认推断 (v7.0核心特性保留) ===

    if not (f.first_is_cn_surname or f.last_is_cn_surname or f.cn_affiliation):
        score_giv += WESTERN_FEATURE_WEIGHTS["NO_CN_EVIDENCE_DEFAULT"]
        reasons.append("NO_CN_EVIDENCE_DEFAULT_GIVEN")

    # === 决策 ===

    delta = score_fam - score_giv

    if abs(delta) < cfg.threshold_west_unknown:
        # Western模式下,tie时强制given_first
        return NameDecision("given_first", 0.55, "WESTERN",
                           reasons + ["FORCED_GIVEN_ON_TIE"])

    if delta > 0:
        conf = min(sigmoid(delta), 0.95)
        return NameDecision("family_first", conf, "WESTERN", reasons)
    else:
        conf = min(sigmoid(-delta), 0.95)
        return NameDecision("given_first", conf, "WESTERN", reasons)


def decide_mixed(
    record: NameRecord,
    parsed: ParsedName,
    f: Features,
    cfg: SourceConfig
) -> NameDecision:
    """
    Mixed模式决策
    Mixed mode decision
    """
    score_fam = cfg.mixed_prior_fam
    score_giv = cfg.mixed_prior_giv
    reasons = []

    # === 姓氏+机构组合 ===

    if f.first_is_cn_surname and f.cn_affiliation:
        score_fam += MIXED_FEATURE_WEIGHTS["CN_SURNAME_FIRST_CN_AFFIL"]
        reasons.append("CN_SURNAME_FIRST_CN_AFFIL_MIXED")

    if f.last_is_cn_surname and f.cn_affiliation:
        score_giv += MIXED_FEATURE_WEIGHTS["CN_SURNAME_LAST_CN_AFFIL"]
        reasons.append("CN_SURNAME_LAST_CN_AFFIL_MIXED")

    # === 仅姓氏证据 ===

    if f.first_is_cn_surname and not f.last_is_cn_surname:
        score_fam += MIXED_FEATURE_WEIGHTS["CN_SURNAME_ONLY"]
        reasons.append("CN_SURNAME_FIRST_ONLY_MIXED")

    if f.last_is_cn_surname and not f.first_is_cn_surname:
        score_giv += MIXED_FEATURE_WEIGHTS["CN_SURNAME_ONLY"]
        reasons.append("CN_SURNAME_LAST_ONLY_MIXED")

    # === 无匹配默认 ===

    if not f.first_is_cn_surname and not f.last_is_cn_surname:
        score_giv += MIXED_FEATURE_WEIGHTS["NO_MATCH_DEFAULT"]
        reasons.append("NO_MATCH_DEFAULT_GIVEN")

    # === 决策 ===

    delta = score_fam - score_giv

    if abs(delta) < cfg.threshold_mixed_unknown:
        return NameDecision("unknown", 0.4, "MIXED",
                           reasons + ["DELTA_SMALL_MIXED"])

    if delta > 0:
        conf = min(sigmoid(delta), 0.9)
        return NameDecision("family_first", conf, "MIXED", reasons)
    else:
        conf = min(sigmoid(-delta), 0.9)
        return NameDecision("given_first", conf, "MIXED", reasons)


# ========== 模块5: 局部决策 Module 5: Local Decision ==========

def local_decision(record: NameRecord, cfg: SourceConfig) -> NameDecision:
    """
    单条记录局部决策
    Local decision for single record

    Args:
        record: 姓名记录
        cfg: 配置

    Returns:
        NameDecision对象
    """
    # 1. 预处理
    parsed = preprocess_name(record.name_raw)

    if parsed.first_idx < 0 or parsed.last_idx < 0 or len(parsed.tokens) < 2:
        return NameDecision("unknown", 0.0, "MIXED", ["INVALID_FORMAT"])

    # 2. 缩写检测（优先级最高）
    # 支持带点和不带点的缩写: A, A., A.B., AB等
    abbrev_pattern = r'^[A-Z](\.[A-Z])*\.?$'
    single_letter_pattern = r'^[A-Z]$'  # 单字母也算缩写
    tokens = parsed.tokens

    if len(tokens) == 2:
        # 检测第二个token是否是缩写
        if re.match(abbrev_pattern, tokens[1].raw) or re.match(single_letter_pattern, tokens[1].raw):
            return NameDecision("family_first", 1.0, "ABBREVIATION",
                               [f"ABBREV_{tokens[0].raw}_{tokens[1].raw}"])
        # 检测第一个token是否是缩写（倒置情况）
        if re.match(abbrev_pattern, tokens[0].raw) or re.match(single_letter_pattern, tokens[0].raw):
            return NameDecision("given_first", 0.85, "ABBREVIATION",
                               [f"ABBREV_{tokens[0].raw}_{tokens[1].raw}_REVERSED"])

    if len(tokens) >= 3:
        # 所有非第一个token都是缩写
        if all(re.match(abbrev_pattern, t.raw) or re.match(single_letter_pattern, t.raw) for t in tokens[1:]):
            return NameDecision("family_first", 1.0, "ABBREVIATION",
                               [f"ABBREV_{tokens[0].raw}_+"])

    # 3. 模式识别
    mode = detect_mode(record, parsed, cfg)

    # 4. 特征提取
    feats = extract_features(record, parsed, cfg, mode)

    # 5. 决策
    if mode == "CHINESE":
        return decide_chinese(record, parsed, feats, cfg)
    elif mode == "WESTERN":
        return decide_western(record, parsed, feats, cfg)
    else:
        return decide_mixed(record, parsed, feats, cfg)


# ========== 模块6: 批量一致性 Module 6: Batch Consistency ==========

def adjust_by_person(
    records: List[NameRecord],
    decisions: Dict[str, NameDecision],
    cfg: SourceConfig
) -> Dict[str, NameDecision]:
    """
    基于person_id的一致性调整
    Person-based consistency adjustment
    """
    # 按person_id分组
    groups = defaultdict(list)
    for rec in records:
        if rec.person_id:
            groups[rec.person_id].append(rec.record_id)

    for pid, rec_ids in groups.items():
        # 收集高置信度决策
        local_decisions = [decisions[rid] for rid in rec_ids
                           if rid in decisions and decisions[rid].order != "unknown"]

        if not local_decisions:
            continue

        fam = [d for d in local_decisions
               if d.order == "family_first" and d.confidence >= cfg.person_conf_thresh]
        giv = [d for d in local_decisions
               if d.order == "given_first" and d.confidence >= cfg.person_conf_thresh]

        if len(fam) == 0 and len(giv) == 0:
            continue

        target_order = "family_first" if len(fam) >= len(giv) else "given_first"

        # 覆盖低置信度或unknown
        for rid in rec_ids:
            if rid not in decisions:
                continue
            d = decisions[rid]
            if d.order == "unknown" or d.confidence < cfg.person_override_thresh:
                decisions[rid] = NameDecision(
                    order=target_order,
                    confidence=max(d.confidence, cfg.person_override_conf),
                    mode=d.mode,
                    reason_codes=d.reason_codes + ["PERSON_CONSISTENCY_OVERRIDE"]
                )

    return decisions


def adjust_by_publication(
    records: List[NameRecord],
    decisions: Dict[str, NameDecision],
    cfg: SourceConfig
) -> Dict[str, NameDecision]:
    """
    基于publication_id的一致性调整
    Publication-based consistency adjustment
    """
    # 按publication_id分组
    groups = defaultdict(list)
    for rec in records:
        if rec.publication_id:
            groups[rec.publication_id].append(rec.record_id)

    for pub_id, rec_ids in groups.items():
        fam = [decisions[rid] for rid in rec_ids if rid in decisions
               and decisions[rid].order == "family_first"
               and decisions[rid].confidence >= cfg.pub_conf_thresh]
        giv = [decisions[rid] for rid in rec_ids if rid in decisions
               and decisions[rid].order == "given_first"
               and decisions[rid].confidence >= cfg.pub_conf_thresh]

        if len(fam) == 0 and len(giv) == 0:
            continue

        if abs(len(fam) - len(giv)) < cfg.pub_dominance_min_diff:
            continue  # 无明显多数

        target_order = "family_first" if len(fam) > len(giv) else "given_first"

        for rid in rec_ids:
            if rid not in decisions:
                continue
            d = decisions[rid]
            if d.order == "unknown" and d.confidence <= cfg.pub_override_thresh:
                decisions[rid] = NameDecision(
                    order=target_order,
                    confidence=cfg.pub_override_conf,
                    mode=d.mode,
                    reason_codes=d.reason_codes + ["PUB_PATTERN_OVERRIDE"]
                )

    return decisions


# ========== 主接口 Main Interface ==========

def identify_surname_position_v8(
    original_name: str,
    lastname: Optional[str] = None,
    firstname: Optional[str] = None,
    affiliation: Optional[str] = None,
    mode_hint: Optional[str] = None,
    source: Optional[str] = None,
    person_id: Optional[str] = None,
    publication_id: Optional[str] = None,
) -> Tuple[Optional[str], float, str]:
    """
    v8.0 姓氏位置识别算法（单条记录接口）
    v8.0 Surname Position Identification Algorithm (Single record interface)

    Args:
        original_name: 原始姓名（必需）
        lastname: 姓氏（保留兼容，v8不使用）
        firstname: 名字（保留兼容，v8不使用）
        affiliation: 机构信息（可选）
        mode_hint: 模式提示（保留兼容，v8不使用）
        source: 数据源 ("CROSSREF" / "ORCID" / "ISTINA")
        person_id: 作者ID（单条调用时不使用）
        publication_id: 文章ID（单条调用时不使用）

    Returns:
        - order: "family_first" | "given_first" | "unknown"
        - confidence: float [0.0, 1.0]
        - reason: str (推理依据)
    """
    # 创建记录
    record = NameRecord(
        record_id="single",
        source=source or "DEFAULT",
        person_id=person_id,
        publication_id=publication_id,
        name_raw=original_name,
        affiliation_raw=affiliation,
        lang_hint=mode_hint,
    )

    # 获取配置
    cfg = get_config(source)

    # 局部决策
    decision = local_decision(record, cfg)

    # 格式化reason
    reason = f"{decision.mode}: {', '.join(decision.reason_codes)}"

    return (decision.order, decision.confidence, reason)


def batch_identify_surname_position_v8(
    records: List[NameRecord],
    source: Optional[str] = None,
    enable_person_consistency: bool = True,
    enable_pub_consistency: bool = True,
) -> Dict[str, NameDecision]:
    """
    v8.0 批量姓氏位置识别（支持一致性调整）
    v8.0 Batch surname position identification (with consistency adjustment)

    Args:
        records: 姓名记录列表
        source: 数据源（如果records中已指定则优先使用records中的）
        enable_person_consistency: 是否启用person一致性
        enable_pub_consistency: 是否启用publication一致性

    Returns:
        Dict[record_id, NameDecision]
    """
    # 获取配置
    cfg = get_config(source)

    # 1. 局部决策
    decisions = {}
    for rec in records:
        rec_cfg = get_config(rec.source) if rec.source else cfg
        decisions[rec.record_id] = local_decision(rec, rec_cfg)

    # 2. 一致性调整
    if enable_person_consistency:
        decisions = adjust_by_person(records, decisions, cfg)

    if enable_pub_consistency:
        decisions = adjust_by_publication(records, decisions, cfg)

    return decisions


# 向后兼容
identify_surname_position = identify_surname_position_v8
