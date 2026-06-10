# Special Crossref Split-Field Cases Audit

Generated: 2026-06-10

## Purpose

This note records the advisor-provided Crossref `(family, given)` special
cases and separates three different concepts:

1. Manual label: the human judgment supplied during advisor discussion.
2. Production label: the final v8 field-only batch API output.
3. Production-safe review label: the opt-in v8 split-field review profile.
4. Audit signal: diagnostic evidence extracted from existing reason codes and
   existing pinyin/surname resources.

The production profile still does not flip these records by default. The review
profile is an explicit audit-mode layer for pre-screened lists.

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
- Captures 63 / 64 manually reliable swapped cases.
- Also marks 5 cases that manual review excludes or keeps separate:
  `Owada Mao`, `Molina Chai`, `Ouchi Mai`, `Kawase Jin`, `Melin Bo`.
- Misses 1 manually reliable swapped case:
  `Yongzhong Ouyang`.

Opt-in review profile:

- `likely_swapped`: 64 / 64 manually reliable swapped cases.
- `not_swapped_or_excluded`: 11 / 11 excluded or check-separately cases.
- No excluded/check case is promoted to `likely_swapped`.

Interpretation: the final production profile sees the main reversal evidence
in most cases but does not flip them, because Crossref split fields are
protected by the conservative external split prior. This behavior is consistent
with the final project objective of avoiding broad false-positive corrections.
The opt-in review profile can be used after the list has already been
pre-screened as suspicious.

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

Opt-in review profile:

- `likely_swapped`: 10 / 10 manually reliable swapped cases.
- Also promotes one possible/check case to `likely_swapped`: `Shui Yuan`.
- Remaining possible/check cases stay `possible_swapped`.

Interpretation: the one-syllable list is intrinsically ambiguous. The existing
features can flag many records for review, but they cannot perfectly separate
reliable swapped cases from possible/check cases. The opt-in review profile
improves recall for the manually reliable cases, but `Shui Yuan` remains a
reasonable manual-check boundary case.

## Recommended wording

Use this wording when reporting the result:

> The final production profile is intentionally conservative for Crossref split
> fields and does not automatically flip these advisor-provided records without
> additional context. For manually pre-screened suspicious lists, I added an
> explicit review profile. In the two-syllable list it matches the manual
> split exactly: 64 likely swapped Chinese cases and 11 excluded/check cases.
> In the one-syllable list it captures all 10 manually reliable swapped cases,
> but also marks `Shui Yuan` as likely, so that list should still be treated as
> an audit queue rather than a fully automatic correction rule.

## Boundary

Do not merge this review profile into the default v8 production profile unless
a larger labeled validation set proves that the false-positive cost is
acceptable.
The current final profile was chosen to preserve:

- advisor DOI challenge: 18 / 19;
- mentor raw-name benchmark: `CHINESE non-given = 253`;
- zero proxy-bad raw-name consistency overrides in the strict frozen audit;
- real comparison artifact: one v8 structural anomaly per comparison file.
