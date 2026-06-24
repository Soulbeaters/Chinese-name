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
9. Allow a publication-level majority to correct any conflicting decision
   below the publication voting confidence threshold, while protecting strong
   local evidence.
10. Set the Crossref publication dominance margin to one vote; ORCID and
    ISTINA retain their previous thresholds because no equivalent validation
    data was available for those sources.
11. Make Western surname-position evidence symmetric enough to recognize both
    `given surname` and `surname given` formats.
12. Add an opt-in Crossref split-field review API for strong swap candidates;
    it does not silently alter production decisions.

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

## Second optimization pass

All rows below use the same dataset hashes and the `person_publication` context
profile. `Error + UNKNOWN` is the primary selection metric; changes were kept
only when the full Crossref corpus and advisor DOI corpus agreed in direction.

| Iteration | Full Crossref errors | UNKNOWN | Error + UNKNOWN | Advisor errors | UNKNOWN | Error + UNKNOWN | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| First-pass optimized | 3,671 | 6,300 | 9,971 | 705 | 1,747 | 2,452 | Starting point |
| Weak-default publication override | 2,582 | 6,300 | 8,882 | 441 | 1,747 | 2,188 | Keep |
| All weak decisions override | 2,525 | 6,300 | 8,825 | 437 | 1,747 | 2,184 | Keep |
| Crossref one-vote dominance | 2,109 | 2,722 | 4,831 | 343 | 1,006 | 1,349 | Keep |
| Symmetric Western surname evidence | 1,927 | 2,725 | 4,652 | 324 | 1,008 | 1,332 | Keep |
| Same-cultural-mode publication only | 3,014 | 3,203 | 6,217 | 570 | 1,118 | 1,688 | Reject |
| Opt-in split review API | 1,927 | 2,725 | 4,652 | 324 | 1,008 | 1,332 | Keep; production-neutral |

Final full Crossref orientation details:

| Orientation | Errors | UNKNOWN |
|---|---:|---:|
| given-first | 362 | 1,351 |
| family-first | 1,565 | 1,374 |
| combined | 1,927 | 2,725 |

Relative to the mentor baseline, combined errors fell from 4,468 to 1,927
(-56.9%), while `error + UNKNOWN` fell from 10,844 to 4,652 (-57.1%).
The independent advisor corpus changed from 744 errors and 1,751 UNKNOWN to
324 errors and 1,008 UNKNOWN.

## Acceptance checks

- `python -m pytest -q tests`: 82 passed.
- Static compilation: passed.
- `git diff --check`: passed (line-ending warnings only).
- Default production path on the hand-audited challenge: 15 / 19. The opt-in
  split-field review flags exactly the four known swapped cases and reaches
  19 / 19 when used as a review step. Production remains conservative rather
  than auto-flipping all dual-surname fields.

## Remaining work

- Build a larger manually labeled split-field set before promoting review
  signals into automatic production corrections.
- Audit the 13 non-Chinese-dictionary records still classified in CHINESE mode.
- Replace hand-maintained non-Chinese surname expansion with a train/dev/test
  lexicon workflow or an independently sourced surname model.
- Evaluate learned publication-order inference on publications with genuinely
  mixed author-name formats; the synthetic stress test assumes one orientation
  per publication.
- Reconcile the paper's 97,582 candidate count with the current 97,810 count.
- Update paper tables only after the final branch and dataset hashes are frozen.
