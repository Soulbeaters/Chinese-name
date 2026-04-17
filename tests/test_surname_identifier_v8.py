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
    identify_surname_position_v8,
    local_decision,
    preprocess_name,
)


def _local_strategy_decision(
    name_raw: str,
    strategy: str = "share_ratio",
    source: str = "CROSSREF",
):
    """Exercise a specific double-surname frequency strategy directly."""
    set_ablation_config(AblationConfig(surname_freq_strategy=strategy))
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
    assert decision.order == "family_first"
    assert "CN_SURNAME_DOUBLE_DEFAULT_FAM" in decision.reason_codes
    assert all(not code.startswith("CN_SURNAME_DOUBLE_FREQ_") for code in decision.reason_codes)


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
