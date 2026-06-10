from experiments.evaluate_special_split_cases import (
    FIRST_NOT_SURNAME_FIELD,
    TWO_SYLLABLE_FAMILY_FIELD,
    evaluate_dataset,
    summarize_dataset,
)


def test_two_syllable_special_cases_document_conservative_production_profile():
    results = evaluate_dataset("two_syllable_family_field", TWO_SYLLABLE_FAMILY_FIELD)
    summary = summarize_dataset("two_syllable_family_field", results)

    assert summary["manual_counts"] == {
        "reliable_swapped": 64,
        "exclude_or_check": 11,
    }
    assert summary["production_counts"] == {"not_swapped": 75}
    assert summary["production_reliable_swapped_found"] == 0
    assert summary["review_signal_counts"] == {
        "reliable_swapped": 62,
        "exclude_or_check": 5,
    }
    assert summary["review_signal_reliable_found"] == 62


def test_single_syllable_special_cases_remain_review_only():
    results = evaluate_dataset("first_not_surname_field", FIRST_NOT_SURNAME_FIELD)
    summary = summarize_dataset("first_not_surname_field", results)

    assert summary["manual_counts"] == {
        "reliable_swapped": 10,
        "possible_check": 10,
        "not_reliable": 1,
    }
    assert summary["production_counts"] == {
        "not_swapped": 20,
        "unknown": 1,
    }
    assert summary["production_reliable_swapped_found"] == 0
    assert summary["review_signal_counts"] == {
        "possible_check": 8,
        "reliable_swapped": 9,
        "not_reliable": 1,
    }
    assert summary["review_signal_reliable_found"] == 9
