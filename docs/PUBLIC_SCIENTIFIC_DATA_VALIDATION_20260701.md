# Public scientific-data validation for the Article 2 author-disambiguation framework

Date: 2026-07-01

This note records the public datasets collected in this iteration, how they were converted into the local evaluation format, and what the tests show. ORCID/DBLP person identifiers are used only as gold labels; they are not passed to the matching algorithm as features.

## Public datasets used

| Dataset | Source | Local builder | Local sample | Gold label | Notes |
|---|---|---:|---:|---|---|
| DBLP XML dump | [DBLP XML release](https://dblp.org/xml/) | `experiments/build_dblp_public_author_mentions.py` | 60,000 author mentions; 35,092 author identities; 13,468 papers | DBLP `author/@pid` when available | Stress test with names and coauthor graph, but no affiliations. |
| LAGOS-AND-BLOCK-TRIMMED | [Zenodo record 7313380](https://zenodo.org/records/7313380) | `experiments/build_lagos_public_author_mentions.py` | 80,000 sampled author mentions; 40,756 ORCID identities; 79,916 papers | ORCID | Hard benchmark with many abbreviated names and ambiguous ORCID blocks. |

The LAGOS sample is produced with deterministic reservoir sampling over the full compressed CSV (`seed=20260701`) instead of taking the first rows, because the original file is block-ordered by names.

## Commands

```powershell
python experiments\build_dblp_public_author_mentions.py --output runs\public_dblp_20260701\dblp_public_mentions.json --min-year 2018 --max-year 2025 --min-authors 2 --max-mentions 60000
python experiments\build_lagos_public_author_mentions.py --source external_data\lagos_and\LAGOS-AND-BLOCK-TRIMMED.csv.tar.gz --output runs\public_lagos_and_20260701\lagos_public_mentions.json --max-mentions 80000 --seed 20260701
```

The raw public archives and generated large JSON datasets are local experiment inputs and are not committed to the repository.

## Main public-data results

### Offline clustering

| Dataset / profile | Candidate P/R/F1 | Cluster P/R/F1 | B³ F1 | Gate |
|---|---:|---:|---:|---|
| DBLP, balanced | 98.927 / 80.138 / 88.547 | 94.933 / 89.308 / 92.035 | 97.192 | FAIL |
| LAGOS-AND, balanced | 79.820 / 70.010 / 74.594 | 79.065 / 77.089 / 78.064 | 89.306 | FAIL |
| LAGOS-AND, strict | 99.497 / 9.330 / 17.061 | 99.533 / 11.363 / 20.397 | 72.932 | Precision-only safe; recall too low |

Interpretation: public offline clustering confirms that full automatic clustering is not safe on sparse or heavily abbreviated public metadata. The strict profile can control false merges, but it is not a replacement for balanced clustering because recall becomes very low.

### Online LINK / NEW / UNKNOWN decision

| Dataset / profile | Hybrid link P/R/F1 | Unknown rate | New-author false-link rate | Gate |
|---|---:|---:|---:|---|
| DBLP, balanced | 99.596 / 82.708 / 90.370 | 16.957 | 0.486% (81 / 16,659) | PASS |
| LAGOS-AND, balanced | 88.254 / 65.156 / 74.966 | 26.172 | 14.678% (267 / 1,819) | FAIL |
| LAGOS-AND, strict | 100.000 / 1.562 / 3.077 | 98.438 | 0.055% (1 / 1,819) | PASS as high-risk auto-link-minimal mode |

Interpretation: balanced remains suitable for richer bibliographic metadata, while strict is useful for very high-risk sources where the correct operational behavior is to automatically link only the safest cases and route nearly everything else to manual review / UNKNOWN.

## What changed in code

1. Added DBLP public dataset builder:
   - Uses DBLP `pid` as the preferred evaluation label.
   - Removes DBLP disambiguation suffixes such as `0001` from name features so labels are not leaked.

2. Added LAGOS-AND public dataset builder:
   - Streams the compressed public CSV archive.
   - Samples deterministically across the full file.
   - Preserves `author_name`, `author_affiliation`, DOI/paper id, year, and coauthor metadata.

3. Added optional `coauthors` support to the framework input schema:
   - If a row contains explicit coauthor names, they are added to the coauthor-context feature.
   - Existing datasets without this field are unaffected.

4. Added `strict` framework profile:
   - Intended for high-risk public data with abbreviated names and dense homonyms.
   - Keeps automatic false links very low by routing most cases to UNKNOWN.
   - Not used as the main balanced production profile because recall is intentionally low.

## Current conclusion

The current final framework should be described as a risk-controlled author-disambiguation framework, not as a universal fully automatic clustering system.

- On our existing large ORCID-labeled Crossref/advisor datasets, the final validation still passes production gates.
- On DBLP, the online LINK/NEW/UNKNOWN mode also passes, despite lack of affiliation metadata.
- On LAGOS-AND, balanced mode is not production-safe; strict mode is safe only as a conservative auto-link-minimal mode.

Therefore, the article should present two operational profiles:

1. `balanced`: main production profile for richer metadata and the current Crossref/advisor pipeline.
2. `strict`: high-risk public-import profile where low false-link rate is more important than recall, and UNKNOWN/manual review is expected.

## Data still needed from the advisor / ISTINA side

To make the production claim stronger, we still need an ISTINA-verified dataset with:

1. `article_id`, DOI, year, venue/title;
2. author position and raw displayed author name;
3. verified `worker_id` / true author id for each mention;
4. full coauthor list for each paper;
5. affiliation / organization at the mention level when available;
6. split by time, e.g. history `<= 2021`, test `2022-2024/2025`;
7. marked new-author cases where the true author is absent from history;
8. preferably hard cases: exact same names, same initials, Chinese/Korean/common surnames, transliteration variants, and same-institution homonyms.

This data is necessary to compare the new framework with the real ISTINA implementation under the same production candidate-generation conditions.
