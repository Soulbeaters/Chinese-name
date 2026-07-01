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

1. Add a public-data supervised feature exporter.
2. Export pair/profile features from S2AND, DBLP, LAGOS, and local ORCID datasets.
3. Save reproducible train/validation/test manifests with SHA-256 hashes.
4. Measure the oracle ceiling:
   - candidate coverage;
   - best possible recall if the true author is in the candidate set;
   - UNKNOWN cases that lack enough features.

### Stage B: optional supervised model

1. Add optional dependency group for `scikit-learn` or `lightgbm`, not a hard dependency of the core package.
2. Train logistic regression / gradient boosting as the first supervised baseline.
3. Calibrate thresholds to satisfy false-link gates while minimizing UNKNOWN.
4. Compare against:
   - current `framework_v1`;
   - ISTINA hypergraph proxy;
   - risk-controlled hybrid;
   - S2AND-style supervised model.

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
