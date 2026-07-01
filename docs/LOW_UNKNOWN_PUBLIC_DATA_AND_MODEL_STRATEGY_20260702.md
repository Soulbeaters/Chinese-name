# Low-UNKNOWN author disambiguation strategy without ISTINA gold data

Date: 2026-07-02

This note records the practical strategy for reducing both wrong automatic links and UNKNOWN/manual-review decisions when ISTINA-labeled data is unavailable. The current conservative production framework remains valid, but lowering UNKNOWN requires a stronger supervised ranking/clustering layer trained and validated on public author-disambiguation datasets.

## Current evidence from our repository

The no-dependency logistic-regression pairwise baseline was tested on the exported real feature table:

- feature rows: 428,436
- positive rows: 119,962
- negative rows: 308,474
- datasets: Advisor DOI ORCID, Crossref ORCID, DBLP public, LAGOS-AND public, S2AND public
- feature hash: `9a79654ddb5312a120c1c00efacd11481d8d1d544ac6230aa0ea9c4f8a030dbd`
- result file: `results/article2_supervised_linker_baseline_20260702.json`

Result: this simple logistic baseline is not a production candidate. It does not reliably pass the 0.995 precision gate across held-out datasets and its recall is much lower than the balanced rule baseline on several datasets. Therefore, it must not replace the current production path.

## Key technical conclusion

If we want low error and low UNKNOWN at the same time, the framework cannot be just a stricter dictionary/rule system or a simple pairwise classifier.

The next production-oriented architecture should be:

1. high-recall candidate generation;
2. supervised candidate ranking with hard negative mining;
3. graph/profile consistency features;
4. calibrated confidence scores by dataset/language/source;
5. assignment/clustering layer, not independent pairwise decisions;
6. UNKNOWN only for genuinely underdetermined cases.

In other words, UNKNOWN must be reduced by better evidence and calibration, not by relaxing safety thresholds.

## Useful public literature and datasets

### S2AND

Source:

- Paper: https://arxiv.org/abs/2103.07534
- Code/data: https://github.com/allenai/S2AND

Why it matters:

- S2AND is a unified benchmark and evaluation system for author name disambiguation.
- The paper states that it harmonizes eight datasets into a common format and feature set.
- It reports that a model trained on the union of S2AND datasets generalizes better than models trained on a single source and reduces Semantic Scholar production error by more than 50% in B³ F1 terms.
- The current repository provides benchmark datasets, production model artifacts, training/evaluation APIs, and large-scale inference support.

How we should use it:

- Use S2AND as the main public benchmark and external baseline.
- Compare our framework against the released S2AND-style pipeline, not only against our rules.
- Reuse its evaluation ideas: blocking, pairwise scoring, clustering, B³ F1, facet-level evaluation.

### LAGOS-AND

Source:

- Paper: https://arxiv.org/abs/2104.01821
- Dataset mirror/reference: https://github.com/carmanzhang/LAGOS-AND
- Zenodo record from search result: https://zenodo.org/records/7313380

Why it matters:

- Built automatically from ORCID and DOI.
- Initial version includes LAGOS-AND-BLOCK with 7.5M citations and 798K unique authors, plus LAGOS-AND-PAIRWISE with close to 1M instances.
- Useful for both clustering-style and pairwise classification-style evaluation.

How we should use it:

- Keep it as one of the main public gold/weak-gold sources.
- Use the pairwise part for model training and the block part for clustering validation.

### WhoIsWho / AMiner

Sources:

- Toolkit: https://github.com/THUDM/WhoIsWho
- Top solutions: https://github.com/THUDM/whoiswho-top-solutions
- AMiner-NA dataset page: https://www.scidb.cn/en/detail?dataSetId=142599a3eeb54910804204e18e86d6b1

Why it matters:

- WhoIsWho is a web-scale manually labeled academic name disambiguation benchmark.
- The top-solutions repository describes it as containing over 900,000 AMiner papers with owners annotated by crowdworkers.
- It provides two relevant settings: name disambiguation from scratch and incremental name disambiguation.
- Its toolkit already has semantic, adhoc, graph, and OAGBERT-style features.

How we should use it:

- Use WhoIsWho for the next serious low-UNKNOWN experiment because it directly matches our target problem: assigning papers to existing author profiles.
- Its incremental setting is especially close to production import workflows.

### ORCID Public Data File

Source:

- Documentation: https://info.orcid.org/documentation/integration-guide/working-with-bulk-data/
- Annual public files: https://orcid.figshare.com/collections/ORCID_Annual_Public_Data_Files/7931102

Why it matters:

- ORCID public data contains public information associated with ORCID records.
- It is useful for aliases, known works, external IDs, affiliations, and weakly supervised labels.

How we should use it:

- Use it to build verified author profiles and multilingual alias dictionaries.
- Use only records with enough evidence for training labels, e.g. ORCID + DOI/OpenAlex/Crossref agreement.

### OpenAlex

Source:

- About data: https://help.openalex.org/hc/en-us/articles/24397285563671-About-the-data
- Main site: https://openalex.org/

Why it matters:

- OpenAlex connects scholarly works, authors, institutions, sources, funders, and topics.
- It aggregates data from Crossref, ORCID, ROR, PubMed, PubMed Central, DOAJ, Unpaywall, repositories, and other sources.

How we should use it:

- Use OpenAlex snapshots/API to construct candidate profiles and cross-source agreement features.
- Do not treat OpenAlex author IDs as perfect gold for final claims; use them as weak labels or external system baselines.

### Author-ity / PubMed

Source:

- Dataset: https://databank.illinois.edu/datasets/IDB-2273402

Why it matters:

- Author-ity 2018 is based on PubMed 2018.
- The dataset page reports 29.1M article records and 114.2M author-name instances.
- It provides cluster IDs, name variants, emails, ORCIDs, year ranges, affiliation words, MeSH terms, journal names, title words, coauthor names, citations, and h-index fields.

How we should use it:

- Use it as a large-scale biomedical stress test.
- Because it is an algorithmically disambiguated resource rather than fully manual gold, use it for stress/weak-label validation, not as the sole final proof.

### Graph and neural approaches

Sources:

- Graph-based survey: https://pmc.ncbi.nlm.nih.gov/articles/PMC10557506/
- Recent heterogeneous graph neural network paper: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0310992
- WhoIsWho graph features and OAGBERT-style toolkit: https://github.com/THUDM/WhoIsWho

Practical conclusion:

- GNN is a reasonable research extension, but it should not be the immediate production dependency.
- The safer engineering path is to first add graph-derived features and a strong ranker. Only after that should we test a GNN against the strong non-GNN baseline.

## Proposed next implementation

### Stage 1: public benchmark adapters

Add import/evaluation adapters for:

- S2AND;
- WhoIsWho;
- LAGOS-AND block and pairwise formats;
- Author-ity PubMed sample;
- OpenAlex/ORCID weak-label pairs.

### Stage 2: profile-level candidate ranker

Replace the current experimental simple pairwise logistic baseline with a stronger ranking design:

- unit of prediction: mention-to-profile, not mention-to-mention only;
- training examples: true profile plus hard negative profiles from the same blocked name group;
- features:
  - name similarity and transliteration evidence;
  - coauthor overlap and weighted coauthor overlap;
  - affiliation and organization overlap;
  - title/topic/venue similarity;
  - year gap and career continuity;
  - ORCID/OpenAlex/Crossref agreement;
  - graph neighborhood overlap;
  - ambiguity priors by family name and initials;
  - language/script-specific features.

Recommended learner:

- first: LightGBM or scikit-learn HistGradientBoosting with probability calibration;
- second: learning-to-rank objective if candidate lists are stable;
- optional later: transformer/title embeddings and GNN embeddings.

### Stage 3: assignment and clustering layer

Do not make independent pairwise decisions for every pair. Use:

- top-k candidate ranking per author mention;
- per-paper consistency scoring using coauthor history;
- cluster-level constraints to avoid one mention linking to multiple profiles;
- calibrated accept/reject thresholds;
- explicit split/lump error accounting.

This is closer to S2AND and also closer to the existing ISTINA hypergraph logic.

### Stage 4: low-UNKNOWN acceptance gates

A realistic production target should be measured per dataset and per hard-case slice:

- automatic LINK precision: at least 0.995 on clean gold datasets;
- automatic LINK recall: target at least 0.90 after model/ranker stage;
- UNKNOWN/manual-review rate: target below 5% first, then below 2% if the public benchmarks support it;
- false merge/lumping rate: stricter than split rate, ideally below 0.5-1.0% on high-confidence automatic decisions;
- report hard slices separately: Chinese names, non-Latin names, same initials, same institution, same field, new-author cases.

If these gates are not met, the model should remain experimental.

## Article framing

The article should not claim that a dictionary-only approach solved production author disambiguation. The stronger and more defensible contribution is:

> A multilingual, evidence-calibrated author disambiguation framework that combines name dictionaries, public author-profile evidence, supervised candidate ranking, graph/profile consistency, and cross-dataset validation.

The innovation can be framed as:

1. multilingual name normalization and dictionary expansion;
2. integration of public scientific identity sources;
3. calibrated low-UNKNOWN decision layer;
4. comparison with graph/hypergraph-style author disambiguation;
5. reproducible public-dataset validation without depending on closed ISTINA labels.

