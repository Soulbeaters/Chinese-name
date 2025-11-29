# -*- coding: utf-8 -*-
"""
v8.0配置文件 / v8.0 Configuration File

基于Fellegi-Sunter风格的打分框架配置
Fellegi-Sunter style scoring framework configuration

作者: Ma Jiaxin
日期: 2025-11-29
"""

from dataclasses import dataclass
from typing import Dict
import math


@dataclass
class SourceConfig:
    """数据源特定配置 / Source-specific configuration"""

    # 先验分数 / Prior scores
    chinese_prior_fam: float  # Chinese模式下family_first先验
    chinese_prior_giv: float  # Chinese模式下given_first先验
    western_prior_fam: float  # Western模式下family_first先验
    western_prior_giv: float  # Western模式下given_first先验
    mixed_prior_fam: float    # Mixed模式下family_first先验
    mixed_prior_giv: float    # Mixed模式下given_first先验

    # Unknown阈值 / Unknown thresholds
    threshold_cn_unknown: float    # Chinese模式下Unknown阈值
    threshold_west_unknown: float  # Western模式下Unknown阈值
    threshold_mixed_unknown: float # Mixed模式下Unknown阈值

    # 批量一致性参数 / Batch consistency parameters
    person_conf_thresh: float      # person一致性最低置信度
    person_override_thresh: float  # person覆盖阈值
    person_override_conf: float    # person覆盖后的置信度

    pub_conf_thresh: float         # publication一致性最低置信度
    pub_override_thresh: float     # publication覆盖阈值
    pub_override_conf: float       # publication覆盖后的置信度
    pub_dominance_min_diff: int    # publication多数派最小优势数


# 各数据源的配置
CROSSREF_CONFIG = SourceConfig(
    # Crossref: 国际数据,强West先验
    chinese_prior_fam=0.3,
    chinese_prior_giv=0.1,
    western_prior_fam=0.1,
    western_prior_giv=0.5,  # 强West先验
    mixed_prior_fam=0.2,
    mixed_prior_giv=0.3,

    threshold_cn_unknown=0.4,   # 降低阈值
    threshold_west_unknown=0.2, # 降低阈值
    threshold_mixed_unknown=0.3, # 降低阈值

    person_conf_thresh=0.7,
    person_override_thresh=0.6,
    person_override_conf=0.75,

    pub_conf_thresh=0.7,
    pub_override_thresh=0.5,
    pub_override_conf=0.65,
    pub_dominance_min_diff=2,
)


ORCID_CONFIG = SourceConfig(
    # ORCID: 类似Crossref,但更激进使用person一致性
    chinese_prior_fam=0.3,
    chinese_prior_giv=0.1,
    western_prior_fam=0.1,
    western_prior_giv=0.5,
    mixed_prior_fam=0.2,
    mixed_prior_giv=0.3,

    threshold_cn_unknown=0.4,  # 降低阈值
    threshold_west_unknown=0.2, # 降低阈值
    threshold_mixed_unknown=0.3, # 降低阈值

    person_conf_thresh=0.6,  # 更激进
    person_override_thresh=0.5,
    person_override_conf=0.8,

    pub_conf_thresh=0.7,
    pub_override_thresh=0.5,
    pub_override_conf=0.65,
    pub_dominance_min_diff=2,
)


ISTINA_CONFIG = SourceConfig(
    # ИСТИНА: 俄中数据,强Chinese先验
    chinese_prior_fam=0.5,  # 强Chinese先验
    chinese_prior_giv=0.1,
    western_prior_fam=0.2,
    western_prior_giv=0.3,
    mixed_prior_fam=0.3,
    mixed_prior_giv=0.2,

    threshold_cn_unknown=0.5,   # 降低阈值
    threshold_west_unknown=0.3,
    threshold_mixed_unknown=0.4,

    person_conf_thresh=0.65,
    person_override_thresh=0.55,
    person_override_conf=0.7,

    pub_conf_thresh=0.65,
    pub_override_thresh=0.5,
    pub_override_conf=0.6,
    pub_dominance_min_diff=2,
)


# 默认配置（用于未知来源）
DEFAULT_CONFIG = SourceConfig(
    chinese_prior_fam=0.3,
    chinese_prior_giv=0.2,
    western_prior_fam=0.2,
    western_prior_giv=0.4,
    mixed_prior_fam=0.25,
    mixed_prior_giv=0.25,

    threshold_cn_unknown=0.4,
    threshold_west_unknown=0.3,
    threshold_mixed_unknown=0.4,

    person_conf_thresh=0.7,
    person_override_thresh=0.6,
    person_override_conf=0.7,

    pub_conf_thresh=0.7,
    pub_override_thresh=0.5,
    pub_override_conf=0.65,
    pub_dominance_min_diff=2,
)


# 来源映射
SOURCE_CONFIGS: Dict[str, SourceConfig] = {
    "CROSSREF": CROSSREF_CONFIG,
    "crossref": CROSSREF_CONFIG,
    "Crossref": CROSSREF_CONFIG,

    "ORCID": ORCID_CONFIG,
    "orcid": ORCID_CONFIG,
    "Orcid": ORCID_CONFIG,

    "ISTINA": ISTINA_CONFIG,
    "istina": ISTINA_CONFIG,
    "Istina": ISTINA_CONFIG,
    "ИСТИНА": ISTINA_CONFIG,
}


def get_config(source: str = None) -> SourceConfig:
    """获取数据源配置 / Get source configuration"""
    if source and source in SOURCE_CONFIGS:
        return SOURCE_CONFIGS[source]
    return DEFAULT_CONFIG


# === 特征权重 Feature Weights ===

# Chinese模式特征权重
CHINESE_FEATURE_WEIGHTS = {
    # 姓氏位置证据
    "CN_SURNAME_FIRST_ONLY": 2.0,      # first是姓,last不是
    "CN_SURNAME_LAST_ONLY": 2.0,       # last是姓,first不是
    "CN_SURNAME_DOUBLE_FREQ": 1.5,     # 双姓,按频率
    "CN_SURNAME_DOUBLE_DEFAULT": 1.5,  # 双姓,默认

    # 拼音名字证据
    "FIRST_VALID_PY_NAME": 0.8,        # first是合法拼音名(2-3音节)
    "LAST_VALID_PY_NAME": 0.8,         # last是合法拼音名(2-3音节)
    "FIRST_SINGLE_SYLLABLE": 0.4,      # first是单音节
    "LAST_SINGLE_SYLLABLE": 0.4,       # last是单音节

    # 机构证据
    "CN_AFFILIATION": 0.5,             # 中国机构

    # 特殊模式
    "TWO_TOKENS_CN_SURNAME_LAST": 0.7, # 两token且last是姓
    "TWO_TOKENS_SINGLE_SYLLABLE": 0.3, # 两token且有单音节
}


# Western模式特征权重
WESTERN_FEATURE_WEIGHTS = {
    # 西方姓氏证据
    "WEST_SURNAME_LAST": 2.0,          # last是西方姓
    "WEST_SURNAME_FIRST": 0.5,         # first是西方姓(罕见)

    # 中文证据（反向）
    "CN_SURNAME_FIRST_WITH_CN_AFFIL": 2.0,  # first是中文姓+中国机构
    "CN_SURNAME_LAST_WITH_CN_AFFIL": 1.0,   # last是中文姓+中国机构

    # 默认推断
    "NO_CN_EVIDENCE_DEFAULT": 1.0,     # 无中文证据,默认given-first
}


# Mixed模式特征权重
MIXED_FEATURE_WEIGHTS = {
    "CN_SURNAME_FIRST_CN_AFFIL": 1.5,
    "CN_SURNAME_LAST_CN_AFFIL": 1.5,
    "CN_SURNAME_ONLY": 1.0,
    "NO_MATCH_DEFAULT": 0.5,
}


def sigmoid(x: float) -> float:
    """Sigmoid函数用于置信度归一化 / Sigmoid for confidence normalization"""
    return 1.0 / (1.0 + math.exp(-x))
