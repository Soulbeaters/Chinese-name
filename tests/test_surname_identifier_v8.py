# -*- coding: utf-8 -*-
"""
Unit tests for the v8 surname-position identifier.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.surname_frequency import (
    compare_surname_frequency_share,
    get_surname_frequency_share,
)
from src.config_v8 import (
    AblationConfig,
    get_config,
    reset_ablation_config,
    set_ablation_config,
)
from src.surname_identifier_v8 import (
    NameRecord,
    batch_identify_surname_position_v8,
    detect_mode,
    identify_surname_position_from_fields_v8,
    identify_surname_position_v8,
    local_decision,
    preprocess_name,
    review_crossref_split_fields_v8,
)


def _local_strategy_decision(
    name_raw: str,
    strategy: str = "share_ratio",
    source: str = "CROSSREF",
    share_threshold: float = 1.0,
):
    """Exercise a specific double-surname frequency strategy directly."""
    set_ablation_config(
        AblationConfig(
            surname_freq_strategy=strategy,
            surname_share_ratio_threshold=share_threshold,
        )
    )
    try:
        record = NameRecord(
            record_id="share-test",
            name_raw=name_raw,
            source=source,
            affiliation_raw="Tsinghua University, Beijing, China",
        )
        return local_decision(record, get_config(source))
    finally:
        reset_ablation_config()


def test_abbreviation_detection():
    order, conf, _ = identify_surname_position_v8("Liu W.")
    assert order == "family_first"
    assert conf == 1.0

    order, conf, _ = identify_surname_position_v8("Chen J.M.")
    assert order == "family_first"
    assert conf == 1.0

    order, conf, _ = identify_surname_position_v8("Wang A.B.C.")
    assert order == "family_first"
    assert conf == 1.0


def test_chinese_mode_basic():
    order, _, _ = identify_surname_position_v8(
        "Tang Tianxiang",
        affiliation="Tsinghua University, Beijing",
    )
    assert order == "family_first"

    order, _, _ = identify_surname_position_v8(
        "Liu Yuhui",
        affiliation="Peking University",
    )
    assert order == "family_first"

    order, _, _ = identify_surname_position_v8(
        "Tianxiang Tang",
        source="CROSSREF",
    )
    assert order == "given_first"


def test_chinese_single_syllable_optimization():
    order, _, _ = identify_surname_position_v8(
        "Li Tianming",
        affiliation="Tsinghua University",
    )
    assert order == "family_first"

    order, _, _ = identify_surname_position_v8(
        "Tianming Li",
        source="CROSSREF",
    )
    assert order == "given_first"


def test_double_surname():
    order, _, _ = identify_surname_position_v8(
        "Zhang Wang",
        source="ISTINA",
    )
    assert order == "family_first"

    order, _, _ = identify_surname_position_v8(
        "Zhang Wang",
        source="CROSSREF",
    )
    assert order in ["family_first", "given_first"]


def test_surname_frequency_share_lookup_and_aggregation():
    assert get_surname_frequency_share("wang") == 7.53
    assert get_surname_frequency_share("unknown") == 0.0
    assert get_surname_frequency_share("yu") == 1.1978
    assert get_surname_frequency_share("he") == 1.311

    comparison = compare_surname_frequency_share("hong", "yuan")
    assert comparison["more_common"] == "yuan"
    assert comparison["share_ratio"] > 1.5
    assert comparison["has_share1"] is True
    assert comparison["has_share2"] is True


def test_share_ratio_double_surname_regressions():
    decision = _local_strategy_decision("Wang Wei", strategy="share_ratio")
    assert decision.order == "family_first"
    assert "CN_SURNAME_DOUBLE_FREQ_FIRST(7.53>0.8375)" in decision.reason_codes

    decision = _local_strategy_decision("Lu Xing", strategy="share_ratio")
    assert decision.order == "family_first"
    assert "CN_SURNAME_DOUBLE_FREQ_FIRST(1.4541>0.1465)" in decision.reason_codes

    decision = _local_strategy_decision("Ge Yan", strategy="share_ratio")
    assert decision.order == "given_first"
    assert "CN_SURNAME_DOUBLE_FREQ_LAST(0.658>0.175)" in decision.reason_codes

    decision = _local_strategy_decision("Huan He", strategy="share_ratio")
    assert decision.order == "given_first"
    assert "CN_SURNAME_DOUBLE_FREQ_LAST(1.311>0)" in decision.reason_codes

    decision = _local_strategy_decision("Hong Yuan", strategy="share_ratio")
    assert decision.order == "given_first"
    assert "CN_SURNAME_DOUBLE_FREQ_LAST(0.5519>0.18)" in decision.reason_codes

    decision = _local_strategy_decision("Zhang Wang", strategy="share_ratio")
    assert decision.order == "given_first"
    assert "CN_SURNAME_DOUBLE_FREQ_LAST(7.53>6.86)" in decision.reason_codes


def test_share_ratio_threshold_changes_boundary_trigger():
    decision_relaxed = _local_strategy_decision(
        "Wang Liu",
        strategy="share_ratio",
        share_threshold=1.0,
    )
    assert decision_relaxed.order == "family_first"
    assert "CN_SURNAME_DOUBLE_FREQ_FIRST(7.53>5.2)" in decision_relaxed.reason_codes

    decision_default = _local_strategy_decision(
        "Wang Liu",
        strategy="share_ratio",
        share_threshold=1.5,
    )
    assert decision_default.order == "family_first"
    assert "CN_SURNAME_DOUBLE_DEFAULT_FAM" in decision_default.reason_codes
    assert all(
        not code.startswith("CN_SURNAME_DOUBLE_FREQ_")
        for code in decision_default.reason_codes
    )


def test_rank_gap_legacy_double_surname_regressions():
    decision = _local_strategy_decision("Hong Yuan", strategy="rank_gap")
    assert decision.order == "given_first"
    assert "CN_SURNAME_DOUBLE_FREQ_LAST(37<999)" in decision.reason_codes

    decision = _local_strategy_decision("Ge Yan", strategy="rank_gap")
    assert decision.order == "given_first"
    assert "CN_SURNAME_DOUBLE_FREQ_LAST(90<999)" in decision.reason_codes


def test_freq_disabled_reproduces_remote_branch_behavior():
    decision = _local_strategy_decision("Wang Wei", strategy="freq_disabled")
    assert decision.order == "family_first"
    assert "CN_SURNAME_DOUBLE_DEFAULT_FAM" in decision.reason_codes
    assert all(not code.startswith("CN_SURNAME_DOUBLE_FREQ_") for code in decision.reason_codes)

    decision = _local_strategy_decision("Hong Yuan", strategy="freq_disabled")
    assert decision.order == "family_first"
    assert "CN_SURNAME_DOUBLE_DEFAULT_FAM" in decision.reason_codes
    assert all(not code.startswith("CN_SURNAME_DOUBLE_FREQ_") for code in decision.reason_codes)


def test_western_mode():
    order, _, _ = identify_surname_position_v8("David Smith")
    assert order == "given_first"

    order, _, _ = identify_surname_position_v8("Chris Aberson")
    assert order == "given_first"

    order, _, _ = identify_surname_position_v8("Tuomas Savolainen")
    assert order == "given_first"

    order, _, _ = identify_surname_position_v8("Smith David")
    assert order in ["family_first", "given_first"]


def test_mixed_mode():
    order, _, _ = identify_surname_position_v8(
        "Zhang Thomas",
        affiliation="Tsinghua University, Beijing, China",
    )
    assert order in ["family_first", "given_first"]

    order, _, _ = identify_surname_position_v8("Peter Mueller")
    assert order in ["given_first", "unknown"]


def test_source_specific_crossref():
    order, _, _ = identify_surname_position_v8(
        "Yuhui Liu",
        source="CROSSREF",
    )
    assert order == "given_first"


def test_source_specific_istina():
    order, _, _ = identify_surname_position_v8(
        "Li Tianming",
        source="ISTINA",
    )
    assert order == "family_first"


def test_source_specific_orcid():
    order, _, _ = identify_surname_position_v8(
        "Yuhui Liu",
        source="ORCID",
    )
    assert order == "given_first"


def test_field_only_valid_crossref_chinese_split():
    order, _, reason = identify_surname_position_from_fields_v8(
        firstname="Yuhui",
        lastname="Liu",
        source="CROSSREF",
    )
    assert order == "given_first"
    assert "FIELD_ONLY_INPUT" in reason
    assert "FIELD_SPLIT_EXACT_GIVEN" not in reason


def test_field_only_detects_swapped_chinese_split():
    order, _, reason = identify_surname_position_from_fields_v8(
        firstname="Zhao",
        lastname="Hongrui",
        affiliation="Chinese Academy of Sciences",
        source="CROSSREF",
    )
    assert order == "given_first"
    assert "FIELD_GIVEN_CN_SURNAME_FAMILY_CN_GIVEN" in reason
    assert "FIELD_FAMILY_FIRST_CANDIDATE_DEFERRED" in reason
    assert "FIELD_SPLIT_EXACT_GIVEN" not in reason


def test_split_review_profile_is_opt_in_for_prescreened_crossref_cases():
    production_order, _, production_reason = identify_surname_position_from_fields_v8(
        firstname="Chen",
        lastname="Sitong",
        source="CROSSREF",
    )
    review = review_crossref_split_fields_v8(
        firstname="Chen",
        lastname="Sitong",
        source="CROSSREF",
    )
    japanese = review_crossref_split_fields_v8(
        firstname="Mai",
        lastname="Ouchi",
        source="CROSSREF",
    )

    assert production_order == "given_first"
    assert "FIELD_EXTERNAL_SPLIT_DEFAULT_GIVEN" in production_reason
    assert review.review_label == "likely_swapped"
    assert "SPLIT_REVIEW_GIVEN_FIELD_CN_SURNAME_FAMILY_FIELD_PINYIN_GIVEN" in review.reason_codes
    assert japanese.review_label == "not_swapped_or_excluded"
    assert any("SPLIT_REVIEW_EXCLUDED_NON_CHINESE_FAMILY_FIELD" in code for code in japanese.reason_codes)


def test_field_only_treats_initial_family_as_ambiguous_without_surname_evidence():
    order, _, reason = identify_surname_position_from_fields_v8(
        firstname="Lokesh K.",
        lastname="N",
        source="CROSSREF",
    )
    assert order == "unknown"
    assert "FIELD_INITIALS_AMBIGUOUS" in reason


def test_field_only_detects_western_surname_before_initials():
    order, _, reason = identify_surname_position_from_fields_v8(
        firstname="Poyarkov",
        lastname="N.A.",
        source="CROSSREF",
    )
    assert order == "family_first"
    assert "FIELD_GIVEN_WEST_SURNAME_FAMILY_INITIALS" in reason


def test_field_only_trusts_external_split_when_no_counterevidence():
    order, confidence, reason = identify_surname_position_from_fields_v8(
        firstname="Sarah",
        lastname="Wulf Hanson",
        source="CROSSREF",
    )
    assert order == "given_first"
    assert 0.6 <= confidence < 0.8
    assert "FIELD_EXTERNAL_SPLIT_DEFAULT_GIVEN" in reason


def test_split_case_field_only_regressions():
    cases = [
        ("10.1038/nature14656", "M. H. Eileen", "Tan", "given_first", "FIELD_FAMILY_CN_SURNAME_GIVEN_CN_NAME"),
        ("10.1016/j.cja.2025.103654", "Jinheng", "ZHANG", "given_first", "FIELD_FAMILY_CN_SURNAME_GIVEN_CN_NAME"),
        ("10.3897/vz.71.e59307", "Lezhang", "Wei", "given_first", "FIELD_FAMILY_CN_SURNAME_GIVEN_CN_NAME"),
        ("10.1063/1.2137890", "Lan", "Jin", "given_first", "FIELD_DUAL_CN_SURNAME_FREQ_FAMILY"),
        ("10.1016/j.jmmm.2006.01.156", "Lan", "Jin", "given_first", "FIELD_DUAL_CN_SURNAME_FREQ_FAMILY"),
        ("10.24272/j.issn.2095-8137.2021.228", "Jian-Huan", "Yang", "given_first", "FIELD_FAMILY_CN_SURNAME_GIVEN_CN_NAME"),
        ("10.4289/0013-8797.124.2.287", "Li", "Yan", "given_first", "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN"),
        ("10.4289/0013-8797.124.2.287", "Li", "Nan", "given_first", "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN"),
        ("10.1515/pac-2024-0024", "Thi My Hanh Le", "Le", "given_first", "FIELD_FAMILY_SURNAME_WEAK"),
        ("10.1117/12.733422", "Zeng-Guang", "Hou", "given_first", "FIELD_FAMILY_CN_SURNAME_GIVEN_CN_NAME"),
        ("10.3847/1538-4365/ac4414", "Y. Sophia \u6631", "Dai \u6234", "given_first", "FIELD_FAMILY_CJK_SURNAME_HINT"),
        ("10.1111/jvs.13235", "Michele", "Di Musciano", "given_first", "FIELD_FAMILY_CN_SURNAME_GIVEN_CN_NAME"),
        ("10.1088/1674-1056/ad6b84", "Jin \u52b2", "Zhan \u6e5b", "given_first", "FIELD_FAMILY_CJK_SURNAME_HINT"),
        ("10.1088/1674-1056/ad6b84", "Yi \u4e00", "Wang \u738b", "given_first", "FIELD_FAMILY_CJK_SURNAME_HINT"),
        ("10.1088/1674-1056/ad6b84", "Yu \u90c1", "Sui \u968b", "given_first", "FIELD_FAMILY_CJK_SURNAME_HINT"),
        ("10.1109/ton.2025.3592491", "Xu", "Shu", "given_first", "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN"),
        ("10.1007/s12665-023-10937-9", "Wang", "Lei", "given_first", "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN"),
    ]

    for doi, firstname, lastname, expected_order, expected_reason in cases:
        order, _, reason = identify_surname_position_from_fields_v8(
            firstname=firstname,
            lastname=lastname,
            source="CROSSREF",
        )
        assert order == expected_order, doi
        assert expected_reason in reason, doi


def test_field_only_strong_dual_single_rescue_keeps_moderate_ratios_deferred():
    order, confidence, reason = identify_surname_position_from_fields_v8(
        firstname="Li",
        lastname="Yan",
        source="CROSSREF",
    )
    assert order == "given_first"
    assert confidence < 0.75
    assert "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN(" in reason
    assert "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE" not in reason
    assert "FIELD_FAMILY_FIRST_CANDIDATE_DEFERRED" in reason


def test_field_only_strong_dual_single_rescue_is_threshold_configured():
    set_ablation_config(
        AblationConfig(
            enable_strong_dual_single_rescue=True,
            strong_dual_single_rescue_ratio=30.0,
        )
    )
    try:
        order, _, reason = identify_surname_position_from_fields_v8(
            firstname="Xu",
            lastname="Shu",
            source="CROSSREF",
        )
    finally:
        reset_ablation_config()

    assert order == "given_first"
    assert "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE" not in reason
    assert "FIELD_FAMILY_FIRST_CANDIDATE_DEFERRED" in reason


def test_field_only_strong_dual_single_rescue_no_context_requires_explicit_legacy_config():
    set_ablation_config(
        AblationConfig(
            enable_strong_dual_single_rescue=True,
            strong_dual_single_rescue_require_cn_context=False,
        )
    )
    try:
        order, _, reason = identify_surname_position_from_fields_v8(
            firstname="Xu",
            lastname="Shu",
            source="CROSSREF",
        )
    finally:
        reset_ablation_config()

    assert order == "family_first"
    assert "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE_NO_CONTEXT" in reason


def test_field_only_strong_dual_single_rescue_can_require_chinese_context():
    set_ablation_config(
        AblationConfig(
            enable_strong_dual_single_rescue=True,
            strong_dual_single_rescue_require_cn_context=True,
        )
    )
    try:
        order_without_context, _, reason_without_context = identify_surname_position_from_fields_v8(
            firstname="Xu",
            lastname="Shu",
            source="CROSSREF",
        )
        order_with_context, _, reason_with_context = identify_surname_position_from_fields_v8(
            firstname="Xu",
            lastname="Shu",
            affiliation="Tsinghua University, Beijing, China",
            source="CROSSREF",
        )
    finally:
        reset_ablation_config()

    assert order_without_context == "given_first"
    assert "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE" not in reason_without_context
    assert order_with_context == "family_first"
    assert "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE" in reason_with_context


def test_batch_strong_dual_single_rescue_uses_doi_level_context():
    set_ablation_config(
        AblationConfig(
            enable_strong_dual_single_rescue=True,
            strong_dual_single_rescue_require_cn_context=True,
        )
    )
    try:
        decisions = batch_identify_surname_position_v8(
            [
                NameRecord(
                    record_id="candidate",
                    name_raw="",
                    firstname_raw="Xu",
                    lastname_raw="Shu",
                    publication_id="doi-context",
                    source="CROSSREF",
                    field_only=True,
                ),
                NameRecord(
                    record_id="context",
                    name_raw="",
                    firstname_raw="Yuhui",
                    lastname_raw="Liu",
                    affiliation_raw="Tsinghua University, Beijing, China",
                    publication_id="doi-context",
                    source="CROSSREF",
                    field_only=True,
                ),
            ],
            source="CROSSREF",
            enable_person_consistency=False,
            enable_pub_consistency=False,
        )
    finally:
        reset_ablation_config()

    decision = decisions["candidate"]
    assert decision.order == "family_first"
    assert any(
        code.startswith("FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE")
        for code in decision.reason_codes
    )


def test_batch_field_only_ignores_name_raw_even_when_present():
    base = {
        "record_id": "x1",
        "doi": "d1",
        "firstname": "Xu",
        "lastname": "Shu",
        "source": "CROSSREF",
    }
    with_name_raw = {
        **base,
        "name_raw": "some deliberately misleading original name",
        "name": "another misleading full name",
        "full_name": "China China",
        "original_name": "China China",
    }

    without_name = batch_identify_surname_position_v8(
        [base],
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=False,
    )["x1"]
    with_name = batch_identify_surname_position_v8(
        [with_name_raw],
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=False,
    )["x1"]

    assert with_name.order == without_name.order
    assert with_name.confidence == without_name.confidence
    assert with_name.reason_codes == without_name.reason_codes


def test_publication_context_does_not_use_name_raw_for_cn_context():
    set_ablation_config(
        AblationConfig(
            enable_strong_dual_single_rescue=True,
            strong_dual_single_rescue_require_cn_context=True,
        )
    )
    try:
        decisions = batch_identify_surname_position_v8(
            [
                {
                    "record_id": "x1",
                    "doi": "d1",
                    "firstname": "Xu",
                    "lastname": "Shu",
                    "name_raw": "China China China",
                    "source": "CROSSREF",
                }
            ],
            source="CROSSREF",
            enable_person_consistency=False,
            enable_pub_consistency=False,
        )
    finally:
        reset_ablation_config()

    decision = decisions["x1"]
    assert decision.order == "given_first"
    assert not any(
        code.startswith("FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE")
        for code in decision.reason_codes
    )


def test_publication_context_does_not_use_text_publication_context_for_cn_context():
    set_ablation_config(
        AblationConfig(
            enable_strong_dual_single_rescue=True,
            strong_dual_single_rescue_require_cn_context=True,
        )
    )
    try:
        decisions = batch_identify_surname_position_v8(
            [
                {
                    "record_id": "x1",
                    "doi": "d1",
                    "firstname": "Xu",
                    "lastname": "Shu",
                    "publication_context": "China Tsinghua Beijing",
                    "source": "CROSSREF",
                }
            ],
            source="CROSSREF",
            enable_person_consistency=False,
            enable_pub_consistency=False,
        )
    finally:
        reset_ablation_config()

    decision = decisions["x1"]
    assert decision.order == "given_first"
    assert not any(
        code.startswith("FIELD_DUAL_CN_SURNAME_FREQ_GIVEN_STRONG_SINGLE")
        for code in decision.reason_codes
    )


def test_field_only_dual_surnames_require_strong_share_gap():
    order, _, reason = identify_surname_position_from_fields_v8(
        firstname="Jing",
        lastname="Che",
        source="CROSSREF",
    )
    assert order == "given_first"
    assert "FIELD_DUAL_CN_SURNAME_AMBIGUOUS" in reason
    assert "FIELD_EXTERNAL_SPLIT_DEFAULT_GIVEN" in reason


def test_batch_field_only_split_is_decisive_without_original_name():
    records = [
        NameRecord(
            record_id="du-guoming",
            name_raw="",
            firstname_raw="DU",
            lastname_raw="Guoming",
            source="CROSSREF",
            field_only=True,
        )
    ]
    decision = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=False,
    )["du-guoming"]
    assert decision.order == "given_first"
    assert "FIELD_GIVEN_CN_SURNAME_FAMILY_CN_GIVEN" in decision.reason_codes
    assert "FIELD_FAMILY_FIRST_CANDIDATE_DEFERRED" in decision.reason_codes
    assert all(not code.startswith("FIELD_SPLIT_EXACT") for code in decision.reason_codes)


def test_batch_accepts_crossref_style_dict_records():
    decisions = batch_identify_surname_position_v8(
        [
            {
                "record_id": "dict-record",
                "original_name": "Zhao Hongrui",
                "firstname": "Lokesh K.",
                "lastname": "N",
                "source": "CROSSREF",
            }
        ],
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=False,
    )
    decision = decisions["dict-record"]
    assert decision.order == "unknown"
    assert "FIELD_ONLY_INPUT" in decision.reason_codes
    assert all(not code.startswith("FIELD_SPLIT_EXACT") for code in decision.reason_codes)


def test_batch_publication_candidate_group_corrects_only_candidates():
    records = [
        NameRecord(
            record_id=f"candidate-{idx}",
            name_raw="",
                firstname_raw=firstname,
                lastname_raw=lastname,
                affiliation_raw="Chinese Academy of Sciences, Beijing, China",
                publication_id="doi-candidate-group",
                source="CROSSREF",
                field_only=True,
        )
        for idx, (firstname, lastname) in enumerate(
            [
                ("Zhao", "Hongrui"),
                ("Li", "Yan"),
                ("Liu", "Shengdong"),
                ("Li", "Nan"),
                ("Meng", "Qingfan"),
            ]
        )
    ]
    records.append(
        NameRecord(
            record_id="western-coauthor",
            name_raw="",
            firstname_raw="Alexander S.",
            lastname_raw="Prosvirov",
            publication_id="doi-candidate-group",
            source="CROSSREF",
            field_only=True,
        )
    )

    set_ablation_config(
        AblationConfig(
            enable_publication_candidate_group_correction=True,
            publication_candidate_group_min_count=4,
            publication_candidate_group_min_share=0.40,
            publication_candidate_group_min_strong_count=0,
            publication_candidate_group_min_strength_sum=0.0,
            enable_publication_external_split_confidence_guard=False,
        )
    )
    try:
        decisions = batch_identify_surname_position_v8(
            records,
            source="CROSSREF",
            enable_person_consistency=False,
            enable_pub_consistency=True,
        )
    finally:
        reset_ablation_config()

    for idx in range(5):
        assert decisions[f"candidate-{idx}"].order == "family_first"
        assert any(
            code.startswith("PUB_CANDIDATE_GROUP_CORRECTION")
            for code in decisions[f"candidate-{idx}"].reason_codes
        )
    assert decisions["western-coauthor"].order == "given_first"
    assert not any(
        code.startswith("PUB_CANDIDATE_GROUP_CORRECTION")
        for code in decisions["western-coauthor"].reason_codes
    )


def test_raw_name_publication_majority_corrects_dual_surname_candidates():
    records = [
        NameRecord(
            record_id="candidate-1",
            name_raw="Yan Peng",
            affiliation_raw="Tsinghua University, Beijing, China",
            publication_id="doi-raw-majority",
            source="CROSSREF",
        ),
        NameRecord(
            record_id="candidate-2",
            name_raw="Jiang Cheng",
            affiliation_raw="Tsinghua University, Beijing, China",
            publication_id="doi-raw-majority",
            source="CROSSREF",
        ),
        NameRecord(
            record_id="given-1",
            name_raw="Alice Smith",
            publication_id="doi-raw-majority",
            source="CROSSREF",
        ),
        NameRecord(
            record_id="given-2",
            name_raw="Robert Johnson",
            publication_id="doi-raw-majority",
            source="CROSSREF",
        ),
    ]

    local = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=False,
    )
    corrected = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=True,
    )

    assert local["candidate-1"].order == "family_first"
    assert corrected["candidate-1"].order == "given_first"
    assert corrected["candidate-2"].order == "given_first"
    assert any(
        code.startswith("PUB_RAW_GIVEN_MAJORITY_OVERRIDE")
        for code in corrected["candidate-1"].reason_codes
    )


def test_raw_name_publication_majority_requires_given_evidence():
    records = [
        NameRecord(
            record_id="candidate-1",
            name_raw="Yan Peng",
            affiliation_raw="Tsinghua University, Beijing, China",
            publication_id="doi-raw-no-majority",
            source="CROSSREF",
        ),
        NameRecord(
            record_id="candidate-2",
            name_raw="Jiang Cheng",
            affiliation_raw="Tsinghua University, Beijing, China",
            publication_id="doi-raw-no-majority",
            source="CROSSREF",
        ),
    ]

    decisions = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=True,
    )

    assert decisions["candidate-1"].order == "family_first"
    assert not any(
        code.startswith("PUB_RAW_GIVEN_MAJORITY_OVERRIDE")
        for code in decisions["candidate-1"].reason_codes
    )


def test_raw_name_person_majority_corrects_repeated_candidate():
    records = [
        NameRecord(
            record_id="candidate",
            name_raw="Yuan Tian",
            person_id="0000-0000-raw-person",
            source="CROSSREF",
        ),
        NameRecord(
            record_id="given-evidence",
            name_raw="Alice Smith",
            person_id="0000-0000-raw-person",
            source="CROSSREF",
        ),
    ]

    local = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=False,
    )
    corrected = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=True,
        enable_pub_consistency=False,
    )

    assert local["candidate"].order == "family_first"
    assert corrected["candidate"].order == "given_first"
    assert any(
        code.startswith("PERSON_RAW_GIVEN_MAJORITY_OVERRIDE")
        for code in corrected["candidate"].reason_codes
    )


def test_batch_publication_candidate_group_requires_group_support():
    records = [
        NameRecord(
            record_id="candidate",
            name_raw="",
            firstname_raw="Zhao",
            lastname_raw="Hongrui",
            publication_id="doi-sparse-candidate",
            source="CROSSREF",
            field_only=True,
        ),
        NameRecord(
            record_id="given-1",
            name_raw="",
            firstname_raw="Yuhui",
            lastname_raw="Liu",
            publication_id="doi-sparse-candidate",
            source="CROSSREF",
            field_only=True,
        ),
        NameRecord(
            record_id="given-2",
            name_raw="",
            firstname_raw="Tianxiang",
            lastname_raw="Tang",
            publication_id="doi-sparse-candidate",
            source="CROSSREF",
            field_only=True,
        ),
    ]

    decisions = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=True,
    )

    assert decisions["candidate"].order == "given_first"
    assert "FIELD_FAMILY_FIRST_CANDIDATE_DEFERRED" in decisions["candidate"].reason_codes
    assert not any(
        code.startswith("PUB_CANDIDATE_GROUP_CORRECTION")
        for code in decisions["candidate"].reason_codes
    )


def test_batch_publication_candidate_group_thresholds_are_configurable():
    records = [
        NameRecord(
            record_id="candidate-1",
            name_raw="",
            firstname_raw="Zhao",
            lastname_raw="Hongrui",
            affiliation_raw="Chinese Academy of Sciences, Beijing, China",
            publication_id="doi-configurable-candidate-group",
            source="CROSSREF",
            field_only=True,
        ),
        NameRecord(
            record_id="candidate-2",
            name_raw="",
            firstname_raw="Liu",
            lastname_raw="Shengdong",
            affiliation_raw="Chinese Academy of Sciences, Beijing, China",
            publication_id="doi-configurable-candidate-group",
            source="CROSSREF",
            field_only=True,
        ),
        NameRecord(
            record_id="given",
            name_raw="",
            firstname_raw="Yuhui",
            lastname_raw="Liu",
            publication_id="doi-configurable-candidate-group",
            source="CROSSREF",
            field_only=True,
        ),
    ]
    set_ablation_config(
        AblationConfig(
            enable_publication_candidate_group_correction=True,
            publication_candidate_group_min_count=2,
            publication_candidate_group_min_share=0.50,
            publication_candidate_group_min_strong_count=0,
            publication_candidate_group_min_strength_sum=0.0,
            enable_publication_external_split_confidence_guard=False,
        )
    )
    try:
        decisions = batch_identify_surname_position_v8(
            records,
            source="CROSSREF",
            enable_person_consistency=False,
            enable_pub_consistency=True,
        )
    finally:
        reset_ablation_config()

    assert decisions["candidate-1"].order == "family_first"
    assert decisions["candidate-2"].order == "family_first"
    assert any(
        code.startswith("PUB_CANDIDATE_GROUP_CORRECTION")
        for code in decisions["candidate-1"].reason_codes
    )


def test_batch_publication_candidate_group_final_profile_is_default():
    records = [
        NameRecord(
            record_id=f"candidate-{idx}",
            name_raw="",
            firstname_raw=firstname,
            lastname_raw=lastname,
            publication_id="doi-publication-default-off",
            source="CROSSREF",
            field_only=True,
        )
        for idx, (firstname, lastname) in enumerate(
            [
                ("Zhao", "Hongrui"),
                ("Li", "Yan"),
                ("Liu", "Shengdong"),
                ("Li", "Nan"),
            ]
        )
    ]

    decisions = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=True,
    )

    assert decisions["candidate-0"].order == "given_first"
    assert decisions["candidate-1"].order == "family_first"
    assert decisions["candidate-2"].order == "given_first"
    assert decisions["candidate-3"].order == "family_first"
    assert any(
        code.startswith("PUB_CANDIDATE_GROUP_CORRECTION")
        for code in decisions["candidate-1"].reason_codes
    )
    assert any(
        code.startswith("PUB_PATTERN_OVERRIDE_SUPPRESSED_BY_EXTERNAL_SPLIT_CONFIDENCE")
        for code in decisions["candidate-0"].reason_codes
    )


def test_publication_candidate_group_guard_suppresses_external_split_override():
    records = [
        NameRecord(
            record_id=f"candidate-{idx}",
            name_raw="",
            firstname_raw=firstname,
            lastname_raw=lastname,
            publication_id="doi-publication-guard",
            source="CROSSREF",
            field_only=True,
        )
        for idx, (firstname, lastname) in enumerate(
            [
                ("Zhao", "Hongrui"),
                ("Liu", "Shengdong"),
                ("Meng", "Qingfan"),
                ("Guo", "Qingbiao"),
            ]
        )
    ]
    set_ablation_config(
        AblationConfig(
            enable_publication_candidate_group_correction=True,
            publication_candidate_group_min_count=4,
            publication_candidate_group_min_share=0.40,
            publication_candidate_group_min_strong_count=0,
            publication_candidate_group_min_strength_sum=0.0,
        )
    )
    try:
        decisions = batch_identify_surname_position_v8(
            records,
            source="CROSSREF",
            enable_person_consistency=False,
            enable_pub_consistency=True,
        )
    finally:
        reset_ablation_config()

    guarded = decisions["candidate-0"]
    assert guarded.order == "given_first"
    assert "PUB_PATTERN_OVERRIDE" not in guarded.reason_codes
    assert "PUB_PATTERN_OVERRIDE_SUPPRESSED_BY_EXTERNAL_SPLIT_CONFIDENCE" in guarded.reason_codes


def test_batch_publication_candidate_group_does_not_fill_unknowns():
    records = [
        NameRecord(
            record_id=f"candidate-{idx}",
            name_raw="",
            firstname_raw=firstname,
            lastname_raw=lastname,
            publication_id="doi-candidate-with-unknown",
            source="CROSSREF",
            field_only=True,
        )
        for idx, (firstname, lastname) in enumerate(
            [
                ("Zhao", "Hongrui"),
                ("Li", "Yan"),
                ("Liu", "Shengdong"),
                ("Li", "Nan"),
            ]
        )
    ]
    records.append(
        NameRecord(
            record_id="unknown",
            name_raw="",
            firstname_raw="Lokesh K.",
            lastname_raw="N",
            publication_id="doi-candidate-with-unknown",
            source="CROSSREF",
            field_only=True,
        )
    )

    decisions = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=False,
        enable_pub_consistency=True,
    )

    assert decisions["unknown"].order == "unknown"
    assert not any(
        code.startswith("PUB_CANDIDATE_GROUP_CORRECTION")
        for code in decisions["unknown"].reason_codes
    )


def test_batch_publication_candidate_group_can_correct_dual_surname_candidate():
    records = [
        NameRecord(
            record_id=f"candidate-{idx}",
            name_raw="",
                firstname_raw=firstname,
                lastname_raw=lastname,
                affiliation_raw="Chinese Academy of Sciences, Beijing, China",
                publication_id="doi-china-group",
                source="CROSSREF",
                field_only=True,
        )
        for idx, (firstname, lastname) in enumerate(
            [
                ("Zheng", "Meinan"),
                ("Guo", "Qingbiao"),
                ("Zhao", "Ruonan"),
                ("Wang", "Lei"),
                ("Han", "Yafang"),
            ]
        )
    ]

    set_ablation_config(
        AblationConfig(
            enable_publication_candidate_group_correction=True,
            publication_candidate_group_min_count=4,
            publication_candidate_group_min_share=0.40,
            publication_candidate_group_min_strong_count=0,
            publication_candidate_group_min_strength_sum=0.0,
            enable_publication_external_split_confidence_guard=False,
        )
    )
    try:
        decisions = batch_identify_surname_position_v8(
            records,
            source="CROSSREF",
            enable_person_consistency=False,
            enable_pub_consistency=True,
        )
    finally:
        reset_ablation_config()

    assert decisions["candidate-3"].order == "family_first"
    assert any(
        code.startswith("PUB_CANDIDATE_GROUP_CORRECTION")
        for code in decisions["candidate-3"].reason_codes
    )


def test_duplicate_split_fields_are_not_decisive():
    order, _, reason = identify_surname_position_from_fields_v8(
        firstname="Piradov",
        lastname="Piradov",
        source="CROSSREF",
    )
    assert order == "unknown"
    assert "FIELD_GIVEN_FAMILY_DUPLICATE" in reason


def test_structural_family_fullname_reason_codes():
    decision = local_decision(
        NameRecord(
            record_id="structural",
            name_raw="Zhu Yongqiang",
            firstname_raw="朱勇强",
            lastname_raw="Zhu Yongqiang",
            source="CROSSREF",
        ),
        get_config("CROSSREF"),
    )
    assert "FIELD_FAMILY_MATCHES_FULL_NAME" in decision.reason_codes
    assert "FIELD_FAMILY_FULLNAME_GIVEN_CJK" in decision.reason_codes
    assert "FIELD_SPLIT_MISMATCH" in decision.reason_codes


def test_given_field_compound_surname_prefix_reason_codes():
    order, _, reason = identify_surname_position_from_fields_v8(
        firstname="Ouyang Ming",
        lastname="Li",
        source="CROSSREF",
    )
    assert order in ["given_first", "unknown"]
    assert "FIELD_GIVEN_COMPOUND_SURNAME_PREFIX" in reason


def test_single_token_compound_surname_is_not_hard_error():
    order, _, reason = identify_surname_position_from_fields_v8(
        firstname="Chunyu",
        lastname="Xu",
        source="CROSSREF",
    )
    assert order == "given_first"
    assert "FIELD_GIVEN_COMPOUND_SURNAME_SINGLE_TOKEN_DIAG" in reason


def test_edge_cases():
    order, _, _ = identify_surname_position_v8("")
    assert order == "unknown"

    order, _, _ = identify_surname_position_v8("Liu")
    assert order == "unknown"

    order, _, _ = identify_surname_position_v8("A.B.")
    assert order == "unknown"

    order, _, _ = identify_surname_position_v8("Liu, Wei")
    assert order in ["family_first", "given_first", "unknown"]

    order, _, _ = identify_surname_position_v8("Jean-Pierre Martin")
    assert order == "given_first"


def test_none_handling():
    order, _, _ = identify_surname_position_v8("Liu Wei", affiliation=None)
    assert order in ["family_first", "given_first"]

    order, _, _ = identify_surname_position_v8("Liu Wei", source=None)
    assert order in ["family_first", "given_first"]


def test_unicode_handling():
    order, _, _ = identify_surname_position_v8("José García")
    assert order == "given_first"

    order, _, _ = identify_surname_position_v8("Иванов Иван")
    assert order in ["family_first", "given_first", "unknown"]


def test_preprocess_name():
    parsed = preprocess_name("Liu Wei")
    assert len(parsed.tokens) == 2
    assert parsed.first_idx == 0
    assert parsed.last_idx == 1

    parsed = preprocess_name("Liu W.X.")
    assert len(parsed.tokens) == 2
    assert parsed.tokens[1].is_initial

    parsed = preprocess_name("Liu, Wei (刘伟)")
    assert len(parsed.tokens) >= 2

    parsed = preprocess_name("")
    assert len(parsed.tokens) == 0
    assert parsed.first_idx == -1


def test_mode_detection():
    cfg = get_config("DEFAULT")

    record = NameRecord(
        record_id="1",
        name_raw="Zhang Tianxiang",
        affiliation_raw="Tsinghua University",
    )
    parsed = preprocess_name(record.name_raw)
    mode = detect_mode(record, parsed, cfg)
    assert mode == "CHINESE"

    record = NameRecord(
        record_id="2",
        name_raw="David Smith",
    )
    parsed = preprocess_name(record.name_raw)
    mode = detect_mode(record, parsed, cfg)
    assert mode == "WESTERN"


def test_batch_processing_basic():
    records = [
        NameRecord(record_id="1", name_raw="Liu Wei", source="CROSSREF"),
        NameRecord(record_id="2", name_raw="David Smith", source="CROSSREF"),
        NameRecord(record_id="3", name_raw="Zhang Tianxiang", source="ISTINA"),
    ]

    decisions = batch_identify_surname_position_v8(
        records,
        enable_person_consistency=False,
        enable_pub_consistency=False,
    )

    assert len(decisions) == 3
    assert all(rid in decisions for rid in ["1", "2", "3"])
    assert decisions["2"].order == "given_first"


def test_batch_person_consistency():
    records = [
        NameRecord(
            record_id="1",
            name_raw="Liu Wei",
            person_id="P001",
            source="CROSSREF",
        ),
        NameRecord(
            record_id="2",
            name_raw="Wei Liu",
            person_id="P001",
            source="CROSSREF",
        ),
        NameRecord(
            record_id="3",
            name_raw="Liu W.",
            person_id="P001",
            source="CROSSREF",
        ),
    ]

    decisions = batch_identify_surname_position_v8(
        records,
        enable_person_consistency=True,
        enable_pub_consistency=False,
    )

    assert decisions["3"].order == "family_first"
    assert decisions["3"].confidence == 1.0


def test_batch_publication_consistency():
    records = [
        NameRecord(
            record_id="1",
            name_raw="Tang Tianxiang",
            publication_id="PUB001",
            source="CROSSREF",
            affiliation_raw="Tsinghua University",
        ),
        NameRecord(
            record_id="2",
            name_raw="Liu Yuhui",
            publication_id="PUB001",
            source="CROSSREF",
            affiliation_raw="Peking University",
        ),
        NameRecord(
            record_id="3",
            name_raw="Wang ABC",
            publication_id="PUB001",
            source="CROSSREF",
        ),
    ]

    decisions = batch_identify_surname_position_v8(
        records,
        enable_person_consistency=False,
        enable_pub_consistency=True,
    )

    assert len(decisions) == 3


def run_all_tests(output_file=None):
    """Legacy script-style test runner."""
    if output_file:
        f = open(output_file, "w", encoding="utf-8")
    else:
        f = None

    def log(msg):
        if f:
            f.write(msg + "\n")
        print(msg)

    tests = [
        ("abbreviation", test_abbreviation_detection),
        ("chinese_mode_basic", test_chinese_mode_basic),
        ("single_syllable_optimization", test_chinese_single_syllable_optimization),
        ("double_surname", test_double_surname),
        ("share_lookup_and_aggregation", test_surname_frequency_share_lookup_and_aggregation),
        ("share_ratio_double_surname_regressions", test_share_ratio_double_surname_regressions),
        ("western_mode", test_western_mode),
        ("mixed_mode", test_mixed_mode),
        ("source_specific_crossref", test_source_specific_crossref),
        ("source_specific_istina", test_source_specific_istina),
        ("source_specific_orcid", test_source_specific_orcid),
        ("split_field_exact_alignment", test_split_field_exact_alignment_reason_codes),
        ("split_field_exact_given_boundary", test_split_field_exact_given_overrides_cn_boundary_unknown),
        ("split_field_exact_given_abbrev", test_split_field_exact_given_overrides_abbreviation_rule),
        ("duplicate_split_fields_proxy_skip", test_duplicate_split_fields_are_not_proxy_labels),
        ("structural_family_fullname", test_structural_family_fullname_reason_codes),
        ("given_field_compound_prefix", test_given_field_compound_surname_prefix_reason_codes),
        ("single_token_compound_surname_soft_signal", test_single_token_compound_surname_is_not_hard_error),
        ("edge_cases", test_edge_cases),
        ("none_handling", test_none_handling),
        ("unicode_handling", test_unicode_handling),
        ("preprocess_name", test_preprocess_name),
        ("mode_detection", test_mode_detection),
        ("batch_processing_basic", test_batch_processing_basic),
        ("batch_person_consistency", test_batch_person_consistency),
        ("batch_publication_consistency", test_batch_publication_consistency),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            log(f"[PASS] {name}")
            passed += 1
        except AssertionError as e:
            log(f"[FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            log(f"[ERROR] {name}: {e}")
            failed += 1

    log(f"\n{'=' * 60}")
    log(f"Test Results: {passed} passed, {failed} failed")
    log(f"{'=' * 60}")

    if f:
        f.close()

    return failed == 0


if __name__ == "__main__":
    import os

    output_path = os.path.join(os.path.dirname(__file__), "..", "test_v8_results.txt")
    success = run_all_tests(output_file=output_path)
    print(f"\nResults saved to: {output_path}")
    sys.exit(0 if success else 1)
