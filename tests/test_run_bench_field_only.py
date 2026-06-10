from experiments.run_bench import evaluate_algorithm, get_true_order


def test_get_true_order_never_infers_from_original_name():
    record = {
        "original_name": "Zhao Hongrui",
        "firstname": "Hongrui",
        "lastname": "Zhao",
    }

    assert get_true_order(record) is None


def test_evaluate_algorithm_uses_field_only_inputs_and_explicit_labels():
    records = [
        {
            "original_name": "N.A. Poyarkov",
            "firstname": "Poyarkov",
            "lastname": "N.A.",
            "true_position": "family_first",
            "source": "CROSSREF",
            "doi": "10.0000/swapped",
        },
        {
            "original_name": "Zhao Hongrui",
            "firstname": "Lokesh K.",
            "lastname": "N",
            "true_position": "given_first",
            "source": "CROSSREF",
            "doi": "10.0000/ambiguous",
        },
        {
            "original_name": "Liu Yuhui",
            "firstname": "Yuhui",
            "lastname": "Liu",
            "source": "CROSSREF",
            "doi": "10.0000/unlabeled",
        },
    ]

    result, errors, field_summary = evaluate_algorithm(
        records,
        config_name="field_only_test",
        force_source="CROSSREF",
    )

    assert result["input_mode"] == "field_only_firstname_lastname"
    assert result["label_mode"] == "explicit_true_position_only"
    assert result["labeled_total"] == 2
    assert result["skipped_count"] == 1
    assert result["correct_count"] == 1
    assert result["unknown_count"] == 1

    assert len(errors) == 1
    assert errors[0]["firstname"] == "Lokesh K."
    assert errors[0]["lastname"] == "N"
    assert errors[0]["predicted"] == "unknown"
    assert "original_name" not in errors[0]

    skipped = field_summary["skipped_examples"]
    assert skipped[0]["skip_reason"] == "missing_true_position"
    assert "original_name" not in skipped[0]

    for samples in field_summary["samples"].values():
        for sample in samples:
            assert "original_name" not in sample
