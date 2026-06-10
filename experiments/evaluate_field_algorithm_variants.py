# -*- coding: utf-8 -*-
"""
Compare field-only surname-order algorithms on the advisor ISTINA DOI set.

The experiment intentionally uses only Crossref given/family fields. It never
uses original_name/full_name as evidence or as a proxy label.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.surname_pinyin_db import is_surname_pinyin
from src.surname_identifier_v8 import (
    _field_confidence_from_delta,
    _joined_ascii,
    _non_initial_tokens,
    _parsed_field,
    batch_identify_surname_position_v8,
    identify_surname_position_from_fields_v8,
    NameRecord,
)


ISTINA_DIR = Path("C:/istina") / "materia \u6750\u6599" / "\u6d4b\u8bd5\u8868\u5355"
DOI_PATH = ISTINA_DIR / "istina_dois.json"
ISTINA_OUT_PATH = ISTINA_DIR / "istina_out.txt"
RAW_PATH = Path("runs/advisor_doi_20260507/advisor_doi_crossref_api_raw.jsonl")
OUTPUT_DIR = Path("runs/field_algorithm_variant_eval")


@dataclass
class AuthorRow:
    row_id: int
    doi: str
    author_index: int
    given: str
    family: str


@dataclass
class Decision:
    order: str
    confidence: float
    reason: str


def field_key(value: str) -> str:
    parsed = _parsed_field(value)
    content = _non_initial_tokens(parsed.tokens)
    if not content:
        content = parsed.tokens
    if not content:
        return ""
    joined = _joined_ascii(content)
    head = content[0].ascii.lower()
    if is_surname_pinyin(joined):
        return joined
    return head


def load_raw_by_doi() -> Dict[str, Dict[str, Any]]:
    raw_by_doi: Dict[str, Dict[str, Any]] = {}
    for line in RAW_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        doi = (
            obj.get("doi")
            or obj.get("DOI")
            or obj.get("message", {}).get("DOI")
            or ""
        ).strip().lower()
        if doi:
            raw_by_doi[doi] = obj
    return raw_by_doi


def load_rows() -> Tuple[List[AuthorRow], List[str]]:
    dois = [d.strip().lower() for d in json.loads(DOI_PATH.read_text(encoding="utf-8"))]
    raw_by_doi = load_raw_by_doi()
    rows: List[AuthorRow] = []
    for doi in sorted(set(dois)):
        msg = raw_by_doi.get(doi, {}).get("message") or {}
        for idx, author in enumerate(msg.get("author") or []):
            rows.append(
                AuthorRow(
                    row_id=len(rows),
                    doi=doi,
                    author_index=idx,
                    given=author.get("given") or "",
                    family=author.get("family") or "",
                )
            )
    return rows, dois


def production_decisions(rows: List[AuthorRow]) -> List[Decision]:
    decisions: List[Decision] = []
    for row in rows:
        order, conf, reason = identify_surname_position_from_fields_v8(
            firstname=row.given,
            lastname=row.family,
            source="CROSSREF",
            publication_id=row.doi,
        )
        decisions.append(Decision(order or "unknown", conf, reason))
    return decisions


def batch_final_profile_decisions(rows: List[AuthorRow]) -> List[Decision]:
    records = [
        NameRecord(
            record_id=str(i),
            name_raw="",
            firstname_raw=row.given,
            lastname_raw=row.family,
            source="CROSSREF",
            publication_id=row.doi,
            field_only=True,
        )
        for i, row in enumerate(rows)
    ]
    batch = batch_identify_surname_position_v8(
        records,
        source="CROSSREF",
        enable_person_consistency=True,
        enable_pub_consistency=True,
    )
    return [
        Decision(
            batch[str(i)].order,
            batch[str(i)].confidence,
            ", ".join(batch[str(i)].reason_codes),
        )
        for i in range(len(rows))
    ]


def build_role_profile(rows: List[AuthorRow]) -> Tuple[Counter, Counter]:
    given_counts: Counter = Counter()
    family_counts: Counter = Counter()
    for row in rows:
        g = field_key(row.given)
        f = field_key(row.family)
        if g:
            given_counts[g] += 1
        if f:
            family_counts[f] += 1
    return given_counts, family_counts


def role_delta(row: AuthorRow, given_counts: Counter, family_counts: Counter) -> Tuple[float, List[str]]:
    """Positive delta supports given_first; negative supports family_first."""
    alpha = 3.0
    reasons: List[str] = []
    g = field_key(row.given)
    f = field_key(row.family)
    if not g or not f:
        return 0.0, ["ROLE_MISSING_KEY"]

    def log_family_odds(token: str) -> float:
        return math.log((family_counts[token] + alpha) / (given_counts[token] + alpha))

    # If the family field token historically behaves like a family name and
    # the given field token historically behaves like a given name, support
    # given_first. The reverse supports family_first.
    delta = log_family_odds(f) - log_family_odds(g)
    reasons.append(f"ROLE_DELTA({delta:.3f})")
    if family_counts[f] + given_counts[f] >= 5:
        reasons.append(f"ROLE_FAMILY_TOKEN_PROFILE({f})")
    if family_counts[g] + given_counts[g] >= 5:
        reasons.append(f"ROLE_GIVEN_TOKEN_PROFILE({g})")
    return delta, reasons


def role_decisions(rows: List[AuthorRow], threshold: float) -> List[Decision]:
    given_counts, family_counts = build_role_profile(rows)
    out: List[Decision] = []
    for row in rows:
        delta, reasons = role_delta(row, given_counts, family_counts)
        if abs(delta) < threshold:
            out.append(Decision("unknown", 0.5, "ROLE_ONLY: " + ", ".join(reasons + ["ROLE_DELTA_SMALL"])))
            continue
        order = "given_first" if delta > 0 else "family_first"
        conf = _field_confidence_from_delta(abs(delta))
        out.append(Decision(order, conf, "ROLE_ONLY: " + ", ".join(reasons)))
    return out


def merge_prod_role(
    prod: List[Decision],
    role: List[Decision],
    prefer_role_conflicts: bool,
) -> List[Decision]:
    out: List[Decision] = []
    for p, r in zip(prod, role):
        if p.order == "unknown" and r.order != "unknown":
            out.append(Decision(r.order, min(r.confidence, 0.82), p.reason + " | ROLE_FILL: " + r.reason))
        elif r.order == "unknown" or p.order == r.order:
            out.append(p)
        elif prefer_role_conflicts and r.confidence >= 0.84 and p.confidence < 0.90:
            out.append(Decision(r.order, min(r.confidence, 0.84), p.reason + " | ROLE_OVERRIDE: " + r.reason))
        elif p.confidence < 0.75 and r.confidence >= 0.80:
            out.append(Decision("unknown", 0.5, p.reason + " | ROLE_CONFLICT: " + r.reason))
        else:
            out.append(p)
    return out


def merge_prod_role_given_only(
    prod: List[Decision],
    role: List[Decision],
) -> List[Decision]:
    """
    Conservative schema-profile fill.

    The role profile can be useful for obvious Crossref-style given/family
    fields, but its family_first fills include risky cross-cultural cases. This
    variant uses role evidence only to fill unknown as given_first and never
    adds family_first decisions.
    """
    out: List[Decision] = []
    for p, r in zip(prod, role):
        if p.order == "unknown" and r.order == "given_first":
            out.append(
                Decision(
                    "given_first",
                    min(r.confidence, 0.80),
                    p.reason + " | ROLE_GIVEN_ONLY_FILL: " + r.reason,
                )
            )
        else:
            out.append(p)
    return out


def apply_doi_consistency(
    rows: List[AuthorRow],
    decisions: List[Decision],
    min_decided: int = 4,
    min_share: float = 0.92,
) -> List[Decision]:
    by_doi: Dict[str, List[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        by_doi[row.doi].append(i)

    out = list(decisions)
    for doi, indexes in by_doi.items():
        decided = [i for i in indexes if decisions[i].order != "unknown"]
        if len(decided) < min_decided:
            continue
        counts = Counter(decisions[i].order for i in decided)
        majority, majority_count = counts.most_common(1)[0]
        share = majority_count / len(decided)
        if share < min_share:
            continue
        for i in indexes:
            if out[i].order == "unknown":
                out[i] = Decision(
                    majority,
                    0.66,
                    decisions[i].reason + f" | DOI_CONSISTENCY_FILL({doi},{majority},{share:.3f})",
                )
    return out


def parse_split_flagged_expected() -> List[Tuple[str, str, str, str]]:
    """Small hand-audited challenge set from advisor SPLIT flagged entries."""
    return [
        ("10.1038/nature14656", "M. H. Eileen", "Tan", "given_first"),
        ("10.1063/1.2137890", "Lan", "Jin", "given_first"),
        ("10.1016/j.jmmm.2006.01.156", "Lan", "Jin", "given_first"),
        ("10.24272/j.issn.2095-8137.2021.228", "Jian-Huan", "Yang", "given_first"),
        ("10.1016/j.ppnp.2022.103948", "M.G.", "Di Luca", "given_first"),
        ("10.4289/0013-8797.124.2.287", "Li", "Yan", "family_first"),
        ("10.4289/0013-8797.124.2.287", "Li", "Nan", "family_first"),
        ("10.1515/pac-2024-0024", "Thi My Hanh Le", "Le", "given_first"),
        ("10.3847/1538-4365/ac4414", "Y. Sophia \u6631", "Dai \u6234", "given_first"),
        ("10.3847/1538-4365/ac4414", "Lihwai \u4fd0 \u6689", "Lin \u6797", "given_first"),
        ("10.1111/jvs.13235", "Michele", "Di\u00a0Musciano", "given_first"),
        ("10.1088/1674-1056/ad6b84", "Jin \u52b2", "Zhan \u6e5b", "given_first"),
        ("10.1088/1674-1056/ad6b84", "Yi \u4e00", "Wang \u738b", "given_first"),
        ("10.1088/1674-1056/ad6b84", "Yu \u90c1", "Sui \u968b", "given_first"),
        ("10.1088/1674-1056/ad6b84", "Bo \u6ce2", "Song \u5b8b", "given_first"),
        ("10.1016/j.jece.2025.117378", "Anqi", "Zhao", "given_first"),
        ("10.1109/ton.2025.3592491", "Xu", "Shu", "family_first"),
        ("10.1109/ton.2025.3592491", "Xiaoshan", "Zhang", "given_first"),
        ("10.1007/s12665-023-10937-9", "Wang", "Lei", "family_first"),
    ]


def split_section_dois() -> set:
    section_re = re.compile(r"^===SPLIT===(.+?)=======\s*$")
    return {
        m.group(1).strip().lower()
        for line in ISTINA_OUT_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        if (m := section_re.match(line))
    }


def summarize_variant(
    name: str,
    rows: List[AuthorRow],
    decisions: List[Decision],
    challenge: List[Tuple[str, str, str, str]],
    split_dois: set,
) -> Dict[str, Any]:
    orders = Counter(d.order for d in decisions)
    by_key = {(r.doi, r.given, r.family): decisions[i] for i, r in enumerate(rows)}
    challenge_total = len(challenge)
    challenge_correct = 0
    challenge_unknown = 0
    challenge_errors: List[Dict[str, str]] = []
    for doi, given, family, expected in challenge:
        d = by_key.get((doi, given, family))
        if not d:
            challenge_errors.append({"doi": doi, "given": given, "family": family, "error": "missing"})
            continue
        if d.order == "unknown":
            challenge_unknown += 1
        if d.order == expected:
            challenge_correct += 1
        else:
            challenge_errors.append(
                {
                    "doi": doi,
                    "given": given,
                    "family": family,
                    "expected": expected,
                    "actual": d.order,
                    "reason": d.reason,
                }
            )

    split_indexes = [i for i, r in enumerate(rows) if r.doi in split_dois]
    split_orders = Counter(decisions[i].order for i in split_indexes)
    changed_family_first = sum(1 for d in decisions if d.order == "family_first")
    return {
        "variant": name,
        "order_counts": dict(orders),
        "unknown_rate": round(orders.get("unknown", 0) / len(rows), 6),
        "decided_rate": round((len(rows) - orders.get("unknown", 0)) / len(rows), 6),
        "family_first_count": changed_family_first,
        "challenge_correct": challenge_correct,
        "challenge_total": challenge_total,
        "challenge_unknown": challenge_unknown,
        "challenge_errors": challenge_errors[:20],
        "split_order_counts": dict(split_orders),
        "split_unknown_rate": round(split_orders.get("unknown", 0) / len(split_indexes), 6) if split_indexes else 0,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, dois = load_rows()
    challenge = parse_split_flagged_expected()
    split_dois = split_section_dois()

    prod = production_decisions(rows)
    batch_final = batch_final_profile_decisions(rows)
    role_10 = role_decisions(rows, threshold=1.0)
    role_14 = role_decisions(rows, threshold=1.4)

    variants: Dict[str, List[Decision]] = {
        "final_batch_profile": batch_final,
        "current_production": prod,
        "role_profile_t1.0": role_10,
        "role_profile_t1.4": role_14,
        "prod_plus_role_fill_t1.0": merge_prod_role(prod, role_10, prefer_role_conflicts=False),
        "prod_plus_role_fill_t1.4": merge_prod_role(prod, role_14, prefer_role_conflicts=False),
        "prod_plus_role_given_only_t1.0": merge_prod_role_given_only(prod, role_10),
        "prod_plus_role_given_only_t1.4": merge_prod_role_given_only(prod, role_14),
        "prod_plus_role_aggressive_t1.0": merge_prod_role(prod, role_10, prefer_role_conflicts=True),
    }
    variants["prod_plus_doi_consistency"] = apply_doi_consistency(rows, prod)
    variants["prod_role_t1.0_plus_doi"] = apply_doi_consistency(rows, variants["prod_plus_role_fill_t1.0"])
    variants["prod_role_t1.4_plus_doi"] = apply_doi_consistency(rows, variants["prod_plus_role_fill_t1.4"])
    variants["prod_role_given_only_t1.0_plus_doi"] = apply_doi_consistency(
        rows,
        variants["prod_plus_role_given_only_t1.0"],
    )
    variants["prod_role_given_only_t1.4_plus_doi"] = apply_doi_consistency(
        rows,
        variants["prod_plus_role_given_only_t1.4"],
    )

    summaries = [
        summarize_variant(name, rows, decisions, challenge, split_dois)
        for name, decisions in variants.items()
    ]
    summaries.sort(key=lambda x: (-x["challenge_correct"], x["challenge_unknown"], x["unknown_rate"], x["family_first_count"]))

    (OUTPUT_DIR / "variant_summary.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (OUTPUT_DIR / "variant_summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "variant",
            "unknown_rate",
            "decided_rate",
            "family_first_count",
            "challenge_correct",
            "challenge_total",
            "challenge_unknown",
            "split_unknown_rate",
            "order_counts",
            "split_order_counts",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summaries:
            writer.writerow({key: row.get(key) for key in fieldnames})

    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    print("OUTPUT_DIR", OUTPUT_DIR.resolve())


if __name__ == "__main__":
    main()
