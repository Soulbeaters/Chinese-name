#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize real-comparison artifact text files into reusable JSON/Markdown stats.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SECTION_RE = re.compile(r"^===(?P<label>[^=]+)===(?P<doi>.+?)=======$")
ANOMALY_RE = re.compile(r"^======(?P<doi>.+?)=======$")


def try_literal_eval(text: str) -> Optional[Any]:
    try:
        return ast.literal_eval(text)
    except Exception:
        return None


def normalize_label(label: str) -> str:
    mapping = {
        "SPLIT": "split_names",
        "ISTINA": "istina",
        "OLD": "old_processor",
        "V8_ANOMALY": "v8_structural_anomaly",
    }
    return mapping.get(label, label.lower())


def parse_names_line(text: str) -> Optional[List[str]]:
    parsed = try_literal_eval(text)
    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        return parsed
    return None


def count_detail_items(text: str) -> int:
    parsed = try_literal_eval(text)
    if isinstance(parsed, list):
        return len(parsed)
    if "NameDecision(" in text:
        return text.count("NameDecision(")
    return 1 if text else 0


def truncate_text(text: Optional[str], limit: int = 240) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 3] + "..."


def parse_sections(path: Path) -> List[Dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: List[Dict[str, Any]] = []
    idx = 0

    while idx < len(lines):
        current = lines[idx].strip()
        header_match = SECTION_RE.match(current)
        anomaly_match = ANOMALY_RE.match(current)
        if not header_match and not anomaly_match:
            idx += 1
            continue

        if header_match:
            raw_label = header_match.group("label")
            doi = header_match.group("doi")
        else:
            raw_label = "V8_ANOMALY"
            doi = anomaly_match.group("doi")

        idx += 1
        payloads: List[str] = []
        while idx < len(lines):
            probe = lines[idx].strip()
            if not probe:
                idx += 1
                continue
            if SECTION_RE.match(probe) or ANOMALY_RE.match(probe):
                break
            payloads.append(probe)
            idx += 1

        names: Optional[List[str]] = None
        detail_text: Optional[str] = None
        if payloads:
            maybe_names = parse_names_line(payloads[0])
            if maybe_names is not None:
                names = maybe_names
                if len(payloads) > 1:
                    detail_text = payloads[1]
            else:
                detail_text = payloads[0]

        sections.append(
            {
                "raw_label": raw_label,
                "label": normalize_label(raw_label),
                "doi": doi,
                "names": names or [],
                "detail_text": detail_text or "",
                "author_errors": count_detail_items(detail_text or ""),
            }
        )

    return sections


def summarize_sections(sections: List[Dict[str, Any]], sample_limit: int) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for section in sections:
        bucket = summary.setdefault(
            section["label"],
            {
                "raw_labels": set(),
                "article_errors": 0,
                "author_errors": 0,
                "samples": [],
            },
        )
        bucket["raw_labels"].add(section["raw_label"])
        bucket["article_errors"] += 1
        bucket["author_errors"] += section["author_errors"]
        if len(bucket["samples"]) < sample_limit:
            bucket["samples"].append(
                {
                    "doi": section["doi"],
                    "author_errors": section["author_errors"],
                    "names_preview": section["names"][:6],
                    "detail_preview": truncate_text(section["detail_text"]),
                }
            )

    for bucket in summary.values():
        bucket["raw_labels"] = sorted(bucket["raw_labels"])

    return summary


def render_markdown(overall: Dict[str, Any], artifact_summaries: List[Dict[str, Any]]) -> str:
    lines = [
        "# Real Comparison Artifact Summary",
        "",
        "## Overall",
        "",
        "| Label | Article errors | Author errors | Raw labels |",
        "| --- | ---: | ---: | --- |",
    ]
    for label, bucket in sorted(overall.items()):
        lines.append(
            f"| {label} | {bucket['article_errors']} | {bucket['author_errors']} | {', '.join(bucket['raw_labels'])} |"
        )

    for artifact in artifact_summaries:
        lines.extend(
            [
                "",
                f"## {artifact['file']}",
                "",
                "| Label | Article errors | Author errors |",
                "| --- | ---: | ---: |",
            ]
        )
        for label, bucket in sorted(artifact["summary"].items()):
            lines.append(f"| {label} | {bucket['article_errors']} | {bucket['author_errors']} |")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize real-comparison artifact text files.")
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="Artifact text files to summarize.",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional JSON output path.",
    )
    parser.add_argument(
        "--output-md",
        type=str,
        default=None,
        help="Optional Markdown output path.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5,
        help="Representative samples per label.",
    )
    args = parser.parse_args()

    artifact_summaries: List[Dict[str, Any]] = []
    overall_sections: List[Dict[str, Any]] = []

    for input_path in args.inputs:
        path = Path(input_path)
        sections = parse_sections(path)
        overall_sections.extend(sections)
        artifact_summaries.append(
            {
                "file": str(path),
                "section_count": len(sections),
                "summary": summarize_sections(sections, args.sample_limit),
            }
        )

    overall = summarize_sections(overall_sections, args.sample_limit)
    payload = {
        "artifacts": artifact_summaries,
        "overall": overall,
    }

    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.output_md:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown(overall, artifact_summaries), encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
