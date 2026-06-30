#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a public DBLP author-mention dataset for Article 2 validation.

DBLP author pids are used as evaluation labels when available.  If a pid is
missing, the DBLP author string is used as a fallback label.  DBLP
disambiguation suffixes such as ``0001`` are removed from the name features so
the label is not leaked into the algorithm.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import urllib.request
from pathlib import Path
from typing import BinaryIO, Iterable

from lxml import etree


DEFAULT_DBLP_XML_GZ_URL = "https://dblp.org/xml/dblp.xml.gz"
PUBLICATION_TAGS = {
    "article",
    "inproceedings",
    "incollection",
    "proceedings",
    "book",
}
AUTHOR_SUFFIX_RE = re.compile(r"\s+\d{4}$")
DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.I)


def open_binary_source(source: str) -> BinaryIO:
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(
            source,
            headers={"User-Agent": "article2-author-disambiguation-research/1.0"},
        )
        return urllib.request.urlopen(request, timeout=120)  # type: ignore[return-value]
    return Path(source).open("rb")


def clean_author_name(author: str) -> str:
    return AUTHOR_SUFFIX_RE.sub("", author).strip()


def split_name(author: str) -> tuple[str, str]:
    parts = clean_author_name(author).split()
    if len(parts) < 2:
        return "", ""
    return " ".join(parts[:-1]), parts[-1]


def extract_doi(values: Iterable[str]) -> str:
    for value in values:
        match = DOI_RE.search(value)
        if match:
            return match.group(0).rstrip(".,;").lower()
    return ""


def label_author(author: str, pid: str) -> str:
    if pid:
        return f"dblp-pid:{pid.lower()}"
    return f"dblp-name:{author.lower()}"


def iter_publication_records(
    source: str,
    min_year: int,
    max_year: int,
    min_authors: int,
    max_mentions: int,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with open_binary_source(source) as raw:
        with gzip.GzipFile(fileobj=raw) as handle:
            for _, element in etree.iterparse(
                handle,
                events=("end",),
                load_dtd=True,
                resolve_entities=True,
                no_network=False,
            ):
                if element.tag not in PUBLICATION_TAGS:
                    continue
                key = str(element.attrib.get("key", ""))
                year_text = element.findtext("year")
                try:
                    year = int(year_text or "")
                except ValueError:
                    element.clear()
                    continue
                if not (min_year <= year <= max_year):
                    element.clear()
                    continue

                authors = [
                    (
                        (child.text or "").strip(),
                        str(child.attrib.get("pid", "")).strip(),
                    )
                    for child in element.findall("author")
                    if (child.text or "").strip()
                ]
                if len(authors) < min_authors:
                    element.clear()
                    continue

                doi = extract_doi(
                    child.text or ""
                    for child in element
                    if child.tag in {"ee", "url"}
                )
                for position, (author, pid) in enumerate(authors):
                    firstname, lastname = split_name(author)
                    if not firstname or not lastname:
                        continue
                    records.append(
                        {
                            "id": f"dblp:{key}:{position}",
                            "firstname": firstname,
                            "lastname": lastname,
                            "original_name": clean_author_name(author),
                            "doi": doi,
                            "article_id": f"dblp:{key}",
                            "year": year,
                            "affiliation": "",
                            "orcid": label_author(author, pid),
                            "source": "dblp",
                        }
                    )
                    if len(records) >= max_mentions:
                        return records
                element.clear()
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_DBLP_XML_GZ_URL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-year", type=int, default=2018)
    parser.add_argument("--max-year", type=int, default=2025)
    parser.add_argument("--min-authors", type=int, default=2)
    parser.add_argument("--max-mentions", type=int, default=60000)
    args = parser.parse_args()

    records = iter_publication_records(
        args.source,
        args.min_year,
        args.max_year,
        args.min_authors,
        args.max_mentions,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    unique_authors = len({record["orcid"] for record in records})
    unique_papers = len({record["article_id"] for record in records})
    print(
        json.dumps(
            {
                "output": str(args.output),
                "records": len(records),
                "unique_authors": unique_authors,
                "unique_papers": unique_papers,
                "min_year": args.min_year,
                "max_year": args.max_year,
                "source": args.source,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
