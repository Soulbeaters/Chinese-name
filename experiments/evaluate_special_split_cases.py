#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluate advisor-provided Crossref split-field special cases.

The cases are stored as Crossref (family, given) tuples. They are evaluated
with the final production field-only batch API. Additional audit signals are
reported from existing reason codes and existing pinyin/surname resources, but
those audit signals do not change the production decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.surname_pinyin_db import is_surname_pinyin
from src.pinyin_validator import is_valid_pinyin_name
from src.surname_identifier_v8 import (
    NameRecord,
    _joined_ascii,
    _non_initial_tokens,
    batch_identify_surname_position_v8,
    preprocess_name,
    review_crossref_split_fields_v8,
)


Pair = Tuple[str, str]


TWO_SYLLABLE_FAMILY_FIELD: List[Pair] = [
    ("Boning", "Gao"),
    ("Kai-bin", "Zhao"),
    ("Yanan", "Lu"),
    ("Baoqiang", "Li"),
    ("Mingfeng", "Zhao"),
    ("Xueping", "Zhu"),
    ("Takahashi", "Mai"),
    ("Jinchi", "Hao"),
    ("Kaichen", "Huang"),
    ("Nakamura", "Mei"),
    ("Zhibo", "Deng"),
    ("Owada", "Mao"),
    ("Qingrong", "Chen"),
    ("Zhen-Chuan", "Wen"),
    ("Tiantian", "Dong"),
    ("Molina", "Chai"),
    ("Meiying", "WANG"),
    ("Junwen", "Liu"),
    ("Zakaria", "Mai"),
    ("Pengfei", "Pang"),
    ("Chuan-Peng", "Hu"),
    ("Mengmeng", "Xu"),
    ("Jianfei", "Li"),
    ("Zijia", "Chu"),
    ("Jianjun", "Xu"),
    ("Chunhua", "Xi"),
    ("Junwen", "Xiong"),
    ("Tanghua", "Li"),
    ("Yongquan", "Huang"),
    ("Qianqian", "Zhang"),
    ("Shuxian", "Li"),
    ("Dediu", "Dan"),
    ("Xiufang", "Lv"),
    ("Meilan", "Hu"),
    ("Ouchi", "Mai"),
    ("Chengxun", "Yuan"),
    ("Yuejuan", "Xu"),
    ("Xudong", "Sun"),
    ("Obayashi", "Ren"),
    ("Weiming", "Guo"),
    ("Kawase", "Jin"),
    ("Jianyong", "Zhang"),
    ("Min-Hua", "Zheng"),
    ("Songyang", "Zhou"),
    ("Yiping", "Wei"),
    ("Ziyue", "An"),
    ("Dandan", "Zhao"),
    ("Guohui", "Li"),
    ("Murayama", "Kou"),
    ("Richao", "Cong"),
    ("Lili", "Wu"),
    ("Xiaoshuai", "Ren"),
    ("Chengyuan", "Wang"),
    ("Weijing", "Zhang"),
    ("Sitong", "Chen"),
    ("Jinhua", "Peng"),
    ("Haiyan", "Lu"),
    ("Jingfeng", "Yao"),
    ("Melin", "Bo"),
    ("Zhongxiang", "Zhou"),
    ("xiaolin", "xiong"),
    ("Ruoyu", "Zhang"),
    ("Zijian", "Liu"),
    ("Zeyu", "Fan"),
    ("Jinjin", "Cheng"),
    ("Tianxiang", "Tang"),
    ("Huanwen", "Chen"),
    ("Qingxian", "Kuang"),
    ("Kang-Wen", "Qiu"),
    ("Benlin", "Yi"),
    ("Jianguo", "Zhang"),
    ("Yongzhong", "Ouyang"),
    ("Lulu", "Li"),
    ("Zhongkai", "Wang"),
    ("Chaoming", "Mei"),
]

TWO_SYLLABLE_EXCLUDE_OR_CHECK: set[Pair] = {
    ("Takahashi", "Mai"),
    ("Nakamura", "Mei"),
    ("Owada", "Mao"),
    ("Ouchi", "Mai"),
    ("Obayashi", "Ren"),
    ("Kawase", "Jin"),
    ("Murayama", "Kou"),
    ("Dediu", "Dan"),
    ("Molina", "Chai"),
    ("Zakaria", "Mai"),
    ("Melin", "Bo"),
}

FIRST_NOT_SURNAME_FIELD: List[Pair] = [
    ("Kun", "Sun"),
    ("Juan", "Yun"),
    ("Bang", "Dan"),
    ("Te", "Yao"),
    ("La", "Ming"),
    ("Bu", "Shu"),
    ("Tie", "Yan"),
    ("Zhuan", "Yuan"),
    ("Bu", "Fan"),
    ("Lun", "Fei"),
    ("Kai", "Wang"),
    ("Neng", "Huang"),
    ("E", "Peng"),
    ("Jun", "Ren"),
    ("Kai", "Yan"),
    ("Tuo", "Wu"),
    ("Ci", "Hui"),
    ("Bing", "Nan"),
    ("Shui", "Yuan"),
    ("Gang", "Shu"),
    ("Fen", "Li"),
]

FIRST_NOT_SURNAME_RELIABLE: set[Pair] = {
    ("Kun", "Sun"),
    ("Te", "Yao"),
    ("Zhuan", "Yuan"),
    ("Bu", "Fan"),
    ("Kai", "Wang"),
    ("Neng", "Huang"),
    ("E", "Peng"),
    ("Jun", "Ren"),
    ("Tuo", "Wu"),
    ("Fen", "Li"),
}

FIRST_NOT_SURNAME_POSSIBLE: set[Pair] = {
    ("Tie", "Yan"),
    ("Kai", "Yan"),
    ("Shui", "Yuan"),
    ("Bang", "Dan"),
    ("Lun", "Fei"),
    ("Juan", "Yun"),
    ("Gang", "Shu"),
    ("Bu", "Shu"),
    ("Ci", "Hui"),
    ("Bing", "Nan"),
}


@dataclass
class CaseResult:
    dataset: str
    index: int
    family_field: str
    given_field: str
    manual_label: str
    production_order: str
    production_label: str
    confidence: float
    mode: str
    reason_codes: List[str]
    review_label: str
    review_confidence: float
    review_reason_codes: List[str]
    audit_signals: Dict[str, Any]
    corrected_name_if_swapped: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="runs/special_crossref_split_cases",
        help="Directory for JSON and Markdown outputs.",
    )
    return parser.parse_args()


def normalize_tokens(value: str) -> List[str]:
    parsed = preprocess_name(value)
    tokens = _non_initial_tokens(parsed.tokens)
    if not tokens:
        tokens = parsed.tokens
    return [token.ascii.lower() for token in tokens if token.ascii]


def joined_ascii(value: str) -> str:
    parsed = preprocess_name(value)
    tokens = _non_initial_tokens(parsed.tokens)
    if not tokens:
        tokens = parsed.tokens
    return _joined_ascii(tokens).lower()


def pinyin_features(value: str) -> Dict[str, Any]:
    joined = joined_ascii(value)
    is_valid, syllable_count, syllables = is_valid_pinyin_name(joined)
    return {
        "joined_ascii": joined,
        "tokens": normalize_tokens(value),
        "is_cn_surname": is_surname_pinyin(joined),
        "is_valid_pinyin": is_valid,
        "pinyin_syllable_count": syllable_count,
        "pinyin_syllables": syllables,
    }


def manual_label(dataset: str, pair: Pair) -> str:
    if dataset == "two_syllable_family_field":
        if pair in TWO_SYLLABLE_EXCLUDE_OR_CHECK:
            return "exclude_or_check"
        return "reliable_swapped"
    if pair in FIRST_NOT_SURNAME_RELIABLE:
        return "reliable_swapped"
    if pair in FIRST_NOT_SURNAME_POSSIBLE:
        return "possible_check"
    return "not_reliable"


def production_label(order: str) -> str:
    if order == "family_first":
        return "swapped"
    if order == "given_first":
        return "not_swapped"
    return "unknown"


def reason_has(reason_codes: Sequence[str], value: str) -> bool:
    return any(code == value or code.startswith(value) for code in reason_codes)


def audit_signals(family_field: str, given_field: str, reason_codes: Sequence[str]) -> Dict[str, Any]:
    family = pinyin_features(family_field)
    given = pinyin_features(given_field)
    reason_list = list(reason_codes)
    return {
        "family_field_features": family,
        "given_field_features": given,
        "strong_reverse_reason": reason_has(reason_list, "FIELD_GIVEN_CN_SURNAME_FAMILY_CN_GIVEN"),
        "candidate_deferred": reason_has(reason_list, "FIELD_FAMILY_FIRST_CANDIDATE_DEFERRED"),
        "dual_surname_freq_given": reason_has(reason_list, "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN"),
        "given_surname_weak": reason_has(reason_list, "FIELD_GIVEN_SURNAME_WEAK"),
        "external_split_default": reason_has(reason_list, "FIELD_EXTERNAL_SPLIT_DEFAULT_GIVEN"),
        "two_syllable_family_review_signal": (
            reason_has(reason_list, "FIELD_GIVEN_CN_SURNAME_FAMILY_CN_GIVEN")
        ),
        "single_syllable_review_signal": (
            reason_has(reason_list, "FIELD_GIVEN_SURNAME_WEAK")
            or reason_has(reason_list, "FIELD_DUAL_CN_SURNAME_FREQ_GIVEN")
        ),
    }


def evaluate_dataset(dataset: str, pairs: Sequence[Pair]) -> List[CaseResult]:
    records = [
        NameRecord(
            record_id=f"{dataset}-{idx}",
            source="CROSSREF",
            name_raw="",
            firstname_raw=given_field,
            lastname_raw=family_field,
            field_only=True,
        )
        for idx, (family_field, given_field) in enumerate(pairs)
    ]
    decisions = batch_identify_surname_position_v8(records, source="CROSSREF")
    results: List[CaseResult] = []
    for idx, (family_field, given_field) in enumerate(pairs):
        decision = decisions[f"{dataset}-{idx}"]
        review = review_crossref_split_fields_v8(
            firstname=given_field,
            lastname=family_field,
            source="CROSSREF",
        )
        results.append(
            CaseResult(
                dataset=dataset,
                index=idx + 1,
                family_field=family_field,
                given_field=given_field,
                manual_label=manual_label(dataset, (family_field, given_field)),
                production_order=decision.order,
                production_label=production_label(decision.order),
                confidence=round(decision.confidence, 6),
                mode=decision.mode,
                reason_codes=list(decision.reason_codes),
                review_label=review.review_label,
                review_confidence=round(review.confidence, 6),
                review_reason_codes=list(review.reason_codes),
                audit_signals=audit_signals(family_field, given_field, decision.reason_codes),
                corrected_name_if_swapped=f"{given_field} {family_field}",
            )
        )
    return results


def count_by_manual(results: Iterable[CaseResult], predicate: Callable[[CaseResult], bool]) -> Dict[str, int]:
    return dict(Counter(item.manual_label for item in results if predicate(item)))


def summarize_dataset(dataset: str, results: List[CaseResult]) -> Dict[str, Any]:
    if dataset == "two_syllable_family_field":
        review_key = "two_syllable_family_review_signal"
    else:
        review_key = "single_syllable_review_signal"
    reliable = [item for item in results if item.manual_label == "reliable_swapped"]
    non_reliable = [item for item in results if item.manual_label != "reliable_swapped"]
    return {
        "dataset": dataset,
        "total": len(results),
        "manual_counts": dict(Counter(item.manual_label for item in results)),
        "production_counts": dict(Counter(item.production_label for item in results)),
        "review_counts": dict(Counter(item.review_label for item in results)),
        "production_reliable_swapped_found": sum(
            item.production_label == "swapped" for item in reliable
        ),
        "production_reliable_swapped_total": len(reliable),
        "production_non_reliable_marked_swapped": sum(
            item.production_label == "swapped" for item in non_reliable
        ),
        "review_likely_reliable_found": sum(
            item.review_label == "likely_swapped" for item in reliable
        ),
        "review_likely_reliable_total": len(reliable),
        "review_likely_non_reliable_marked": [
            {
                "family_field": item.family_field,
                "given_field": item.given_field,
                "manual_label": item.manual_label,
            }
            for item in non_reliable
            if item.review_label == "likely_swapped"
        ],
        "review_likely_reliable_missed": [
            {
                "family_field": item.family_field,
                "given_field": item.given_field,
                "manual_label": item.manual_label,
            }
            for item in reliable
            if item.review_label != "likely_swapped"
        ],
        "review_signal": review_key,
        "review_signal_counts": count_by_manual(
            results,
            lambda item: bool(item.audit_signals[review_key]),
        ),
        "review_signal_reliable_found": sum(
            bool(item.audit_signals[review_key]) for item in reliable
        ),
        "review_signal_reliable_total": len(reliable),
        "review_signal_non_reliable_marked": [
            {
                "family_field": item.family_field,
                "given_field": item.given_field,
                "manual_label": item.manual_label,
            }
            for item in non_reliable
            if item.audit_signals[review_key]
        ],
        "review_signal_reliable_missed": [
            {
                "family_field": item.family_field,
                "given_field": item.given_field,
                "manual_label": item.manual_label,
            }
            for item in reliable
            if not item.audit_signals[review_key]
        ],
    }


def truncate_reason(reason_codes: Sequence[str], limit: int = 120) -> str:
    text = ", ".join(reason_codes)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def render_markdown(results: List[CaseResult], summaries: List[Dict[str, Any]]) -> str:
    by_dataset: Dict[str, List[CaseResult]] = {}
    for item in results:
        by_dataset.setdefault(item.dataset, []).append(item)

    lines = [
        "# Special Crossref Split-Field Cases",
        "",
        "These are advisor-provided Crossref `(family, given)` tuples.",
        "The production label is the final v8 field-only batch API output.",
        "Audit signals are diagnostic only and do not change the production decision.",
        "",
        "## Summary",
        "",
        "| Dataset | Total | Manual labels | Production labels | Opt-in review labels | Review signal | Review signal by manual label |",
        "|---|---:|---|---|---|---|---|",
    ]
    for summary in summaries:
        lines.append(
            "| {dataset} | {total} | {manual} | {prod} | {review_labels} | {signal} | {review} |".format(
                dataset=summary["dataset"],
                total=summary["total"],
                manual=json.dumps(summary["manual_counts"], ensure_ascii=False),
                prod=json.dumps(summary["production_counts"], ensure_ascii=False),
                review_labels=json.dumps(summary["review_counts"], ensure_ascii=False),
                signal=summary["review_signal"],
                review=json.dumps(summary["review_signal_counts"], ensure_ascii=False),
            )
        )

    for dataset, items in by_dataset.items():
        lines.extend(
            [
                "",
                f"## {dataset}",
                "",
                "| # | Crossref family | Crossref given | Manual | Production | Confidence | Audit flags | Reason codes |",
                "|---:|---|---|---|---|---:|---|---|",
            ]
        )
        for item in items:
            flags = [
                name
                for name in [
                    "strong_reverse_reason",
                    "candidate_deferred",
                    "dual_surname_freq_given",
                    "given_surname_weak",
                    "external_split_default",
                ]
                if item.audit_signals[name]
            ]
            lines.append(
                "| {idx} | {family} | {given} | {manual} | {prod} ({order}); review={review_label} | {conf:.3f} | {flags} | {reason} |".format(
                    idx=item.index,
                    family=item.family_field,
                    given=item.given_field,
                    manual=item.manual_label,
                    prod=item.production_label,
                    order=item.production_order,
                    review_label=item.review_label,
                    conf=item.confidence,
                    flags=", ".join(flags),
                    reason=truncate_reason(item.reason_codes).replace("|", "/"),
                )
            )

    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = (
        evaluate_dataset("two_syllable_family_field", TWO_SYLLABLE_FAMILY_FIELD)
        + evaluate_dataset("first_not_surname_field", FIRST_NOT_SURNAME_FIELD)
    )
    summaries = [
        summarize_dataset("two_syllable_family_field", [r for r in results if r.dataset == "two_syllable_family_field"]),
        summarize_dataset("first_not_surname_field", [r for r in results if r.dataset == "first_not_surname_field"]),
    ]

    payload = {
        "interpretation": {
            "production_label": "family_first means Crossref fields are likely swapped; given_first means fields are treated as valid.",
            "audit_signals": "diagnostic only; they do not change final production decisions",
        },
        "summaries": summaries,
        "results": [asdict(item) for item in results],
    }
    (output_dir / "special_split_cases.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "special_split_cases.md").write_text(
        render_markdown(results, summaries),
        encoding="utf-8",
    )

    print(json.dumps({"output_dir": str(output_dir.resolve()), "summaries": summaries}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
