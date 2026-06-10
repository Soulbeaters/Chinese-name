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
from collections import Counter, defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.surname_pinyin_db import is_surname_pinyin, get_surname_from_pinyin
from data.surname_frequency import (
    compare_surname_frequency_share,
    get_surname_frequency_rank,
    get_surname_frequency_share,
)
from data.non_chinese_surnames import is_non_chinese_surname, get_surname_origin
from data.pinyin_syllables import is_common_given_name_syllable
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
class SplitFieldReviewDecision:
    """Opt-in review decision for pre-screened Crossref split-field cases."""
    review_label: str              # "likely_swapped" | "possible_swapped" | "not_swapped_or_excluded"
    confidence: float
    production_decision: NameDecision
    reason_codes: List[str] = field(default_factory=list)


@dataclass
class PublicationContext:
    """Structured same-publication evidence used by conservative rescues."""
    has_cn_affiliation: bool = False
    cn_affiliation_count: int = 0
    complete_split_count: int = 0
    cn_surname_token_count: int = 0
    field_family_first_candidate_count: int = 0
    cjk_split_hint_count: int = 0
    source_record_count: int = 0


@dataclass
class PublicationCandidateCorrection:
    """Audit record for publication-level candidate-group correction."""
    record_id: str
    publication_id: str
    candidate_count: int
    complete_count: int
    candidate_share: float
    before: NameDecision
    after: NameDecision
    strong_candidate_count: int = 0
    weighted_candidate_strength_sum: float = 0.0
    candidate_strength: float = 0.0
    suppressed: bool = False
    suppression_reason: Optional[str] = None


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
    publication_context_raw: Optional[str] = None
    publication_context: PublicationContext = field(default_factory=PublicationContext)
    lang_hint: Optional[str] = None
    field_only: bool = False


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


def _cjk_token_is_cn_surname(token: Token) -> bool:
    """Best-effort check for a Han-character surname token."""
    if token.char_script != "CJK" or not token.raw:
        return False
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return False

    pinyin = "".join(lazy_pinyin(token.raw)).lower()
    return bool(pinyin and is_surname_pinyin(pinyin))


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


def _is_initial_token(token: Token) -> bool:
    """Return True for one-letter or dotted-initial field tokens."""
    return bool(re.fullmatch(r"[A-Za-z](\.[A-Za-z])*\.?", token.raw))


def _non_initial_tokens(tokens: List[Token]) -> List[Token]:
    """Keep content tokens and drop initials used as given/family abbreviations."""
    return [tok for tok in tokens if not _is_initial_token(tok)]


def _joined_ascii(tokens: List[Token]) -> str:
    """Join a token list into a compact ASCII key."""
    return "".join(tok.ascii.lower() for tok in tokens if tok.ascii)


def _head_or_joined_is_cn_surname(tokens: List[Token]) -> bool:
    """Check whether a field head or compact multi-token form is a Chinese surname."""
    content = _non_initial_tokens(tokens)
    if not content:
        content = tokens
    if not content:
        return False

    head = content[0].ascii.lower()
    joined = _joined_ascii(content)
    return is_surname_pinyin(head) or is_surname_pinyin(joined)


def _field_has_cjk_surname_hint(value: Optional[str], tokens: List[Token]) -> bool:
    """Detect explicit Han-character surname hints inside a split field."""
    if not _contains_cjk_text(value):
        return False
    return (
        _head_or_joined_is_cn_surname(tokens)
        or any(_cjk_token_is_cn_surname(tok) for tok in tokens)
    )


def _single_cn_surname_ascii(tokens: List[Token]) -> Optional[str]:
    """Return a single-token Chinese surname pinyin key, otherwise None."""
    content = _non_initial_tokens(tokens)
    if len(content) != 1:
        return None
    head = content[0].ascii.lower()
    return head if head and is_surname_pinyin(head) else None


def _head_is_western_surname_like(tokens: List[Token]) -> bool:
    """Detect strong western/Russian surname evidence in the field head."""
    content = _non_initial_tokens(tokens)
    if not content:
        return False
    head = content[0].ascii.lower()
    return is_common_western_surname(head) or has_western_suffix(head)


def _field_looks_like_cn_given(tokens: List[Token]) -> bool:
    """Detect a Chinese romanized given-name field without using full-name order."""
    content = _non_initial_tokens(tokens)
    if not content:
        return False
    if len(content) > 2:
        return False

    if len(content) == 1:
        token = content[0]
        is_valid, syl_count, _ = is_valid_pinyin_name(token.ascii)
        return is_valid and 2 <= syl_count <= 3 and not is_surname_pinyin(token.ascii)

    joined = _joined_ascii(content)
    is_valid, syl_count, _ = is_valid_pinyin_name(joined)
    return is_valid and 2 <= syl_count <= 3


def _all_tokens_are_initials(tokens: List[Token]) -> bool:
    """Check whether a split field contains only initials."""
    return bool(tokens) and all(_is_initial_token(tok) for tok in tokens)


def _field_share_score(share_ratio: float) -> float:
    """Convert a dual-surname population-share gap into bounded evidence."""
    if share_ratio >= 20.0:
        return 1.8
    if share_ratio >= 8.0:
        return 1.55
    if share_ratio >= 3.0:
        return 1.30
    return 1.05


def _field_confidence_from_delta(delta: float) -> float:
    """Map split-field score separation to a conservative confidence value."""
    return min(0.95, 0.5 + min(delta * 0.16, 0.45))


def _has_field_family_first_candidate(reason_codes: List[str]) -> bool:
    """Detect field-only evidence that should be promoted only with group support."""
    return _field_family_first_candidate_strength(reason_codes) > 0.0


def _field_family_first_candidate_strength(reason_codes: List[str]) -> float:
    """Score candidate strength for publication-level family-first correction."""
    strength = 0.0
    if "FIELD_GIVEN_WEST_SURNAME_FAMILY_INITIALS" in reason_codes:
        strength += 2.0
    if any(code.startswith("FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE") for code in reason_codes):
        strength += 2.0
    if "FIELD_GIVEN_CN_SURNAME_FAMILY_CN_GIVEN" in reason_codes:
        strength += 1.0
    if any(code.startswith("FIELD_DUAL_CN_SURNAME_FREQ_GIVEN(") for code in reason_codes):
        strength += 0.5
    if strength > 0.0 and "CN_AFFILIATION" in reason_codes:
        strength += 0.5
    return strength


def _publication_override_suppression_reason(decision: NameDecision) -> Optional[str]:
    """Protect high-confidence external split evidence from weak DOI propagation."""
    if decision.order != "given_first":
        return None
    if decision.confidence < 0.66:
        return None
    if "FIELD_EXTERNAL_SPLIT_DEFAULT_GIVEN" not in decision.reason_codes:
        return None
    has_strong_counterevidence = (
        any(code.startswith("FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE") for code in decision.reason_codes)
        or "FIELD_GIVEN_WEST_SURNAME_FAMILY_INITIALS" in decision.reason_codes
        or "FIELD_FAMILY_CJK_SURNAME_HINT" in decision.reason_codes
    )
    if has_strong_counterevidence:
        return None
    return "PUB_PATTERN_OVERRIDE_SUPPRESSED_BY_EXTERNAL_SPLIT_CONFIDENCE"


def _field_tokens_have_western_surface(tokens: List[Token]) -> bool:
    """Detect surface evidence that should block Chinese single-token rescue."""
    for token in _non_initial_tokens(tokens):
        text = token.raw or token.ascii
        ascii_text = token.ascii.lower()
        if token.has_diacritics or has_latin_extended_chars(text):
            return True
        if ascii_text and has_western_suffix(ascii_text):
            return True
    return False


def _has_cn_affiliation(affiliation_raw: Optional[str]) -> bool:
    """Return True when a single affiliation field contains Chinese context."""
    affil_info = analyze_affiliation(affiliation_raw) if affiliation_raw else None
    return bool(affil_info and affil_info.is_chinese)


def _strong_rescue_context_subtype(
    affiliation_raw: Optional[str],
    publication_context: PublicationContext,
    require_cn_context: bool,
) -> Optional[str]:
    """Explain which context condition allows strong dual-surname rescue."""
    if not require_cn_context:
        return "NO_CONTEXT"
    if _has_cn_affiliation(affiliation_raw):
        return "AUTHOR_CN_AFFIL"
    if publication_context.cn_affiliation_count >= 1:
        return "DOI_CN_AFFIL"
    if publication_context.cn_surname_token_count >= 2:
        return "DOI_CN_SURNAME_DENSITY"
    if publication_context.field_family_first_candidate_count >= 2:
        return "DOI_CANDIDATE_SUPPORT"
    if publication_context.cjk_split_hint_count >= 1:
        return "DOI_CJK_SPLIT_HINT"
    return None


def _strong_dual_cn_surname_single_rescue(
    given_tokens: List[Token],
    family_tokens: List[Token],
    share_comparison: Dict[str, Any],
    given_west_surname: bool,
    family_west_surname: bool,
    family_all_initials: bool,
    source: Optional[str],
    affiliation_raw: Optional[str],
    publication_context: PublicationContext,
) -> Tuple[bool, List[str], float]:
    """
    Conservative single-record rescue for dual single-token Chinese surnames.

    It promotes family_first only when the given-slot surname population share
    is much larger than the family-slot surname share and no western/initial
    surface evidence makes the external split unsafe to override.
    """
    ablation = get_ablation_config()
    if not ablation.enable_strong_dual_single_rescue:
        return False, [], 0.0
    if not _is_external_metadata_source(source):
        return False, [], 0.0
    if family_all_initials or given_west_surname or family_west_surname:
        return False, [], 0.0
    if _field_tokens_have_western_surface(given_tokens) or _field_tokens_have_western_surface(family_tokens):
        return False, [], 0.0
    if not (share_comparison.get("has_share1") and share_comparison.get("has_share2")):
        return False, [], 0.0

    share1 = share_comparison["share1"]
    share2 = share_comparison["share2"]
    share_ratio = share_comparison["share_ratio"]
    if share1 <= share2:
        return False, [], 0.0
    if share_ratio < ablation.strong_dual_single_rescue_ratio:
        return False, [], 0.0
    if share1 < ablation.strong_dual_single_rescue_given_min_share:
        return False, [], 0.0
    if share2 > ablation.strong_dual_single_rescue_family_max_share:
        return False, [], 0.0

    family_content = _non_initial_tokens(family_tokens)
    if len(family_content) != 1:
        return False, [], 0.0
    family_valid_pinyin, family_syllable_count, _ = is_valid_pinyin_name(family_content[0].ascii)
    if not family_valid_pinyin or family_syllable_count != 1:
        return False, [], 0.0

    context_subtype = _strong_rescue_context_subtype(
        affiliation_raw,
        publication_context,
        ablation.strong_dual_single_rescue_require_cn_context,
    )
    if not context_subtype:
        return False, [], 0.0

    confidence = min(max(ablation.strong_dual_single_rescue_confidence_cap, 0.70), 0.78)
    return (
        True,
        [
            (
                f"FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE_{context_subtype}"
                f"({_format_share_value(share1)}>{_format_share_value(share2)};"
                f"ratio={share_ratio:.1f})"
            )
        ],
        confidence,
    )


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
        reasons.append("FIELD_SPLIT_EXACT_FAMILY_DIAG")

    if f.field_split_exact_given_first:
        reasons.append("FIELD_SPLIT_EXACT_GIVEN_DIAG")

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
            score_fam += CHINESE_FEATURE_WEIGHTS["CN_SURNAME_DOUBLE_DEFAULT"]
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


def decide_from_split_fields(record: NameRecord, cfg: SourceConfig) -> NameDecision:
    """
    Decide from split metadata fields only.

    This path intentionally does not inspect record.name_raw/original_name. It
    treats the constructed order as firstname/given field followed by
    lastname/family field:
    - given_first: family/lastname field appears to contain the surname.
    - family_first: firstname/given field appears to contain the surname.
    - unknown: evidence is insufficient or ambiguous.
    """
    given = _parsed_field(record.firstname_raw)
    family = _parsed_field(record.lastname_raw)
    given_tokens = given.tokens
    family_tokens = family.tokens
    reasons: List[str] = ["FIELD_ONLY_INPUT"]

    if not given_tokens or not family_tokens:
        return NameDecision("unknown", 0.0, "FIELD_ONLY", reasons + ["MISSING_SPLIT_FIELD"])

    given_ascii = _token_ascii_sequence(given_tokens)
    family_ascii = _token_ascii_sequence(family_tokens)
    if given_ascii and family_ascii and given_ascii == family_ascii:
        return NameDecision("unknown", 0.5, "FIELD_ONLY", reasons + ["FIELD_GIVEN_FAMILY_DUPLICATE"])

    given_cn_surname = _head_or_joined_is_cn_surname(given_tokens)
    family_cn_surname = _head_or_joined_is_cn_surname(family_tokens)
    given_cn_given = _field_looks_like_cn_given(given_tokens)
    family_cn_given = _field_looks_like_cn_given(family_tokens)
    given_west_surname = _head_is_western_surname_like(given_tokens)
    family_west_surname = _head_is_western_surname_like(family_tokens)
    given_all_initials = _all_tokens_are_initials(given_tokens)
    family_all_initials = _all_tokens_are_initials(family_tokens)
    family_cjk_surname_hint = _field_has_cjk_surname_hint(record.lastname_raw, family_tokens)
    given_single_surname = _single_cn_surname_ascii(given_tokens)
    family_single_surname = _single_cn_surname_ascii(family_tokens)

    # Scores are hypothesis scores, not direct field scores:
    # - given_first: lastname/family field carries the surname.
    # - family_first: firstname/given field carries the surname.
    score_given_first = 0.0
    score_family_first = 0.0

    if _is_external_metadata_source(record.source):
        score_given_first += 0.20
        reasons.append("FIELD_SOURCE_SPLIT_PRIOR")

    if family_all_initials:
        reasons.append("FIELD_FAMILY_INITIALS_ONLY")
    if given_all_initials:
        reasons.append("FIELD_GIVEN_INITIALS_ONLY")

    compound_prefix = _extract_compound_surname_prefix(given_tokens)
    given_content_tokens = _non_initial_tokens(given_tokens)
    given_compound_single_token = bool(compound_prefix and len(given_content_tokens) == 1)
    if compound_prefix:
        if len(given_content_tokens) >= 2:
            reasons.append("FIELD_GIVEN_COMPOUND_SURNAME_PREFIX")
        else:
            reasons.append("FIELD_GIVEN_COMPOUND_SURNAME_SINGLE_TOKEN_DIAG")

    given_cn_surname_decisive = given_cn_surname and not given_compound_single_token

    if record.affiliation_raw:
        affil_info = analyze_affiliation(record.affiliation_raw)
        if affil_info and affil_info.is_chinese:
            reasons.append("CN_AFFILIATION")

    # Explicit Han-character surname hints in the family field are the
    # strongest field evidence. The same signal is not symmetric: Han
    # characters inside a given-name field can be ordinary given-name
    # characters with pinyin that also maps to a surname.
    if family_cjk_surname_hint:
        score_given_first += 2.60
        reasons.append("FIELD_FAMILY_CJK_SURNAME_HINT")

    # Strong swapped-field evidence: the given slot starts with a surname-like
    # token while the family slot is initials or a Chinese given-name pattern.
    if given_west_surname and family_all_initials:
        score_family_first += 2.20
        reasons.append("FIELD_GIVEN_WEST_SURNAME_FAMILY_INITIALS")

    if given_cn_surname_decisive and not family_cn_surname and family_cn_given:
        score_family_first += 2.20
        reasons.append("FIELD_GIVEN_CN_SURNAME_FAMILY_CN_GIVEN")

    # Strong valid-field evidence: the family slot carries surname evidence and
    # the given slot carries given-name evidence or initials.
    if family_west_surname and not given_west_surname:
        score_given_first += 1.75
        reasons.append("FIELD_FAMILY_WEST_SURNAME")

    dual_single_cn_surname = (
        bool(given_single_surname)
        and bool(family_single_surname)
        and not given_compound_single_token
        and not _contains_cjk_text(record.firstname_raw)
        and not _contains_cjk_text(record.lastname_raw)
    )
    dual_share_decisive = False
    share_comparison: Optional[Dict[str, Any]] = None

    if dual_single_cn_surname:
        share_comparison = compare_surname_frequency_share(given_single_surname, family_single_surname)
        share1 = share_comparison["share1"]
        share2 = share_comparison["share2"]
        min_ratio = max(get_ablation_config().surname_share_ratio_threshold, 2.0)
        if (
            share_comparison["has_share1"]
            and share_comparison["has_share2"]
            and share_comparison["share_ratio"] >= min_ratio
            and share1 != share2
        ):
            dual_share_decisive = True
            share_score = _field_share_score(share_comparison["share_ratio"])
            if share1 > share2:
                score_family_first += share_score
                reasons.append(
                    f"FIELD_DUAL_CN_SURNAME_FREQ_GIVEN({_format_share_value(share1)}>{_format_share_value(share2)})"
                )
            else:
                score_given_first += share_score
                reasons.append(
                    f"FIELD_DUAL_CN_SURNAME_FREQ_FAMILY({_format_share_value(share2)}>{_format_share_value(share1)})"
                )
        else:
            reasons.append("FIELD_DUAL_CN_SURNAME_AMBIGUOUS")

    if (
        _is_external_metadata_source(record.source)
        and not dual_single_cn_surname
        and not family_all_initials
    ):
        score_given_first += 0.75
        reasons.append("FIELD_EXTERNAL_SPLIT_DEFAULT_GIVEN")

    if not dual_single_cn_surname:
        if family_cn_surname and not given_cn_surname_decisive and (
            given_cn_given or given_compound_single_token or given_all_initials
        ):
            score_given_first += 1.60
            reasons.append("FIELD_FAMILY_CN_SURNAME_GIVEN_CN_NAME")
        elif family_cn_surname and given_cn_given:
            score_given_first += 1.35
            reasons.append("FIELD_FAMILY_CN_SURNAME_GIVEN_CN_NAME")
        elif family_cn_surname or family_west_surname:
            score_given_first += 0.85
            reasons.append("FIELD_FAMILY_SURNAME_WEAK")

        if (
            given_cn_surname_decisive
            and family_cn_given
            and "FIELD_GIVEN_CN_SURNAME_FAMILY_CN_GIVEN" not in reasons
        ):
            score_family_first += 1.60
            reasons.append("FIELD_GIVEN_CN_SURNAME_FAMILY_CN_GIVEN")
        elif given_cn_surname_decisive or given_west_surname:
            score_family_first += 0.45
            reasons.append("FIELD_GIVEN_SURNAME_WEAK")

    if given_cn_given:
        score_given_first += 0.35
    if family_cn_given:
        score_family_first += 0.35
    if given_all_initials:
        score_given_first += 0.35

    # Initial-only family fields are common in metadata but are unsafe unless
    # independent evidence strongly places the surname in the given field.
    if family_all_initials and score_family_first < 1.20:
        return NameDecision(
            "unknown",
            0.5,
            "FIELD_ONLY",
            reasons + ["FIELD_INITIALS_AMBIGUOUS"],
        )

    if dual_single_cn_surname and dual_share_decisive and share_comparison:
        strong_rescue, rescue_reasons, rescue_confidence = _strong_dual_cn_surname_single_rescue(
            given_tokens=given_tokens,
            family_tokens=family_tokens,
            share_comparison=share_comparison,
            given_west_surname=given_west_surname,
            family_west_surname=family_west_surname,
            family_all_initials=family_all_initials,
            source=record.source,
            affiliation_raw=record.affiliation_raw,
            publication_context=record.publication_context,
        )
        if strong_rescue:
            return NameDecision(
                "family_first",
                rescue_confidence,
                "FIELD_ONLY",
                reasons + rescue_reasons,
            )

    if dual_single_cn_surname and not dual_share_decisive:
        if _is_external_metadata_source(record.source):
            return NameDecision(
                "given_first",
                0.66,
                "FIELD_ONLY",
                reasons + ["FIELD_EXTERNAL_SPLIT_DEFAULT_GIVEN"],
            )
        return NameDecision(
            "unknown",
            0.5,
            "FIELD_ONLY",
            reasons,
        )

    delta = score_given_first - score_family_first
    if abs(delta) < 0.65:
        if _is_external_metadata_source(record.source) and not family_all_initials:
            return NameDecision(
                "given_first",
                0.66,
                "FIELD_ONLY",
                reasons + ["FIELD_EXTERNAL_SPLIT_DEFAULT_GIVEN"],
            )
        return NameDecision("unknown", 0.5, "FIELD_ONLY", reasons + ["FIELD_SCORE_DELTA_SMALL"])

    confidence = _field_confidence_from_delta(abs(delta))
    if delta > 0:
        return NameDecision("given_first", confidence, "FIELD_ONLY", reasons)

    if (
        _is_external_metadata_source(record.source)
        and "FIELD_GIVEN_WEST_SURNAME_FAMILY_INITIALS" not in reasons
    ):
        return NameDecision(
            "given_first",
            min(confidence, 0.72),
            "FIELD_ONLY",
            reasons + ["FIELD_FAMILY_FIRST_CANDIDATE_DEFERRED"],
        )

    return NameDecision("family_first", confidence, "FIELD_ONLY", reasons)


def _field_review_key(tokens: List[Token]) -> str:
    """Return a compact content key for split-field review rules."""
    content = _non_initial_tokens(tokens)
    if not content:
        content = tokens
    return _joined_ascii(content)


def _field_non_chinese_origin(tokens: List[Token]) -> Optional[str]:
    """Return a known non-Chinese surname origin for a split-field head/key."""
    content = _non_initial_tokens(tokens)
    if not content:
        return None
    candidates = []
    head = content[0].ascii.lower()
    joined = _joined_ascii(content)
    if head:
        candidates.append(head)
    if joined and joined != head:
        candidates.append(joined)

    for candidate in candidates:
        if is_non_chinese_surname(candidate):
            return get_surname_origin(candidate)
        if is_common_western_surname(candidate):
            return "Western"
    return None


def _field_pinyin_syllable_count(tokens: List[Token]) -> Tuple[bool, int, List[str]]:
    """Return pinyin validity for the compact content key of a split field."""
    key = _field_review_key(tokens)
    return is_valid_pinyin_name(key)


def review_crossref_split_fields_v8(
    firstname: Optional[str] = None,
    lastname: Optional[str] = None,
    source: Optional[str] = "CROSSREF",
    affiliation: Optional[str] = None,
    publication_id: Optional[str] = None,
) -> SplitFieldReviewDecision:
    """
    Opt-in review classifier for pre-screened Crossref split-field candidates.

    The production field-only profile stays conservative: it protects Crossref
    split fields unless strong contextual evidence supports a correction. This
    review profile is separate and is intended for advisor/manual audit queues
    that are already suspected of given/family reversal.
    """
    record = NameRecord(
        record_id="review",
        source=source or "CROSSREF",
        name_raw="",
        firstname_raw=firstname,
        lastname_raw=lastname,
        affiliation_raw=affiliation,
        publication_id=publication_id,
        field_only=True,
    )
    production = decide_from_split_fields(record, get_config(source))
    reasons = list(production.reason_codes) + ["SPLIT_REVIEW_PROFILE"]

    given = _parsed_field(firstname)
    family = _parsed_field(lastname)
    given_tokens = given.tokens
    family_tokens = family.tokens
    if not given_tokens or not family_tokens:
        return SplitFieldReviewDecision(
            "not_swapped_or_excluded",
            0.0,
            production,
            reasons + ["SPLIT_REVIEW_MISSING_FIELD"],
        )

    if production.order == "family_first":
        return SplitFieldReviewDecision(
            "likely_swapped",
            max(production.confidence, 0.80),
            production,
            reasons + ["SPLIT_REVIEW_PRODUCTION_FAMILY_FIRST"],
        )

    family_non_chinese_origin = _field_non_chinese_origin(family_tokens)
    if family_non_chinese_origin:
        return SplitFieldReviewDecision(
            "not_swapped_or_excluded",
            0.78,
            production,
            reasons + [f"SPLIT_REVIEW_EXCLUDED_NON_CHINESE_FAMILY_FIELD({family_non_chinese_origin})"],
        )

    given_is_cn_surname = _head_or_joined_is_cn_surname(given_tokens)
    family_is_cn_given = _field_looks_like_cn_given(family_tokens)
    if given_is_cn_surname and family_is_cn_given:
        return SplitFieldReviewDecision(
            "likely_swapped",
            0.82,
            production,
            reasons + ["SPLIT_REVIEW_GIVEN_FIELD_CN_SURNAME_FAMILY_FIELD_PINYIN_GIVEN"],
        )

    family_valid_pinyin, family_syllable_count, _ = _field_pinyin_syllable_count(family_tokens)
    given_key = _field_review_key(given_tokens)
    given_share = get_surname_frequency_share(given_key)
    given_is_common_given_syllable = is_common_given_name_syllable(given_key)
    family_key = _field_review_key(family_tokens)
    family_is_single_letter = len(family_key) == 1

    family_is_short_single_token = bool(family_key) and len(family_key) <= 5 and " " not in family_key
    family_can_be_single_syllable_review = (
        (family_valid_pinyin and family_syllable_count == 1)
        or family_is_short_single_token
    )

    if given_is_cn_surname and family_can_be_single_syllable_review:
        if given_share >= 1.0:
            return SplitFieldReviewDecision(
                "likely_swapped",
                0.74,
                production,
                reasons + [f"SPLIT_REVIEW_SINGLE_SYLLABLE_HIGH_FREQ_SURNAME({given_key})"],
            )
        if given_share >= 0.40 and not given_is_common_given_syllable:
            return SplitFieldReviewDecision(
                "likely_swapped",
                0.72,
                production,
                reasons + [f"SPLIT_REVIEW_SINGLE_SYLLABLE_MEDIUM_FREQ_SURNAME({given_key})"],
            )
        if family_is_single_letter and given_share >= 0.40:
            return SplitFieldReviewDecision(
                "likely_swapped",
                0.70,
                production,
                reasons + [f"SPLIT_REVIEW_SINGLE_LETTER_FAMILY_FIELD_SURNAME({given_key})"],
            )
        return SplitFieldReviewDecision(
            "possible_swapped",
            0.58,
            production,
            reasons + ["SPLIT_REVIEW_SINGLE_SYLLABLE_AMBIGUOUS"],
        )

    if _has_field_family_first_candidate(production.reason_codes):
        return SplitFieldReviewDecision(
            "possible_swapped",
            0.58,
            production,
            reasons + ["SPLIT_REVIEW_DEFERRED_PRODUCTION_CANDIDATE"],
        )

    return SplitFieldReviewDecision(
        "not_swapped_or_excluded",
        max(0.5, production.confidence),
        production,
        reasons + ["SPLIT_REVIEW_NO_STRONG_SWAP_SIGNAL"],
    )


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
    if record.field_only:
        return decide_from_split_fields(record, cfg)

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

def _has_reason_prefix(decision: NameDecision, prefix: str) -> bool:
    return any(code.startswith(prefix) for code in decision.reason_codes)


def _is_raw_chinese_family_first_candidate(
    record: NameRecord,
    decision: NameDecision,
) -> bool:
    if record.field_only or not record.name_raw:
        return False
    if decision.mode != "CHINESE" or decision.order != "family_first":
        return False
    return (
        _has_reason_prefix(decision, "CN_SURNAME_DOUBLE_FREQ_FIRST")
        or "CN_SURNAME_DOUBLE_DEFAULT_FAM" in decision.reason_codes
        or "CN_SURNAME_FIRST_ONLY" in decision.reason_codes
    )


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
            groups[rec.person_id].append(rec)

    for pid, group_records in groups.items():
        rec_ids = [rec.record_id for rec in group_records]
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

        candidate_ids = {
            rec.record_id
            for rec in group_records
            if rec.record_id in decisions
            and _is_raw_chinese_family_first_candidate(rec, decisions[rec.record_id])
        }
        if not candidate_ids:
            continue

        giv = [
            decisions[rec.record_id]
            for rec in group_records
            if rec.record_id in decisions
            and decisions[rec.record_id].order == "given_first"
            and decisions[rec.record_id].confidence >= cfg.person_conf_thresh
        ]
        fam = [
            decisions[rec.record_id]
            for rec in group_records
            if rec.record_id in decisions
            and rec.record_id not in candidate_ids
            and decisions[rec.record_id].order == "family_first"
            and decisions[rec.record_id].confidence >= cfg.person_conf_thresh
        ]

        evidence_count = len(giv) + len(fam)
        if evidence_count == 0:
            continue

        given_share = len(giv) / evidence_count
        if len(giv) < 1:
            continue
        if len(giv) <= len(fam):
            continue
        if given_share < 0.60:
            continue

        for rid in candidate_ids:
            d = decisions[rid]
            decisions[rid] = NameDecision(
                order="given_first",
                confidence=max(d.confidence, cfg.person_override_conf),
                mode=d.mode,
                reason_codes=d.reason_codes + [
                    (
                        f"PERSON_RAW_GIVEN_MAJORITY_OVERRIDE("
                        f"{len(giv)}/{evidence_count}={given_share:.3f})"
                    ),
                    "PERSON_CONSISTENCY_OVERRIDE",
                ],
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
            groups[rec.publication_id].append(rec)

    for pub_id, group_records in groups.items():
        rec_ids = [rec.record_id for rec in group_records]
        records_by_id = {rec.record_id: rec for rec in group_records}
        fam = [decisions[rid] for rid in rec_ids if rid in decisions
               and decisions[rid].order == "family_first"
               and decisions[rid].confidence >= cfg.pub_conf_thresh]
        giv = [decisions[rid] for rid in rec_ids if rid in decisions
               and decisions[rid].order == "given_first"
               and decisions[rid].confidence >= cfg.pub_conf_thresh]

        candidate_ids = {
            rec.record_id
            for rec in group_records
            if rec.record_id in decisions
            and _is_raw_chinese_family_first_candidate(rec, decisions[rec.record_id])
        }
        if candidate_ids:
            raw_giv = [
                decisions[rec.record_id]
                for rec in group_records
                if rec.record_id in decisions
                and decisions[rec.record_id].order == "given_first"
                and decisions[rec.record_id].confidence >= cfg.pub_conf_thresh
            ]
            raw_fam = [
                decisions[rec.record_id]
                for rec in group_records
                if rec.record_id in decisions
                and rec.record_id not in candidate_ids
                and decisions[rec.record_id].order == "family_first"
                and decisions[rec.record_id].confidence >= cfg.pub_conf_thresh
            ]

            evidence_count = len(raw_giv) + len(raw_fam)
            given_share = len(raw_giv) / evidence_count if evidence_count else 0.0
            if (
                evidence_count > 0
                and len(raw_giv) >= cfg.pub_dominance_min_diff
                and len(raw_giv) - len(raw_fam) >= cfg.pub_dominance_min_diff
                and given_share >= 0.70
            ):
                for rid in candidate_ids:
                    d = decisions[rid]
                    decisions[rid] = NameDecision(
                        order="given_first",
                        confidence=max(d.confidence, cfg.pub_override_conf),
                        mode=d.mode,
                        reason_codes=d.reason_codes + [
                            (
                                f"PUB_RAW_GIVEN_MAJORITY_OVERRIDE("
                                f"{len(raw_giv)}/{evidence_count}={given_share:.3f})"
                            ),
                            "PUB_PATTERN_OVERRIDE",
                        ],
                    )

        if len(fam) == 0 and len(giv) == 0:
            continue

        if abs(len(fam) - len(giv)) < cfg.pub_dominance_min_diff:
            continue  # 无明显多数

        target_order = "family_first" if len(fam) > len(giv) else "given_first"

        for rid in rec_ids:
            if rid not in decisions:
                continue
            if records_by_id[rid].field_only:
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

def adjust_by_publication_high_share(
    records: List[NameRecord],
    decisions: Dict[str, NameDecision],
    cfg: SourceConfig
) -> Dict[str, NameDecision]:
    """
    Promote split-field correction candidates with publication-level support.

    Crossref-style split fields are usually reliable, so single-record Chinese
    surname evidence is treated as a candidate rather than an immediate
    correction. A publication-level correction is applied only when multiple
    authors in the same DOI show the same swapped-field pattern. Only candidate
    records are corrected; unrelated coauthors in the same DOI are not touched.
    """
    for correction in _publication_candidate_group_corrections(records, decisions, cfg):
        decisions[correction.record_id] = correction.after

    return decisions


def _publication_candidate_group_corrections(
    records: List[NameRecord],
    decisions: Dict[str, NameDecision],
    cfg: SourceConfig,
) -> List[PublicationCandidateCorrection]:
    """Return publication candidate-group corrections without mutating decisions."""
    ablation = get_ablation_config()
    if not ablation.enable_publication_candidate_group_correction:
        return []

    groups = defaultdict(list)
    for rec in records:
        if rec.publication_id:
            groups[rec.publication_id].append(rec.record_id)

    corrections: List[PublicationCandidateCorrection] = []
    for pub_id, rec_ids in groups.items():
        complete = [
            rid for rid in rec_ids
            if rid in decisions and decisions[rid].order != "unknown"
        ]
        if not complete:
            continue

        candidate_strengths = {
            rid: _field_family_first_candidate_strength(decisions[rid].reason_codes)
            for rid in complete
        }
        candidates = [rid for rid, strength in candidate_strengths.items() if strength > 0.0]
        if len(candidates) < ablation.publication_candidate_group_min_count:
            continue

        candidate_share = len(candidates) / len(complete)
        if candidate_share < ablation.publication_candidate_group_min_share:
            continue
        strong_candidate_count = sum(
            1
            for rid in candidates
            if candidate_strengths[rid] >= ablation.publication_candidate_group_strong_threshold
        )
        if strong_candidate_count < ablation.publication_candidate_group_min_strong_count:
            continue
        weighted_candidate_strength_sum = sum(candidate_strengths[rid] for rid in candidates)
        if weighted_candidate_strength_sum < ablation.publication_candidate_group_min_strength_sum:
            continue

        for rid in candidates:
            if rid not in decisions:
                continue
            d = decisions[rid]
            suppression_reason = (
                _publication_override_suppression_reason(d)
                if ablation.enable_publication_external_split_confidence_guard
                else None
            )
            if suppression_reason:
                after = NameDecision(
                    order=d.order,
                    confidence=d.confidence,
                    mode=d.mode,
                    reason_codes=d.reason_codes + [suppression_reason],
                )
            else:
                after = NameDecision(
                    order="family_first",
                    confidence=max(d.confidence, cfg.pub_override_conf, 0.66),
                    mode=d.mode,
                    reason_codes=d.reason_codes + [
                        (
                            f"PUB_CANDIDATE_GROUP_CORRECTION("
                            f"{len(candidates)}/{len(complete)}={candidate_share:.3f};"
                            f"strong={strong_candidate_count};"
                            f"strength={weighted_candidate_strength_sum:.1f})"
                        ),
                        "PUB_PATTERN_OVERRIDE",
                    ]
                )
            corrections.append(
                PublicationCandidateCorrection(
                    record_id=rid,
                    publication_id=str(pub_id),
                    candidate_count=len(candidates),
                    complete_count=len(complete),
                    candidate_share=candidate_share,
                    before=d,
                    after=after,
                    strong_candidate_count=strong_candidate_count,
                    weighted_candidate_strength_sum=weighted_candidate_strength_sum,
                    candidate_strength=candidate_strengths[rid],
                    suppressed=bool(suppression_reason),
                    suppression_reason=suppression_reason,
                )
            )

    return corrections


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


def identify_surname_position_from_fields_v8(
    firstname: Optional[str] = None,
    lastname: Optional[str] = None,
    affiliation: Optional[str] = None,
    mode_hint: Optional[str] = None,
    source: Optional[str] = None,
    person_id: Optional[str] = None,
    publication_id: Optional[str] = None,
) -> Tuple[Optional[str], float, str]:
    """
    v8.0 split-field validation interface.

    This is the production-safe path for Crossref-style metadata when only
    given/family fields are available. It intentionally does not accept or use
    original_name.
    """
    record = NameRecord(
        record_id="single",
        source=source or "DEFAULT",
        person_id=person_id,
        publication_id=publication_id,
        name_raw="",
        firstname_raw=firstname,
        lastname_raw=lastname,
        affiliation_raw=affiliation,
        lang_hint=mode_hint,
        field_only=True,
    )
    decision = local_decision(record, get_config(source))
    reason = f"{decision.mode}: {', '.join(decision.reason_codes)}"
    return (decision.order, decision.confidence, reason)


def _coerce_batch_record(
    record: Any,
    index: int,
    default_source: Optional[str] = None,
    force_field_only_when_split_fields: bool = True,
) -> NameRecord:
    """Accept NameRecord or common Crossref-style dicts in the batch API."""
    if isinstance(record, NameRecord):
        updates: Dict[str, Any] = {}
        if default_source and (not record.source or record.source == "DEFAULT"):
            updates["source"] = default_source
        has_split = bool(record.firstname_raw or record.lastname_raw)
        if force_field_only_when_split_fields and has_split:
            updates["name_raw"] = ""
            updates["field_only"] = True
        return replace(record, **updates) if updates else record

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
        or record.get("name")
        or record.get("full_name")
        or ""
    )
    has_split = bool(firstname_raw or lastname_raw)
    if force_field_only_when_split_fields and has_split:
        name_raw = ""
        field_only = True
    else:
        field_only = not bool(name_raw) and has_split
    raw_publication_context = record.get("publication_context")
    publication_context = (
        raw_publication_context
        if isinstance(raw_publication_context, PublicationContext)
        else PublicationContext()
    )
    publication_context_raw = record.get("publication_context_raw")
    if publication_context_raw is None and isinstance(raw_publication_context, str):
        publication_context_raw = raw_publication_context

    return NameRecord(
        record_id=str(record.get("record_id") or record.get("id") or index),
        source=record.get("source") or default_source or "DEFAULT",
        person_id=record.get("person_id") or record.get("orcid"),
        publication_id=record.get("publication_id") or record.get("doi"),
        name_raw=name_raw,
        firstname_raw=firstname_raw,
        lastname_raw=lastname_raw,
        affiliation_raw=record.get("affiliation_raw") or record.get("affiliation"),
        publication_context_raw=publication_context_raw,
        publication_context=publication_context,
        lang_hint=record.get("lang_hint"),
        field_only=bool(record.get("field_only", field_only)),
    )


def _record_has_cn_surname_split_token(record: NameRecord) -> bool:
    """Detect whether split fields contain at least one Chinese surname token."""
    given = _parsed_field(record.firstname_raw)
    family = _parsed_field(record.lastname_raw)
    return (
        _head_or_joined_is_cn_surname(given.tokens)
        or _head_or_joined_is_cn_surname(family.tokens)
        or bool(_single_cn_surname_ascii(given.tokens))
        or bool(_single_cn_surname_ascii(family.tokens))
    )


def _record_has_cjk_split_hint(record: NameRecord) -> bool:
    """Detect explicit Han-character surname hints in split fields."""
    given = _parsed_field(record.firstname_raw)
    family = _parsed_field(record.lastname_raw)
    return (
        _field_has_cjk_surname_hint(record.firstname_raw, given.tokens)
        or _field_has_cjk_surname_hint(record.lastname_raw, family.tokens)
    )


def _record_has_field_family_first_candidate_static(record: NameRecord) -> bool:
    """Static approximation of family-first split-field candidate evidence."""
    given = _parsed_field(record.firstname_raw)
    family = _parsed_field(record.lastname_raw)
    given_tokens = given.tokens
    family_tokens = family.tokens
    if not given_tokens or not family_tokens:
        return False

    given_cn_surname = _head_or_joined_is_cn_surname(given_tokens)
    family_cn_surname = _head_or_joined_is_cn_surname(family_tokens)
    family_cn_given = _field_looks_like_cn_given(family_tokens)
    given_west_surname = _head_is_western_surname_like(given_tokens)
    family_all_initials = _all_tokens_are_initials(family_tokens)
    given_single_surname = _single_cn_surname_ascii(given_tokens)
    family_single_surname = _single_cn_surname_ascii(family_tokens)
    compound_prefix = _extract_compound_surname_prefix(given_tokens)
    given_content_tokens = _non_initial_tokens(given_tokens)
    given_compound_single_token = bool(compound_prefix and len(given_content_tokens) == 1)

    if given_west_surname and family_all_initials:
        return True
    if given_cn_surname and not given_compound_single_token and not family_cn_surname and family_cn_given:
        return True
    if given_single_surname and family_single_surname and not given_compound_single_token:
        share_comparison = compare_surname_frequency_share(given_single_surname, family_single_surname)
        return (
            share_comparison["has_share1"]
            and share_comparison["has_share2"]
            and share_comparison["share1"] > share_comparison["share2"]
            and share_comparison["share_ratio"] >= max(get_ablation_config().surname_share_ratio_threshold, 2.0)
        )
    return False


def _build_publication_context(group_records: List[NameRecord]) -> PublicationContext:
    """Build structured DOI-level context without using original/name fields."""
    cn_affiliation_count = sum(1 for rec in group_records if _has_cn_affiliation(rec.affiliation_raw))
    complete_split_count = sum(1 for rec in group_records if rec.firstname_raw and rec.lastname_raw)
    cn_surname_token_count = sum(1 for rec in group_records if _record_has_cn_surname_split_token(rec))
    field_family_first_candidate_count = sum(
        1 for rec in group_records if _record_has_field_family_first_candidate_static(rec)
    )
    cjk_split_hint_count = sum(1 for rec in group_records if _record_has_cjk_split_hint(rec))
    return PublicationContext(
        has_cn_affiliation=cn_affiliation_count > 0,
        cn_affiliation_count=cn_affiliation_count,
        complete_split_count=complete_split_count,
        cn_surname_token_count=cn_surname_token_count,
        field_family_first_candidate_count=field_family_first_candidate_count,
        cjk_split_hint_count=cjk_split_hint_count,
        source_record_count=len(group_records),
    )


def _attach_publication_context(records: List[NameRecord]) -> None:
    """Attach structured same-DOI evidence to every record in that DOI."""
    groups = defaultdict(list)
    for rec in records:
        if rec.publication_id:
            groups[rec.publication_id].append(rec)

    for group_records in groups.values():
        publication_context = _build_publication_context(group_records)
        for group_rec in group_records:
            group_rec.publication_context = publication_context


def batch_identify_surname_position_v8(
    records: List[Any],
    source: Optional[str] = None,
    enable_person_consistency: bool = True,
    enable_pub_consistency: bool = True,
    force_field_only_when_split_fields: bool = True,
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
        _coerce_batch_record(
            record,
            index,
            source,
            force_field_only_when_split_fields=force_field_only_when_split_fields,
        )
        for index, record in enumerate(records)
    ]
    _attach_publication_context(records)

    decisions = {}
    for rec in records:
        rec_cfg = get_config(rec.source) if rec.source else cfg
        decisions[rec.record_id] = local_decision(rec, rec_cfg)

    # 2. 一致性调整
    if enable_person_consistency:
        decisions = adjust_by_person(records, decisions, cfg)

    if enable_pub_consistency:
        decisions = adjust_by_publication(records, decisions, cfg)

    # Re-run person consistency after publication evidence has been normalized.
    if enable_person_consistency:
        decisions = adjust_by_person(records, decisions, cfg)

    if enable_pub_consistency:
        decisions = adjust_by_publication_high_share(records, decisions, cfg)

    return decisions


# 向后兼容
identify_surname_position = identify_surname_position_v8
