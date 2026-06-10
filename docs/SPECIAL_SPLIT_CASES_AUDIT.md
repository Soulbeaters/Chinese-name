# Special Crossref Split-Field Cases Audit

Generated: 2026-06-10

## Purpose

This note records the advisor-provided Crossref `(family, given)` special
cases and separates three different concepts:

1. Manual label: the human judgment supplied during advisor discussion.
2. Production label: the final v8 field-only batch API output.
3. Audit signal: diagnostic evidence extracted from existing reason codes and
   existing pinyin/surname resources.

The audit signal is not a production decision and must not be described as the
final algorithm flipping a record. It is a review aid for pre-screened lists.

## Reproduction

```powershell
python experiments\evaluate_special_split_cases.py --output-dir runs\special_crossref_split_cases_20260610
```

Outputs:

- `runs/special_crossref_split_cases_20260610/special_split_cases.json`
- `runs/special_crossref_split_cases_20260610/special_split_cases.md`

The output directory is under `runs/` and remains ignored by git.

## Results

### Two-syllable family-field list

Manual labels:

- 64 reliable swapped Chinese cases.
- 11 excluded or check-separately cases.

Production final profile:

- `not_swapped`: 75.
- `swapped`: 0.
- `unknown`: 0.

Diagnostic audit signal:

- Signal: `FIELD_GIVEN_CN_SURNAME_FAMILY_CN_GIVEN`.
- Captures 62 / 64 manually reliable swapped cases.
- Also marks 5 cases that manual review excludes or keeps separate:
  `Owada Mao`, `Molina Chai`, `Ouchi Mai`, `Kawase Jin`, `Melin Bo`.
- Misses 2 manually reliable swapped cases:
  `Sitong Chen`, `Yongzhong Ouyang`.

Interpretation: the final production profile sees the main reversal evidence
in most cases but does not flip them, because Crossref split fields are
protected by the conservative external split prior. This behavior is consistent
with the final project objective of avoiding broad false-positive corrections.

### First-token-not-surname list

Manual labels:

- 10 reliable swapped cases.
- 10 possible/check cases.
- 1 not-reliable case.

Production final profile:

- `not_swapped`: 20.
- `unknown`: 1.
- `swapped`: 0.

Diagnostic audit signal:

- Signal: `FIELD_GIVEN_SURNAME_WEAK` or `FIELD_DUAL_CN_SURNAME_FREQ_GIVEN`.
- Captures 9 / 10 manually reliable swapped cases.
- Also marks 8 possible/check cases and `La Ming`.
- Misses `Kun Sun`.

Interpretation: the one-syllable list is intrinsically ambiguous. The existing
features can flag many records for review, but they cannot separate reliable
swapped cases from possible/check cases with enough precision to be used as a
production flip rule without additional evidence such as ORCID, affiliation,
journal page, full name, or Han characters.

## Recommended wording

Use this wording when reporting the result:

> The final production profile is intentionally conservative for Crossref split
> fields and does not automatically flip these advisor-provided records without
> additional context. However, the diagnostic reason codes identify most
> suspicious Chinese swapped-field candidates. In the two-syllable list, the
> strongest existing signal captures 62 of the 64 manually reliable cases, but
> also includes several Japanese or non-Chinese cases that should remain manual
> checks. In the one-syllable list, the evidence is too ambiguous for automatic
> correction and should be treated as a review list rather than a confident
> error list.

## Boundary

Do not merge this audit signal into the default v8 production profile unless a
larger labeled validation set proves that the false-positive cost is acceptable.
The current final profile was chosen to preserve:

- advisor DOI challenge: 18 / 19;
- mentor raw-name benchmark: `CHINESE non-given = 257`;
- zero proxy-bad raw-name consistency overrides in the strict frozen audit;
- real comparison artifact: one v8 structural anomaly per comparison file.
