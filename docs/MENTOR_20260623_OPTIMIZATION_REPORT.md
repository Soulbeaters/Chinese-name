# Mentor 2026-06-23 Branch Optimization Report

Generated: 2026-06-24

Branch: `codex/mentor-20260623-optimize`

Base: `origin/zenderro/20260623-fix` (`3ebaf5a`)

## Evaluation policy

The original `experiments/run_bench.py` passes `firstname` and `lastname` to
the model while also deriving its proxy label from those fields. On the 301,586
record corpus this produces 301,146 / 301,146 correct decisions because the
exact split-field feature reveals the label. This result is data leakage and is
not used as an optimization target.

`experiments/evaluate_mentor_large_scale.py` implements the paper's two-order
stress test without leakage. It constructs `given family` and `family given`
strings but does not expose the split fields to the algorithm. The split fields
are used only to construct the two known test orientations.

## Data

### Full Crossref corpus

- Input records: 301,586.
- Pinyin-compatible complete split records under the mentor branch resources:
  97,810.
- Unique name pairs: 29,269.
- SHA-256:
  `3546bcf7fa3566ab5ddc7105829c28df890e34544700034c70efbe2af7639806`.
- Note: the paper reports 97,582 candidates. The 228-record difference is
  consistent with the expanded pinyin list in the 2026-06-23 commit.

### Advisor DOI corpus

- Input records: 92,872.
- Pinyin-compatible complete split records: 11,822.
- Unique name pairs: 7,073.
- SHA-256:
  `cf06727bf5c7241cb4729904db503c9224ad45145d780193d796e55d89eacf02`.

## Changes retained

1. Make `freq_disabled` the conservative default for non-ISTINA dual-surname
   cases. Ambiguous pairs abstain instead of guessing from frequency.
2. Keep a separate ISTINA dual-surname default because that source profile has
   a family-first prior.
3. Integrate the existing non-Chinese surname resource into mode and order
   evidence.
4. Add the audited Japanese/European entries `Owada`, `Ouchi`, `Obayashi`,
   `Kawase`, `Murayama`, and `Molina`.
5. Mark cross-cultural collision tokens such as `Bowen`, `Le`, and `Dao` as
   audit-only evidence, not hard order evidence.
6. Add an optional `publication_same_mode_only` profile. It lowers automatic
   correction risk but is not the default because it materially increases
   abstentions.
7. Fix the dead tuple-`or` pinyin expression and legacy `Ming Zhang` handling.
8. Repair the pytest harness so JSON-backed checks run as actual assertions.

## Full Crossref result

Configuration: `freq_disabled`, person and publication consistency enabled,
default cross-mode publication majority.

| Orientation | Metric | Mentor baseline | Optimized | Change |
|---|---:|---:|---:|---:|
| given-first | errors | 386 | 374 | -12 |
| given-first | UNKNOWN | 3,152 | 3,132 | -20 |
| family-first | errors | 4,082 | 3,297 | -785 |
| family-first | UNKNOWN | 3,224 | 3,168 | -56 |
| combined | errors | 4,468 | 3,671 | -797 (-17.8%) |
| combined | UNKNOWN | 6,376 | 6,300 | -76 (-1.2%) |
| combined | error + UNKNOWN | 10,844 | 9,971 | -873 (-8.1%) |

The improvement is asymmetric because the mentor's reported weakness is most
visible when a non-Chinese surname is presented in family-first order.

## Advisor DOI result

| Orientation | Metric | Mentor baseline | Optimized | Change |
|---|---:|---:|---:|---:|
| given-first | errors | 98 | 97 | -1 |
| given-first | UNKNOWN | 877 | 875 | -2 |
| family-first | errors | 646 | 608 | -38 |
| family-first | UNKNOWN | 874 | 872 | -2 |

## Acceptance checks

- `python -m pytest -q tests`: 79 passed.
- Static compilation: passed.
- `git diff --check`: passed (line-ending warnings only).
- Hand-audited 19-row challenge: 15 / 19. The remaining four cases are split
  fields known to be swapped, but the mentor branch's exact split-field override
  trusts the aligned `original_name`. This limitation predates the optimization
  and is intentionally reported rather than hidden.

## Remaining work

- Replace the exact split-field override with a field-only review/correction
  path and revalidate the four challenge failures on a larger manually labeled
  swapped-field set.
- Audit the 13 non-Chinese-dictionary records still classified in CHINESE mode.
- Reconcile the paper's 97,582 candidate count with the current 97,810 count.
- Update paper tables only after the final branch and dataset hashes are frozen.
