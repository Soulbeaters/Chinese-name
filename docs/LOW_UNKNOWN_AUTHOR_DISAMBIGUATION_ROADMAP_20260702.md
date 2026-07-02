# Low-UNKNOWN author-disambiguation roadmap

Date: 2026-07-02

## Problem

The current Article 2 framework has a deliberately conservative `LINK / NEW / UNKNOWN` design. It is safe on high-risk public datasets, but the strict profile produces too many `UNKNOWN` decisions:

- LAGOS-AND strict online: link precision `100.000%`, new-author false-link `0.055%`, but link recall only `1.562%`.
- S2AND strict online: link precision `100.000%`, new-author false-link `0.000%`, but link recall only `0.971%`.

This is not a bug in the implementation. It is the expected behavior of a thresholded rule system: when metadata is sparse or names are ambiguous, the rules abstain to avoid false links. If the target is both low error and low UNKNOWN/manual-review rate, the next stage must learn from labeled public data rather than only hard-coding thresholds.

## Literature-backed direction

### 1. Supervised pairwise/linker model before GNN

S2AND is the closest model to what we need. It defines AND as a production-scale scholarly author entity-resolution task, harmonizes multiple datasets, and shows that training on a union of datasets improves robustness to unseen datasets. The S2AND paper reports that its model reduced Semantic Scholar production error by over 50% in terms of B-cubed F1. The public repository provides datasets, training/evaluation APIs, inference APIs, and production model artifacts.

Practical implication for our framework:

1. Keep the current deterministic framework as a safe baseline and audit layer.
2. Add a supervised pairwise scorer trained on public labeled data.
3. Use calibrated probabilities and margins to reduce UNKNOWN only when the model is confident.
4. Continue to report false-link rate separately for `truth-not-in-history` / new-author cases.

### 2. Candidate assignment should be a ranking/linking task, not only pair classification

Culotta et al. showed that a plain pair classifier followed by clustering misses evidence available at the cluster/profile level, such as coauthor sets and publication history. Their error-driven ranking approach reduced errors compared with standard binary classification.

Practical implication:

- Train the model to rank candidate author profiles for a new mention, not only to decide whether two isolated mentions match.
- Use top-1 score, top-2 margin, and author-profile aggregate features as production confidence signals.

### 3. Hybrid features are better than text-only or graph-only models

Hybrid pairwise AND work combines manually structured metadata features with learned text/global representations, and reports gains over earlier pairwise methods. OpenAlex also describes author disambiguation as a machine-learning problem using name variants, coauthors, affiliations, research topics, citation patterns, and ORCID when available.

Practical implication:

Our next feature set should add:

- title / abstract token similarity;
- venue / journal similarity;
- topic / field similarity;
- reference or citation overlap where available;
- author-profile aggregate features, e.g. historical affiliation tokens, topic centroid, coauthor graph neighborhood, year span;
- top-candidate margin features.

### 4. GNN is useful, but should be a second-stage reranker

Recent graph and heterogeneous-GNN papers use paper-author-affiliation-venue-topic/coauthor graphs and can improve representation quality, especially on WhoIsWho/AMiner-style data. However, GNNs add complexity and leakage risk. They should be compared against a strong non-GNN supervised model first.

Practical implication:

- Do not replace the current framework with a GNN immediately.
- First build a strong supervised pairwise/linker baseline.
- Add graph features without deep learning first.
- Use GNN only if it improves precision/recall/UNKNOWN tradeoff on held-out public datasets.

## Public data sources to use without ISTINA

| Source | Use | Why it matters |
|---|---|---|
| S2AND full release | Main supervised training and leave-one-dataset-out validation | Unified benchmark across multiple AND datasets; directly matches scholarly AND. |
| WhoIsWho / AMiner | Hard same-name and incremental assignment benchmark | Large-scale benchmark with real ambiguous author names and an online-system framing. |
| DBLP public data | Computer-science coauthor graph stress test | Good for coauthor structure and name variants; weaker metadata. |
| LAGOS-AND | High-risk sparse/abbreviated metadata validation | Useful negative stress test for false-link control. |
| Author-ity / PubMed Computed Authors | Biomedical large-scale profile validation | PubMed-scale disambiguated clusters and rich biomedical metadata. |
| OpenAlex snapshot / API | Topic, institution, citation, ORCID-derived auxiliary features | Useful for model features and external validation, not as direct gold without caution. |

## Next algorithmic architecture

```text
raw author mention
  -> current multilingual name normalization
  -> candidate generation by family + initials + alias variants
  -> supervised pairwise/profile linker
       features:
         name compatibility
         affiliation similarity
         coauthor overlap and graph support
         title/venue/topic similarity
         year distance
         citation/reference overlap if available
         author-profile aggregate features
       output:
         calibrated probability per candidate
         top-1 / top-2 margin
  -> risk controller
       LINK if precision-calibrated probability and margin pass
       NEW if all candidates are below calibrated rejection threshold
       UNKNOWN only for the remaining narrow conflict zone
  -> clustering / profile update
```

## Evaluation protocol

The next production gate should no longer accept “safe but mostly UNKNOWN” as sufficient.

Suggested gates:

1. Linkable precision: `>= 99.5%`.
2. New-author false-link rate: `<= 1.0%`.
3. UNKNOWN rate on rich metadata datasets: target `<= 15%`.
4. UNKNOWN rate on sparse public datasets: target should be reported separately; initial target `<= 40%`, then lowered after adding text/topic/citation features.
5. Candidate coverage: report separately, because no classifier can recover a true author absent from the candidate set.
6. Leave-one-source-out validation: train on several public sources, test on an unseen source.
7. Hard-case validation: exact same name, initials-only, Chinese/Korean/common surnames, same institution, same field, new-author-with-candidates.

## Implementation plan

### Stage A: no new heavy dependency

1. Add a public-data supervised feature exporter. **Status: implemented in `experiments/export_author_linker_features.py`.**
2. Export pair/profile features from S2AND, DBLP, LAGOS, and local ORCID datasets.
3. Save reproducible train/validation/test manifests with SHA-256 hashes.
4. Measure the oracle ceiling:
   - candidate coverage;
   - best possible recall if the true author is in the candidate set;
   - UNKNOWN cases that lack enough features.

The first export was generated on 2026-07-02 across Crossref ORCID, Advisor DOI ORCID, DBLP, LAGOS-AND, and S2AND. It produced `428,436` supervised candidate-pair rows: `119,962` positive pairs and `308,474` negative pairs. The large JSONL feature file is kept under ignored `runs/`; the committed manifest is `results/article2_supervised_feature_export_manifest_20260702.json`.

### Stage B: optional supervised model

1. Add optional dependency group for `scikit-learn` or `lightgbm`, not a hard dependency of the core package.
2. Train logistic regression / gradient boosting as the first supervised baseline.
3. Calibrate thresholds to satisfy false-link gates while minimizing UNKNOWN.
4. Compare against:
   - current `framework_v1`;
   - ISTINA hypergraph proxy;
   - risk-controlled hybrid;
   - S2AND-style supervised model.

On 2026-07-02, a no-dependency logistic-regression baseline was tested as a first sanity check on the exported pairwise features. It used leave-one-dataset-out validation over Crossref ORCID, Advisor DOI ORCID, DBLP, LAGOS-AND, and S2AND. The result is saved as `results/article2_supervised_linker_baseline_20260702.json`.

This simple baseline is **not** a production candidate:

| Held-out dataset | Logistic P/R/F1 | Current balanced P/R/F1 | Strict P/R/F1 |
|---|---:|---:|---:|
| Advisor DOI ORCID | 99.460 / 37.797 / 54.777 | 99.049 / 77.227 / 86.787 | 99.513 / 27.612 / 43.230 |
| Crossref ORCID | 97.771 / 41.416 / 58.185 | 97.570 / 75.660 / 85.230 | 98.236 / 29.844 / 45.780 |
| DBLP public | 99.766 / 15.360 / 26.621 | 99.302 / 80.256 / 88.769 | 99.492 / 19.572 / 32.709 |
| LAGOS-AND public | 99.452 / 5.804 / 10.968 | 89.632 / 70.716 / 79.058 | 99.618 / 9.380 / 17.146 |
| S2AND public | 94.944 / 15.024 / 25.943 | 64.477 / 61.132 / 62.760 | 94.137 / 10.212 / 18.425 |

The simple model is too conservative and does not solve the high-UNKNOWN problem. Its value is diagnostic: pairwise scalar features alone are not enough. The next supervised iteration should use profile-level/ranking features and a stronger optional learner such as LightGBM, with threshold calibration on validation folds.

### Stage B2: candidate-capped graph relaxation

On 2026-07-02, a read-only scan tested whether the current hybrid could safely lower UNKNOWN by accepting graph-supported predictions at `support >= 0.5` only when the online candidate set is small. This was tested before changing the production algorithm.

Best internal candidate:

| Dataset | Rule | Link precision | Link recall | UNKNOWN | New-author false-link | Decision |
|---|---|---:|---:|---:|---:|---|
| Crossref ORCID | support >= 0.5 and candidates <= 3 | 99.524% | 89.407% | 10.166% | 0.982% | Not adopted |
| Advisor DOI ORCID | support >= 0.5 and candidates <= 3 | 99.906% | 91.556% | 8.358% | 0.299% | Not adopted |

This almost improves the internal online gate, but it still misses the low-UNKNOWN target on Crossref (`recall >= 90%`, `UNKNOWN <= 10%`) and has a smaller precision safety margin than the current production setting.

Public-dataset check:

| Dataset | Profile/rule | Link precision | Link recall | UNKNOWN | New-author false-link | Decision |
|---|---|---:|---:|---:|---:|---|
| DBLP public | balanced, support >= 0.5 and candidates <= 3 | 99.597% | 82.786% | 16.879% | 0.534% | Not enough |
| LAGOS-AND public | strict, support >= 0.5 and candidates <= 3 | 100.000% | 1.563% | 98.438% | 0.055% | No practical gain |
| S2AND public | strict, support >= 0.5 and candidates <= 3 | 100.000% | 1.129% | 98.871% | 0.000% | No practical gain |

Balanced-profile scans on LAGOS-AND and S2AND were also rejected because they lowered UNKNOWN only by creating too many false links:

- LAGOS-AND balanced online: link precision `88.254%`, new-author false-link `14.678%`.
- S2AND balanced online: link precision `87.593%`, new-author false-link `8.143%`.

Conclusion: a small rule relaxation is not sufficient. This rule should not be added to production. Low-UNKNOWN progress requires a profile-level ranker with stronger public training data and explicit new-author rejection.

### Stage B3: sampled mention-level ranking diagnostic

On 2026-07-02, `experiments/analyze_author_linker_ranking_ceiling.py` tested mention-level candidate ranking over the existing exported pairwise feature table. The run used `428,436` feature rows from Crossref ORCID, Advisor DOI ORCID, DBLP, LAGOS-AND, and S2AND, with leave-one-dataset-out threshold and margin selection. The result is saved as `results/article2_author_linker_ranking_ceiling_20260702.json`.

Best observed held-out results still failed the low-UNKNOWN gate:

| Scorer | Weakest held-out behavior | Main failure |
|---|---|---|
| `framework_balanced_score` | S2AND: precision 97.769%, recall 41.569%, UNKNOWN 57.482%, new false-link 6.705% | false links and UNKNOWN |
| `framework_strict_score` | S2AND: precision 98.051%, recall 21.396%, UNKNOWN 78.178%, new false-link 1.686% | recall and false links |
| `context_score` | S2AND: precision 97.368%, recall 42.852%, UNKNOWN 55.990%, new false-link 6.966% | false links and UNKNOWN |

Internal datasets also did not meet the low-UNKNOWN target. For example, `framework_balanced_score` on Crossref reached precision `99.786%`, but recall was only `49.951%` and UNKNOWN was `49.942%`; Advisor DOI ORCID reached recall `73.283%` with new-author false-link `1.727%`, above the current `1%` false-link gate.

Conclusion: the existing sampled pairwise feature table is useful for diagnostics, but it is not enough for a production low-UNKNOWN ranker. The next implementation should export true mention-to-profile candidate features from the online benchmark, including candidate coverage, top-k profile scores, profile-level coauthor/affiliation aggregation, graph support, and explicit new-author negative examples.

### Stage C: graph/GNN extension

1. Build a heterogeneous graph schema:
   - author-mention nodes;
   - candidate-profile nodes;
   - paper nodes;
   - venue/source nodes;
   - affiliation/institution nodes;
   - topic/reference/coauthor edges.
2. Start with graph-derived non-neural features.
3. Test GNN/heterogeneous attention only after the supervised non-GNN baseline is strong.

## Current decision

The next real iteration should not further tune the strict thresholds. That would only move along the same precision/UNKNOWN tradeoff curve.

The correct next step is to build a supervised public-data training layer. The current deterministic rules should remain as:

- a baseline;
- a safe fallback;
- a set of interpretable features;
- a risk-control wrapper around learned scores.

## References and source links

- Subramanian, S., King, D., Downey, D., & Feldman, S. (2021). *S2AND: A Benchmark and Evaluation System for Author Name Disambiguation*. JCDL 2021. <https://arxiv.org/abs/2103.07534>
- AI2/Semantic Scholar S2AND repository. <https://github.com/allenai/S2AND>
- Chen, B., Zhang, J., Zhang, F., Han, T., Cheng, Y., Li, X., Dong, Y., & Tang, J. (2023). *Web-Scale Academic Name Disambiguation: the WhoIsWho Benchmark, Leaderboard, and Toolkit*. KDD 2023. <https://arxiv.org/abs/2302.11848>
- THUDM WhoIsWho toolkit. <https://github.com/THUDM/WhoIsWho>
- Culotta, A., Kanani, P., Hall, R., Wick, M., & McCallum, A. (2007). *Author Disambiguation using Error-driven Machine Learning with a Ranking Loss Function*. <https://www.cs.umass.edu/~mccallum/papers/culotta07author.pdf>
- Kim, K., Rohatgi, S., & Giles, C. L. (2019). *Hybrid Deep Pairwise Classification for Author Name Disambiguation*. CIKM 2019. <https://clgiles.ist.psu.edu/pubs/CIKM2019.pdf>
- OpenAlex documentation: *Author disambiguation*. <https://help.openalex.org/hc/en-us/articles/24347048891543-Author-disambiguation>
- NCBI PubMed Computed Authors API / FTP. <https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/authors/>
- Torvik, V. I., & Smalheiser, N. R. *Author-ity 2009 - PubMed author name disambiguated dataset*. University of Illinois Data Bank. <https://databank.illinois.edu/datasets/IDB-4222651>
- Wang, G., Sun, Z., HU, W., & Cai, M. (2025). *Author name disambiguation based on heterogeneous graph neural network*. PLOS ONE. <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0310992>
