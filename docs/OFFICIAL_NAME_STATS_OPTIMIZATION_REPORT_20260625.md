# Official name-statistics optimization report (2026-06-25)

## Outcome

The final candidate adds a fourth independent role model based on official
national name statistics:

1. U.S. Census 2020 first-name and last-name tables;
2. France INSEE first-name and surname files;
3. Poland PESEL first-name and surname files;
4. Statistics Sweden / SCB first-name and surname statistics by country of
   birth.

The model is applied after the existing Crossref, JMnedict, and SSA/Census
role fallbacks. It only handles Crossref records, and only overrides weak
defaults or Western morphology-only decisions. It does not override exact
split-field structure, abbreviations, or strong non-Chinese surname evidence.

The frozen threshold is `abs(log_odds_delta) >= 2.0` with both edge tokens
having model support `>= 3`. This was selected on pair-hash bucket 3 and then
validated on held-out bucket 4, the advisor DOI dataset, the full local
non-Chinese-inclusive set, and the frozen Wikidata external set.

## Final evaluation results

Reported score is `errors + unknown` across both generated display orders with
person and publication consistency. Lower is better.

| Dataset | Previous best combined | New combined | Change |
|---|---:|---:|---:|
| Local pinyin-compatible full set, 97,810 records | 3,488 | 3,428 | -60 (-1.72%) |
| Pair-disjoint holdout bucket 4, 20,046 records | 4,153 | 4,133 | -20 (-0.48%) |
| Advisor DOI dataset, 11,822 records | 1,252 | 1,245 | -7 (-0.56%) |
| Full local `--candidate-filter all`, 301,559 records | 36,174 | 29,503 | -6,671 (-18.44%) |
| Frozen Wikidata unseen external set, 1,660 records | 387 | 290 | -97 (-25.06%) |

Detailed final scores:

| Dataset | Errors | Unknown | Combined |
|---|---:|---:|---:|
| Local pinyin-compatible full set | 1,012 | 2,416 | 3,428 |
| Pair-disjoint holdout bucket 4 | 211 | 3,922 | 4,133 |
| Advisor DOI dataset | 276 | 969 | 1,245 |
| Full local `--candidate-filter all` | 28,869 | 634 | 29,503 |
| Frozen Wikidata unseen external set | 290 | 0 | 290 |

For context, the mentor baseline on the pinyin-compatible local set was 10,844
combined; the new final score is 3,428 (`-68.39%`). On the full local
non-Chinese-inclusive test, the no-role-model baseline was 123,625 combined;
the new final score is 29,503 (`-76.14%`).

## Candidate selection notes

The US/France/Poland official-statistics model already improved every key set:

| Dataset | Previous best | US+FR+PL model |
|---|---:|---:|
| Local pinyin-compatible full set | 3,488 | 3,436 |
| Pair-disjoint holdout bucket 4 | 4,153 | 4,135 |
| Advisor DOI dataset | 1,252 | 1,247 |
| Full local `--candidate-filter all` | 36,174 | 31,570 |
| Frozen Wikidata unseen external set | 387 | 293 |

Adding the Sweden/SCB data improved the official-statistics model further on
all confirmation sets, so the Sweden-enhanced model is the final committed
version.

## Data provenance

| Artifact | SHA-256 |
|---|---|
| Local Crossref input | `3546bcf7fa3566ab5ddc7105829c28df890e34544700034c70efbe2af7639806` |
| Advisor DOI input | `cf06727bf5c7241cb4729904db503c9224ad45145d780193d796e55d89eacf02` |
| Frozen Wikidata external sample | `d7536b3ba2d5e212c38181813a55e7fbc64896ad047cabae6af19b808231a7c0` |
| Official national-statistics derived model | `f203d44234eea568802b6868aeb500640169d529950c77155fcb0887f18579ca` |

Source details and raw-file hashes are in
[`OFFICIAL_NAME_STATISTICS_SOURCES_20260625.md`](OFFICIAL_NAME_STATISTICS_SOURCES_20260625.md)
and [`../data/OFFICIAL_NAME_STATS_ATTRIBUTION.md`](../data/OFFICIAL_NAME_STATS_ATTRIBUTION.md).

## Reproduction

```powershell
$env:PYTHONPATH='.'
python -m pytest -q

python experiments/evaluate_mentor_large_scale.py `
  --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --output results/official_stats_se_final_full_pinyin_97810.json `
  --surname-frequency-strategy freq_disabled

python experiments/evaluate_mentor_large_scale.py `
  --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --output results/official_stats_se_final_all_301559.json `
  --surname-frequency-strategy freq_disabled `
  --candidate-filter all
```
