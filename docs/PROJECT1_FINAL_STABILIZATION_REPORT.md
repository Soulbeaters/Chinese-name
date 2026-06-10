# Project 1 Final Stabilization Report

Generated: 2026-06-10
Branch: `codex-share-ratio-finalize`
Base HEAD: `300d270 fix: make split-field validation effective in batch v8`

## What changed

- Raw-name DOI/person consistency is now folded into the existing
  `adjust_by_publication` and `adjust_by_person` consistency passes instead of
  being exposed as separate batch-level raw-name functions.
- The final split-field profile enables the existing publication candidate
  group correction with conservative thresholds:
  `min_count=2`, `min_share=0.50`, `min_strong_count=1`,
  `min_strength_sum=1.0`, `strong_threshold=1.0`.
- Publication consistency no longer fills `field_only` unknown records. This
  prevents DOI majority evidence from fabricating decisions for split-field
  inputs with insufficient evidence.
- `experiments/run_bench.py` now evaluates field-only split inputs against
  explicit `true_position` labels only. It does not infer labels from
  `original_name`.
- `experiments/evaluate_field_algorithm_variants.py` now reports
  `final_batch_profile`, which uses the production batch API and therefore
  includes publication/person consistency.

## Verification results

### Unit and static checks

- `python -m pytest tests -q`: 99 passed.
- `python -m py_compile src\surname_identifier_v8.py experiments\evaluate_field_algorithm_variants.py experiments\run_bench.py`: passed.
- `git diff --check`: passed. Git only warned that several files will be
  converted from LF to CRLF when touched on Windows.

### Mentor raw-name benchmark

Input: `C:\istina\materia 材料\测试表单\crossref_authors.json`

Command shape: same as the mentor's raw-name entry point:
`NameRecord(name_raw=original_name, person_id=orcid, publication_id=article_id, affiliation_raw=affiliation)`.

Results:

- Rows: 301,586.
- Mode counts: CHINESE 56,362; MIXED 126,568; WESTERN 75,520; ABBREVIATION 43,136.
- Order counts: given_first 300,892; family_first 694.
- Mentor metric (`mode == CHINESE and order != given_first`): 257 / 56,362.
- Simple proxy-labeled rows: 301,559.
- Proxy errors: 694 / 301,559 = 0.2301%.
- Raw publication majority overrides: 4,740, with 4,740 proxy-good and 0 proxy-bad.
- Raw person majority overrides: 527, with 527 proxy-good and 0 proxy-bad.

Interpretation: this is a reproducibility/sanity benchmark only. The simple
proxy label is derived from `original_name`, `firstname`, and `lastname`; it is
not manual ground truth and should not be used as a paper claim of true
accuracy.

### Advisor DOI challenge set

Script: `python experiments\evaluate_field_algorithm_variants.py`

Final profile result:

- Variant: `final_batch_profile`.
- Rows evaluated: 92,872.
- Order counts: unknown 633; given_first 92,228; family_first 11.
- Challenge result: 18 / 19 correct, 0 unknown.
- Remaining challenge error:
  `10.1109/ton.2025.3592491`, given=`Xu`, family=`Shu`,
  expected=`family_first`, actual=`given_first`.

### Real comparison artifact

Reproduced summary command:

`python experiments\summarize_real_comparison_artifacts.py --inputs v8_vs_istina_vs_split_names\check_chinese_names_v8_vs_istina_vs_split_names.txt v8_vs_istina_vs_split_names\check_chinese_names_processor_vs_v8.txt --output-json runs\real_comparison_summary_20260610.json --output-md runs\real_comparison_summary_20260610.md`

Key artifact counts:

- ISTINA current database state: 867 article-level errors, 1,637 author-level errors.
- `split_names`: 359 article-level errors, 1,011 author-level errors in the current artifact summary.
- v8 structural anomaly: 1 author-level anomaly per comparison file, both pointing to DOI `10.3788/CJL221356`.

Interpretation: the paper's "one record" claim is supported by the per-file
v8 structural anomaly count. The combined `overall` block counts the same DOI
twice because it merges two comparison files.

## Worktree organization

Tracked modified groups:

- Core algorithm/config/tests:
  `src/surname_identifier_v8.py`, `src/config_v8.py`,
  `tests/test_surname_identifier_v8.py`, `tests/test_with_json_data.py`.
- Evaluation tooling:
  `experiments/run_bench.py`, `experiments/evaluate_field_algorithm_variants.py`.
- Existing project drift to review before commit:
  `.gitignore`, `data/pinyin_syllables.py`, `src/name_order_detector.py`,
  `src/surname_identifier.py`, and several docs.

Untracked groups:

- `experiments/`: helper scripts for calibration, comparison, benchmarking, and report generation.
- `docs/`: final paper/path and ISTINA pilot documentation.
- `paper/`, `figs/`, `tables/`: manuscript and figure/table assets.
- `v8_vs_istina_vs_split_names/`: real comparison text artifacts.
- `runs/`: ignored generated outputs; should remain untracked.

Recommended local commit grouping:

1. Core final profile and tests.
2. Evaluation scripts and explicit-label benchmark protocol.
3. Documentation/report updates.
4. Paper/artifact package, only after deciding which untracked assets belong in the repository.

## Context-stall diagnosis

The previous Codex thread likely stalled because the conversation combined a
large dirty worktree, long recursive searches, long command outputs, Windows
encoding issues for Chinese paths, and context compaction. The 301k dataset is
large enough to make individual benchmark commands slow, but it is not the
primary reason for the client stall.

Mitigation used in this pass:

- Keep `runs/` ignored and avoid printing generated artifacts into chat.
- Use Python path discovery for Chinese paths under `C:\istina`.
- Record final metrics in this repo report so future compressed contexts can
  recover from the file instead of conversation memory.
