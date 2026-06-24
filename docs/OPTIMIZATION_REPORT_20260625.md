# Multilingual name-order optimization report (2026-06-25)

## Outcome

The final algorithm adds three conservative token-role fallbacks to the mentor
branch:

1. the existing pair-disjoint Crossref role model;
2. independent Japanese surname/given evidence derived from JMnedict;
3. normalized US given-name/surname evidence from SSA national baby names and
   the 2010 US Census surname table.

The SSA/Census model may also override a Western *name morphology* heuristic
when the normalized role log-odds differ by at least 4. It does not override
exact split-field structure, abbreviations, or strong non-Chinese surname
evidence.

## Frozen evaluation results

The reported score is `errors + unknown` across both generated display orders,
using person and publication consistency. Lower is better.

| Dataset / configuration | Errors | Unknown | Combined |
|---|---:|---:|---:|
| Local pinyin-compatible mentor baseline | 4,468 | 6,376 | 10,844 |
| + pair-disjoint Crossref role model | 1,484 | 2,647 | 4,131 |
| + JMnedict | 1,282 | 2,635 | 3,917 |
| + SSA/Census role model | 1,104 | 2,431 | 3,535 |
| **Final, including morphology correction** | **1,063** | **2,425** | **3,488** |

The final score is 7,356 lower than the mentor baseline (`-67.83%`) on 97,810
candidate records from the 301,586-row local file.

| Independent check | Before new external roles | Final | Change |
|---|---:|---:|---:|
| Pair-disjoint holdout, 20,046 records | 4,469 | 4,153 | -316 (-7.07%) |
| Mentor DOI dataset, 11,822 records | 1,322 | 1,252 | -70 (-5.30%) |
| Frozen Wikidata final set, 1,660 unseen pairs | 796 | 387 | -409 (-51.38%) |

The Wikidata sample uses structured `P735` (given name) and `P734` (family
name), excludes all normalized pairs in the local dataset and the earlier
diagnostic Wikidata sample, and is not used for training or threshold selection.

## Full local non-Chinese-inclusive test

With `--candidate-filter all`, 301,559 rows had non-empty structured given and
family fields (100,004 unique pairs). Both display orders produced 603,118
decisions.

| Role-model ablation | Errors | Unknown | Combined |
|---|---:|---:|---:|
| All role models disabled | 122,444 | 1,181 | 123,625 |
| **Final model** | **35,460** | **714** | **36,174** |

The combined score decreased by 87,451 (`-70.74%`). This is the direct
large-scale test of the mentor's concern about non-Chinese names.

## Rejected candidates

- Census surname frequency alone improved the development and holdout sets but
  regressed the mentor DOI set from 1,300 to 1,314; it is not used.
- Requiring Census Asian-population share did not improve the development set;
  it is not used.
- Western morphology override margins 3 and 5 produced diagnostic combined
  scores 647 and 663, versus 645 at margin 4; both were rejected.
- Full SSA/Census fallback margins 1/2/3/4 were compared on a separate
  development bucket. Margin 4 with minimum support 5 was frozen before
  holdout, mentor DOI, and external testing.

## Data integrity and provenance

| Artifact | SHA-256 |
|---|---|
| Local Crossref input | `3546bcf7fa3566ab5ddc7105829c28df890e34544700034c70efbe2af7639806` |
| Mentor DOI input | `cf06727bf5c7241cb4729904db503c9224ad45145d780193d796e55d89eacf02` |
| JMnedict XML gzip | `cae0f5bca478aed29496bbf0db554793f133f4b5c25917f3a926eeefd8fa47e0` |
| SSA `names.zip` | `cd78e975ed7bb358e018dd62fbe14ced89295e9581c49172ca4eedcb011b3724` |
| Census `names.zip` | `117c41cb4668727b7627b2845b6df3f83eb2a22a1813f42c0ff4bdcab86de135` |
| Frozen SSA/Census derived model | `0a00a9bfffa568bd12b8d528062516d71293f8519f264b6e4271459c8e19a550` |
| Frozen Wikidata final sample | `d7536b3ba2d5e212c38181813a55e7fbc64896ad047cabae6af19b808231a7c0` |

Source and redistribution details are in
[`JMNEDICT_ATTRIBUTION.md`](../data/JMNEDICT_ATTRIBUTION.md) and
[`SSA_CENSUS_ATTRIBUTION.md`](../data/SSA_CENSUS_ATTRIBUTION.md).

## Reproduction

```powershell
$env:PYTHONPATH='.'
python -m pytest -q

python experiments/evaluate_mentor_large_scale.py `
  --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --output results/final_pinyin.json `
  --surname-frequency-strategy freq_disabled

python experiments/evaluate_mentor_large_scale.py `
  --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --output results/final_all_names.json `
  --surname-frequency-strategy freq_disabled `
  --candidate-filter all
```

The evaluation JSON records every feature switch, candidate count, dataset
hash, error sample, and mode count.

## Concise Russian summary for the supervisor

На основе ветки научного руководителя мы добавили три консервативных источника
признаков роли токена: раздельную по парам модель Crossref, японский словарь
JMnedict и нормализованную модель «имя/фамилия» по данным SSA и переписи США.
Кроме того, статистика ролей исправляет только ошибочные морфологические
эвристики западных имён и не переопределяет надёжные структурные признаки.

На 97 810 записях итоговый показатель `ошибки + неизвестные` снизился с 10 844
до 3 488 (-67,83%). На полном наборе из 301 559 записей он снизился с 123 625
до 36 174 (-70,74%). На независимой выборке Wikidata из 1 660 ранее не
встречавшихся пар число ошибок снизилось с 796 до 387 (-51,38%). Все параметры
проверены на отдельной отложенной выборке и наборе DOI руководителя; варианты,
которые давали ухудшение хотя бы на одном наборе, были исключены.
