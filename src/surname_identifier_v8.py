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
from typing import Any, Optional, Tuple, List, Dict
from dataclasses import dataclass, field, replace
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.surname_pinyin_db import is_surname_pinyin, get_surname_from_pinyin
from data.surname_frequency import (
    compare_surname_frequency_share,
    get_surname_frequency_rank,
)
from data.non_chinese_surnames import is_strong_non_chinese_surname
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
    get_ablation_config,
    SourceConfig,
    CHINESE_FEATURE_WEIGHTS,
    WESTERN_FEATURE_WEIGHTS,
    MIXED_FEATURE_WEIGHTS,
    sigmoid,
)

ISTINA_SOURCE_NAMES = {"ISTINA", "istina", "袠小孝袠袧袗"}


def _format_share_value(share: float) -> str:
    """Format share values for compact reason codes."""
    return f"{share:.4f}".rstrip("0").rstrip(".")


def _apply_double_surname_frequency_rule(
    first_token: "Token",
    last_token: "Token",
) -> Tuple[float, float, str]:
    """
    Apply the configured double-surname frequency rule for non-ISTINA sources.
    """
    ablation_config = get_ablation_config()
    strategy = ablation_config.surname_freq_strategy
    share_ratio_threshold = ablation_config.surname_share_ratio_threshold

    if strategy == "share_ratio":
        share_comparison = compare_surname_frequency_share(first_token.ascii, last_token.ascii)
        share1 = share_comparison["share1"]
        share2 = share_comparison["share2"]
        has_share1 = share_comparison["has_share1"]
        has_share2 = share_comparison["has_share2"]

        if has_share1 and has_share2 and share_comparison["share_ratio"] >= share_ratio_threshold:
            if share1 > share2:
                return (
                    CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"],
                    0.0,
                    f"CN_SURNAME_DOUBLE_FREQ_FIRST({_format_share_value(share1)}>{_format_share_value(share2)})",
                )
            if share2 > share1:
                return (
                    0.0,
                    CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"],
                    f"CN_SURNAME_DOUBLE_FREQ_LAST({_format_share_value(share2)}>{_format_share_value(share1)})",
                )
        elif has_share1 != has_share2:
            known_share = share1 if has_share1 else share2
            if known_share >= 0.10:
                if has_share1:
                    return (
                        CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"],
                        0.0,
                        f"CN_SURNAME_DOUBLE_FREQ_FIRST({_format_share_value(share1)}>{_format_share_value(share2)})",
                    )
                return (
                    0.0,
                    CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"],
                    f"CN_SURNAME_DOUBLE_FREQ_LAST({_format_share_value(share2)}>{_format_share_value(share1)})",
                )

        return (
            CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_DEFAULT"],
            0.0,
            "CN_SURNAME_DOUBLE_DEFAULT_FAM",
        )

    if strategy == "freq_disabled":
        return (
            CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_DEFAULT"],
            0.0,
            "CN_SURNAME_DOUBLE_DEFAULT_FAM",
        )

    r_first = get_surname_frequency_rank(first_token.ascii)
    r_last = get_surname_frequency_rank(last_token.ascii)

    if abs(r_first - r_last) > 20:
        if r_last < r_first:
            return (
                0.0,
                CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"],
                f"CN_SURNAME_DOUBLE_FREQ_LAST({r_last}<{r_first})",
            )
        return (
            CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_FREQ"],
            0.0,
            f"CN_SURNAME_DOUBLE_FREQ_FIRST({r_first}<{r_last})",
        )

    return (
        CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_DEFAULT"],
        0.0,
        "CN_SURNAME_DOUBLE_DEFAULT_FAM",
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
    first_is_known_non_chinese_surname: bool = False
    last_is_known_non_chinese_surname: bool = False

    # 拼音合法性
    first_pinyin_ok: bool = False
    last_pinyin_ok: bool = False
    first_pinyin_syllables: int = 0
    last_pinyin_syllables: int = 0

    # 机构
    cn_affiliation: bool = False
    west_affiliation: bool = False

    has_split_fields: bool = False
    field_split_exact_family_first: bool = False
    field_split_exact_given_first: bool = False
    field_split_mismatch: bool = False
    field_family_matches_full_name: bool = False
    field_family_multitoken: bool = False
    field_given_family_duplicate: bool = False
    field_firstname_has_cjk: bool = False
    field_lastname_has_cjk: bool = False
    field_family_fullname_given_cjk: bool = False
    field_given_compound_surname_prefix: bool = False
    field_given_compound_surname_single_token: bool = False
    field_given_head_surname_family_non_surname: bool = False


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
    firstname_raw: Optional[str] = None
    lastname_raw: Optional[str] = None
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
    s = re.sub(r'\b([A-Z])\.(?=[A-Z][a-z])', r'\1. ', s)
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

def _normalize_field_text(value: Optional[str]) -> str:
    """Normalize split-field content before secondary parsing."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip())


def _parsed_field(value: Optional[str]) -> ParsedName:
    """Parse a firstname/lastname field with the main tokenizer."""
    return preprocess_name(_normalize_field_text(value))


def _token_ascii_sequence(tokens: List[Token]) -> List[str]:
    """Return a lowercased token sequence for exact-order checks."""
    return [tok.ascii.lower() for tok in tokens if tok.ascii]


def _contains_cjk_text(value: Optional[str]) -> bool:
    """Detect Han characters in split fields."""
    return bool(value and re.search(r"[\u4e00-\u9fff]", value))


def _is_compound_surname_pinyin(text: str) -> bool:
    """Check whether a pinyin form maps to a compound Chinese surname."""
    if not text:
        return False
    return any(len(surname) > 1 for surname in get_surname_from_pinyin(text))


def _extract_compound_surname_prefix(tokens: List[Token]) -> Optional[str]:
    """Return a compound-surname prefix at the start of a given-name field."""
    if not tokens:
        return None

    candidates = [tokens[0].ascii.lower()]
    if len(tokens) >= 2:
        head1 = tokens[0].ascii.lower()
        head2 = tokens[1].ascii.lower()
        candidates.extend([head1 + head2, f"{head1} {head2}"])

    for candidate in candidates:
        if _is_compound_surname_pinyin(candidate):
            return candidate
    return None


def _is_external_metadata_source(source: Optional[str]) -> bool:
    """External metadata can use stronger split-field evidence than ISTINA."""
    return (source or "DEFAULT") not in ISTINA_SOURCE_NAMES


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
    first_is_known_non_chinese = is_strong_non_chinese_surname(first.ascii)
    last_is_known_non_chinese = is_strong_non_chinese_surname(last.ascii)

    # === 中文证据 Chinese Evidence ===

    # CN1: CJK字符
    if any(tok.char_script == "CJK" for tok in parsed.tokens):
        score_cn += 0.9

    # CN2: 中文姓氏
    if is_surname_pinyin(first.ascii):
        score_cn += 0.4
    if is_surname_pinyin(last.ascii):
        score_cn += 0.4 # FIXED

    # CN3: 拼音合法性
    for tok in [first, last]:
        is_valid, syl_count, _ = is_valid_pinyin_name(tok.ascii)
        if is_valid and 2 <= syl_count <= 3:
            score_cn += 0.2

    # CN4: 中国机构
    if record.affiliation_raw:
        affil_info = analyze_affiliation(record.affiliation_raw)
        if affil_info and affil_info.is_chinese:
            score_cn += 0.1

    # === 西方证据 Western Evidence ===

    # W0: curated non-Chinese surname evidence. This is deliberately stronger
    # than pinyin compatibility, which is shared by some Japanese, Korean, and
    # Vietnamese romanizations.
    if first_is_known_non_chinese or last_is_known_non_chinese:
        score_west += 0.8

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

    split_first = _parsed_field(record.firstname_raw)
    split_last = _parsed_field(record.lastname_raw)
    split_first_tokens = split_first.tokens
    split_last_tokens = split_last.tokens

    if split_first_tokens or split_last_tokens:
        f.has_split_fields = True

    original_ascii = _token_ascii_sequence(parsed.tokens)
    split_first_ascii = _token_ascii_sequence(split_first_tokens)
    split_last_ascii = _token_ascii_sequence(split_last_tokens)

    if split_first_ascii and split_last_ascii:
        if original_ascii == split_last_ascii + split_first_ascii:
            f.field_split_exact_family_first = True
        elif original_ascii == split_first_ascii + split_last_ascii:
            f.field_split_exact_given_first = True

    if split_last_ascii and split_last_ascii == original_ascii and split_first_ascii:
        f.field_family_matches_full_name = True

    f.field_family_multitoken = len(split_last_tokens) >= 2
    f.field_firstname_has_cjk = _contains_cjk_text(record.firstname_raw)
    f.field_lastname_has_cjk = _contains_cjk_text(record.lastname_raw)
    f.field_given_family_duplicate = bool(
        split_first_ascii and split_last_ascii and split_first_ascii == split_last_ascii
    )

    if (
        f.field_family_matches_full_name
        and f.field_firstname_has_cjk
        and not f.field_lastname_has_cjk
    ):
        f.field_family_fullname_given_cjk = True

    compound_prefix = _extract_compound_surname_prefix(split_first_tokens)
    if compound_prefix:
        if len(split_first_tokens) >= 2:
            f.field_given_compound_surname_prefix = True
        else:
            f.field_given_compound_surname_single_token = True

    if split_first_tokens and split_last_tokens:
        first_head = split_first_tokens[0].ascii.lower()
        last_head = split_last_tokens[0].ascii.lower()
        last_joined = "".join(tok.ascii.lower() for tok in split_last_tokens if tok.ascii)
        lastname_looks_like_surname = is_surname_pinyin(last_head) or is_surname_pinyin(last_joined)
        if is_surname_pinyin(first_head) and not lastname_looks_like_surname:
            if len(split_first_tokens) >= 2 or f.field_given_compound_surname_prefix:
                f.field_given_head_surname_family_non_surname = True

    if (
        f.has_split_fields
        and not f.field_split_exact_family_first
        and not f.field_split_exact_given_first
        and (
            f.field_family_matches_full_name
            or f.field_given_family_duplicate
            or f.field_family_fullname_given_cjk
            or f.field_given_compound_surname_prefix
            or f.field_given_head_surname_family_non_surname
        )
    ):
        f.field_split_mismatch = True

    # 中文姓氏
    f.first_is_cn_surname = is_surname_pinyin(first.ascii)
    f.last_is_cn_surname = is_surname_pinyin(last.ascii)

    # 西方姓氏
    f.first_is_known_non_chinese_surname = is_strong_non_chinese_surname(first.ascii)
    f.last_is_known_non_chinese_surname = is_strong_non_chinese_surname(last.ascii)
    f.first_is_west_surname = (
        f.first_is_known_non_chinese_surname
        or is_common_western_surname(first.ascii)
        or is_likely_western_name(first.ascii)
    )
    f.last_is_west_surname = (
        f.last_is_known_non_chinese_surname
        or is_common_western_surname(last.ascii)
        or is_likely_western_name(last.ascii)
    )

    # 拼音合法性
    is_valid_first, syl_first, _ = is_valid_pinyin_name(first.ascii)
    is_valid_last, syl_last, _ = is_valid_pinyin_name(last.ascii)

    f.first_pinyin_ok = is_valid_first
    f.last_pinyin_ok = is_valid_last
    f.first_pinyin_syllables = syl_first
    f.last_pinyin_syllables = syl_last

    return f


def _apply_field_structure_evidence(
    record: NameRecord,
    f: Features,
    weight_map: Dict[str, float],
    score_fam: float,
    score_giv: float,
    reasons: List[str],
) -> Tuple[float, float]:
    """Translate split-field checks into soft, explainable evidence."""
    if not f.has_split_fields:
        return score_fam, score_giv

    source_multiplier = 1.0 if _is_external_metadata_source(record.source) else 0.35

    if f.field_split_exact_family_first:
        score_fam += weight_map["FIELD_SPLIT_EXACT_FAMILY"] * source_multiplier
        reasons.append("FIELD_SPLIT_EXACT_FAMILY")

    if f.field_split_exact_given_first:
        score_giv += weight_map["FIELD_SPLIT_EXACT_GIVEN"] * source_multiplier
        reasons.append("FIELD_SPLIT_EXACT_GIVEN")

    if f.field_family_matches_full_name:
        score_fam += weight_map["FIELD_FAMILY_MATCHES_FULL_NAME"] * source_multiplier
        reasons.append("FIELD_FAMILY_MATCHES_FULL_NAME")

    if f.field_family_fullname_given_cjk:
        score_fam += weight_map["FIELD_FAMILY_FULLNAME_GIVEN_CJK"] * source_multiplier
        reasons.append("FIELD_FAMILY_FULLNAME_GIVEN_CJK")

    if f.field_given_head_surname_family_non_surname:
        score_fam += weight_map["FIELD_GIVEN_HEAD_SURNAME_FAMILY_NON_SURNAME"] * source_multiplier
        reasons.append("FIELD_GIVEN_HEAD_SURNAME_FAMILY_NON_SURNAME")

    if f.field_given_compound_surname_prefix:
        score_fam += weight_map["FIELD_GIVEN_COMPOUND_SURNAME_PREFIX"] * source_multiplier
        reasons.append("FIELD_GIVEN_COMPOUND_SURNAME_PREFIX")

    if f.field_given_compound_surname_single_token:
        score_fam += weight_map["FIELD_GIVEN_COMPOUND_SURNAME_SINGLE_TOKEN"] * source_multiplier
        reasons.append("FIELD_GIVEN_COMPOUND_SURNAME_SINGLE_TOKEN_DIAG")

    if f.field_family_multitoken:
        reasons.append("FIELD_FAMILY_MULTITOKEN")

    if f.field_given_family_duplicate:
        reasons.append("FIELD_GIVEN_FAMILY_DUPLICATE")

    if f.field_split_mismatch:
        reasons.append("FIELD_SPLIT_MISMATCH")

    return score_fam, score_giv


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
            score_fam += CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_ISTINA_DEFAULT"]
            reasons.append("CN_SURNAME_DOUBLE_DEFAULT_FAM_ISTINA")
        else:
            # 其他数据源: 使用频率逻辑
            fam_delta, giv_delta, reason = _apply_double_surname_frequency_rule(
                first_token,
                last_token,
            )
            score_fam += fam_delta
            score_giv += giv_delta
            reasons.append(reason)

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

    score_fam, score_giv = _apply_field_structure_evidence(
        record,
        f,
        CHINESE_FEATURE_WEIGHTS,
        score_fam,
        score_giv,
        reasons,
    )

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

    if (
        f.first_is_known_non_chinese_surname
        and not f.last_is_known_non_chinese_surname
    ):
        score_fam += 1.0
        reasons.append("KNOWN_NON_CHINESE_SURNAME_FIRST")

    # === 特征2: 中文证据（反向） ===

    if f.first_is_cn_surname and f.cn_affiliation:
        score_fam += WESTERN_FEATURE_WEIGHTS["CN_SURNAME_FIRST_WITH_CN_AFFIL"]
        reasons.append("CN_SURNAME_FIRST_WITH_CN_AFFIL")

    if f.last_is_cn_surname and f.cn_affiliation:
        score_giv += WESTERN_FEATURE_WEIGHTS["CN_SURNAME_LAST_WITH_CN_AFFIL"]
        reasons.append("CN_SURNAME_LAST_WITH_CN_AFFIL")

    # === 特征3: 默认推断 (v7.0核心特性保留) ===

    if not (
        f.first_is_cn_surname
        or f.last_is_cn_surname
        or f.first_is_known_non_chinese_surname
        or f.last_is_known_non_chinese_surname
        or f.cn_affiliation
    ):
        score_giv += WESTERN_FEATURE_WEIGHTS["NO_CN_EVIDENCE_DEFAULT"]
        reasons.append("NO_CN_EVIDENCE_DEFAULT_GIVEN")

    score_fam, score_giv = _apply_field_structure_evidence(
        record,
        f,
        WESTERN_FEATURE_WEIGHTS,
        score_fam,
        score_giv,
        reasons,
    )

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

    score_fam, score_giv = _apply_field_structure_evidence(
        record,
        f,
        MIXED_FEATURE_WEIGHTS,
        score_fam,
        score_giv,
        reasons,
    )

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
    second_token_is_abbrev = (
        len(tokens) == 2
        and (
            re.match(abbrev_pattern, tokens[1].raw)
            or re.match(single_letter_pattern, tokens[1].raw)
        )
    )
    first_token_is_abbrev = (
        len(tokens) == 2
        and (
            re.match(abbrev_pattern, tokens[0].raw)
            or re.match(single_letter_pattern, tokens[0].raw)
        )
    )
    tail_tokens_are_abbrev = (
        len(tokens) >= 3
        and all(
            re.match(abbrev_pattern, t.raw) or re.match(single_letter_pattern, t.raw)
            for t in tokens[1:]
        )
    )

    # External metadata may already provide a reliable split-field alignment.
    # Treat an exact original_name <-> given/family alignment as decisive for
    # external sources, while still recording when it suppresses abbreviation rules.
    has_abbrev_pattern = second_token_is_abbrev or first_token_is_abbrev or tail_tokens_are_abbrev
    if _is_external_metadata_source(record.source):
        split_first = _parsed_field(record.firstname_raw)
        split_last = _parsed_field(record.lastname_raw)
        split_first_ascii = _token_ascii_sequence(split_first.tokens)
        split_last_ascii = _token_ascii_sequence(split_last.tokens)
        original_ascii = _token_ascii_sequence(parsed.tokens)
        if (
            split_first_ascii
            and split_last_ascii
            and split_first_ascii != split_last_ascii
        ):
            diagnostic_reasons = []
            if len(split_last.tokens) >= 2:
                diagnostic_reasons.append("FIELD_FAMILY_MULTITOKEN")

            compound_prefix = _extract_compound_surname_prefix(split_first.tokens)
            if compound_prefix:
                if len(split_first.tokens) >= 2:
                    diagnostic_reasons.append("FIELD_GIVEN_COMPOUND_SURNAME_PREFIX")
                else:
                    diagnostic_reasons.append("FIELD_GIVEN_COMPOUND_SURNAME_SINGLE_TOKEN_DIAG")

            if split_first.tokens and split_last.tokens:
                first_head = split_first.tokens[0].ascii.lower()
                last_head = split_last.tokens[0].ascii.lower()
                last_joined = "".join(tok.ascii.lower() for tok in split_last.tokens if tok.ascii)
                lastname_looks_like_surname = (
                    is_surname_pinyin(last_head) or is_surname_pinyin(last_joined)
                )
                if is_surname_pinyin(first_head) and not lastname_looks_like_surname:
                    if len(split_first.tokens) >= 2 or compound_prefix:
                        diagnostic_reasons.append("FIELD_GIVEN_HEAD_SURNAME_FAMILY_NON_SURNAME")

            if original_ascii == split_last_ascii + split_first_ascii:
                reasons = [
                    "FIELD_SPLIT_EXACT_FAMILY",
                    "FIELD_STRUCTURE_EXACT_OVERRIDE",
                    *diagnostic_reasons,
                ]
                if has_abbrev_pattern:
                    reasons.append("ABBREV_DEFER_TO_SPLIT_FIELDS")
                return NameDecision(
                    "family_first",
                    0.99,
                    "FIELD_STRUCTURE",
                    reasons,
                )
            if original_ascii == split_first_ascii + split_last_ascii:
                reasons = [
                    "FIELD_SPLIT_EXACT_GIVEN",
                    "FIELD_STRUCTURE_EXACT_OVERRIDE",
                    *diagnostic_reasons,
                ]
                if has_abbrev_pattern:
                    reasons.append("ABBREV_DEFER_TO_SPLIT_FIELDS")
                return NameDecision(
                    "given_first",
                    0.99,
                    "FIELD_STRUCTURE",
                    reasons,
                )

    if len(tokens) == 2:
        # 检测第二个token是否是缩写
        if second_token_is_abbrev:
            return NameDecision("family_first", 1.0, "ABBREVIATION",
                               [f"ABBREV_{tokens[0].raw}_{tokens[1].raw}"])
        # 检测第一个token是否是缩写（倒置情况）
        if first_token_is_abbrev:
            return NameDecision("given_first", 0.85, "ABBREVIATION",
                               [f"ABBREV_{tokens[0].raw}_{tokens[1].raw}_REVERSED"])

    if len(tokens) >= 3:
        # 所有非第一个token都是缩写
        if tail_tokens_are_abbrev:
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
            if d.order == "unknown" and d.confidence < cfg.person_override_thresh:
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
        # A publication may mix Chinese and non-Chinese authors whose normal
        # writing orders differ. Derive a majority separately for each detected
        # cultural mode so Western coauthors cannot rewrite an ambiguous Chinese
        # record (and vice versa).
        same_mode_only = get_ablation_config().publication_same_mode_only
        target_by_mode: Dict[str, str] = {}
        modes = (
            {
                decisions[rid].mode
                for rid in rec_ids
                if rid in decisions
            }
            if same_mode_only
            else {"*"}
        )
        for mode in modes:
            fam = [
                decisions[rid]
                for rid in rec_ids
                if rid in decisions
                and (mode == "*" or decisions[rid].mode == mode)
                and decisions[rid].order == "family_first"
                and decisions[rid].confidence >= cfg.pub_conf_thresh
            ]
            giv = [
                decisions[rid]
                for rid in rec_ids
                if rid in decisions
                and (mode == "*" or decisions[rid].mode == mode)
                and decisions[rid].order == "given_first"
                and decisions[rid].confidence >= cfg.pub_conf_thresh
            ]

            if not fam and not giv:
                continue
            if abs(len(fam) - len(giv)) < cfg.pub_dominance_min_diff:
                continue
            target_by_mode[mode] = (
                "family_first" if len(fam) > len(giv) else "given_first"
            )

        for rid in rec_ids:
            if rid not in decisions:
                continue
            d = decisions[rid]
            target_order = target_by_mode.get(d.mode if same_mode_only else "*")
            if (
                target_order
                and d.order == "unknown"
                and d.confidence <= cfg.pub_override_thresh
            ):
                decisions[rid] = NameDecision(
                    order=target_order,
                    confidence=cfg.pub_override_conf,
                    mode=d.mode,
                    reason_codes=(
                        d.reason_codes
                        + ["PUB_PATTERN_OVERRIDE"]
                        + (["PUB_SAME_MODE_EVIDENCE"] if same_mode_only else [])
                    )
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
        firstname_raw=firstname,
        lastname_raw=lastname,
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


def _coerce_batch_record(
    record: Any,
    index: int,
    default_source: Optional[str] = None,
) -> NameRecord:
    """Accept NameRecord or common Crossref-style dicts in the batch API."""
    if isinstance(record, NameRecord):
        if default_source and (not record.source or record.source == "DEFAULT"):
            return replace(record, source=default_source)
        return record

    if not isinstance(record, dict):
        raise TypeError(
            "batch_identify_surname_position_v8 expects NameRecord or dict records"
        )

    firstname_raw = (
        record.get("firstname_raw")
        or record.get("firstname")
        or record.get("given")
        or record.get("given_name")
    )
    lastname_raw = (
        record.get("lastname_raw")
        or record.get("lastname")
        or record.get("family")
        or record.get("family_name")
        or record.get("surname")
    )
    name_raw = (
        record.get("name_raw")
        or record.get("original_name")
        or record.get("name")
        or record.get("full_name")
        or ""
    )
    if not name_raw and firstname_raw and lastname_raw:
        name_raw = f"{firstname_raw} {lastname_raw}"

    return NameRecord(
        record_id=str(record.get("record_id") or record.get("id") or index),
        source=record.get("source") or default_source or "DEFAULT",
        person_id=record.get("person_id") or record.get("orcid"),
        publication_id=record.get("publication_id") or record.get("doi"),
        name_raw=name_raw,
        firstname_raw=firstname_raw,
        lastname_raw=lastname_raw,
        affiliation_raw=record.get("affiliation_raw") or record.get("affiliation"),
        lang_hint=record.get("lang_hint"),
    )


def batch_identify_surname_position_v8(
    records: List[Any],
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
    records = [
        _coerce_batch_record(record, index, source)
        for index, record in enumerate(records)
    ]

    decisions = {}
    for rec in records:
        rec_cfg = get_config(rec.source) if rec.source else cfg
        decisions[rec.record_id] = local_decision(rec, rec_cfg)

    # 2. 一致性调整
    if enable_pub_consistency:
        decisions = adjust_by_publication(records, decisions, cfg)

    if enable_person_consistency:
        decisions = adjust_by_person(records, decisions, cfg)

    return decisions


# 向后兼容
identify_surname_position = identify_surname_position_v8
