# Production-quality and disambiguation implementation report (2026-06-25)

## Quality target

For a real bibliographic system, the recommended operating mode is conservative:

- automatic hard-error rate should be below 0.5-1.0%;
- uncertain cases should be routed to `unknown` / manual review instead of being
  forced into an order;
- author disambiguation should target pairwise precision >= 99%, pairwise recall
  >= 95%, and B³/cluster F1 >= 95% before it is treated as production-grade.

This matches the practical behavior of high-quality scholarly identity systems:
they prefer avoiding false merges and false order inversions over maximizing
automatic coverage.

## Current name-order quality

All numbers are from real re-runs of the current branch. The score is across
both generated display orders.

| Dataset / policy | Hard errors | UNKNOWN | Hard-error rate | UNKNOWN rate |
|---|---:|---:|---:|---:|
| pinyin-compatible, default | 1,012 | 2,416 | 0.517% | 1.235% |
| pinyin-compatible, conservative review gate | 942 | 4,447 | 0.482% | 2.273% |
| full `--candidate-filter all`, default | 28,869 | 634 | 4.787% | 0.105% |
| full `--candidate-filter all`, conservative review gate | 6,534 | 115,090 | 1.083% | 19.083% |
| advisor DOI, default | 276 | 969 | 1.167% | 4.098% |
| advisor DOI, conservative review gate | 266 | 1,106 | 1.125% | 4.678% |
| holdout bucket 4, default | 211 | 3,922 | 0.526% | 9.783% |
| holdout bucket 4, conservative review gate | 199 | 4,185 | 0.496% | 10.438% |

The conservative review gate routes these high-risk reason codes to UNKNOWN:

- `NO_CN_EVIDENCE_DEFAULT_GIVEN`
- `KNOWN_NON_CHINESE_SURNAME_FIRST`
- `WEST_SURNAME_LAST`

Conclusion: the pinyin-compatible and holdout settings satisfy the conservative
hard-error target after review gating. The full multilingual setting is improved
but still not production-grade because it requires about 19% manual review to
reach about 1.08% hard error.

## Error strata

The full multilingual errors are concentrated in a small number of decision
families:

| Reason code | Empirical error rate in full set | Error count |
|---|---:|---:|
| `NO_CN_EVIDENCE_DEFAULT_GIVEN` | 50.0% | 6,938 |
| `KNOWN_NON_CHINESE_SURNAME_FIRST` | 24.9% | 3,775 |
| `WEST_SURNAME_LAST` | 14.8% | 13,061 |
| `WEST_SURNAME_FIRST` | 5.4% | 3,365 |

This confirms that adding more dictionaries alone is not enough. The remaining
problem is mainly context-sensitive Western/non-Chinese ordering, not simple
surname lookup.

## Non-GNN author-disambiguation baseline

Implemented a conservative ORCID-labeled baseline using only non-leaking
features:

- normalized split names;
- affiliation token Jaccard;
- coauthor overlap derived from DOI groups;
- publication year gap.

ORCID is used only as the evaluation label, not as a feature.

| Dataset | Labeled mentions | Pairwise precision | Pairwise recall | Pairwise F1 | B³ precision | B³ recall | B³ F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| local Crossref ORCID rows | 150,795 | 99.66% | 47.13% | 64.00% | 99.67% | 73.43% | 84.56% |
| advisor DOI ORCID rows | 19,181 | 99.14% | 41.84% | 58.85% | 99.80% | 82.66% | 90.43% |

Conclusion: the non-GNN baseline already reaches production-like precision, but
recall is too low. The next engineering target should be recall improvement
without losing precision, before investing in a GNN.

## GNN decision

Do not start with a GNN as the next implementation step. The graph route is
justified only after a stronger non-GNN baseline cannot meet recall targets.

If needed, the graph task should be defined as author-mention link prediction:

- nodes: AuthorMention, Paper, Name, Institution/AffiliationString, Venue,
  Topic, Coauthor, external AuthorID;
- edges: authored-by, coauthor, same normalized name block, same affiliation,
  same venue/topic, citation/reference, external ID match;
- models to compare: node2vec/metapath2vec + classifier, GraphSAGE, GAT, HGT;
- evaluation split: by ORCID/OpenAlex author ID and time, with no person leakage.

The GNN must beat the non-GNN baseline on recall while preserving pairwise
precision >= 99%.

## Reproduction

```powershell
python experiments/analyze_name_order_quality.py `
  --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --output results/quality_diagnostics_all_20260625.json `
  --candidate-filter all `
  --confidence-thresholds 0 0.72 0.8 0.9

python experiments/evaluate_mentor_large_scale.py `
  --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --output results/quality_gate_all_conservative_review.json `
  --surname-frequency-strategy freq_disabled `
  --candidate-filter all `
  --review-reason-codes NO_CN_EVIDENCE_DEFAULT_GIVEN KNOWN_NON_CHINESE_SURNAME_FIRST WEST_SURNAME_LAST

python experiments/evaluate_author_disambiguation_baseline.py `
  --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --output results/author_disambiguation_baseline_crossref_orcid.json
```
