# 文章二作者消歧框架实现与真实测试记录（2026-06-28）

## 当前实现

新增 `framework_v1` 作者消歧框架，用于文章二的“多语言姓名规范化 + 作者实体消歧”实验。ORCID 只作为评估标签，不作为算法特征。

核心组成：

1. 多语言姓名规范化：统一处理 Latin/Cyrillic/CJK token、变音符、缩写、复合名。
2. 阻塞策略：按 `family name + given-name initial` 生成候选对，避免全量两两比较。
3. 姓名变体兼容：支持 exact、prefix（如 `Vyacheslav` / `Vyacheslav A.`）、initial-compatible。
4. 上下文特征：IDF 加权机构相似度、共同作者 Jaccard、年份间隔。
5. 聚类：对判定为同一作者的候选对做 Union-Find 聚类，并报告候选对指标、聚类 pairwise 指标和 B³ 指标。

新增文件：

- `src/author_disambiguation.py`
- `experiments/evaluate_author_disambiguation_framework.py`
- `tests/test_author_disambiguation.py`

## 数据集与测试口径

### Crossref ORCID 大规模本地数据

- 原始路径：`C:\istina\materia 材料\测试表单\crossref_authors.json`
- SHA-256：`3546bcf7fa3566ab5ddc7105829c28df890e34544700034c70efbe2af7639806`
- 进入评估的记录：150,775 条带 ORCID、firstname、lastname 的作者记录
- 唯一 ORCID：45,730
- 评估候选对：2,265,741
- 超大 block：26；其中按 exact normalized full name 恢复比较 742 个子 block、111,455 个候选对

### 导师 DOI Crossref API ORCID 数据

- 原始路径：`runs\advisor_doi_20260507\advisor_doi_crossref_api_authors.json`
- SHA-256：`cf06727bf5c7241cb4729904db503c9224ad45145d780193d796e55d89eacf02`
- 进入评估的记录：19,180 条带 ORCID、firstname、lastname 的作者记录
- 唯一 ORCID：12,456
- 评估候选对：28,436
- 跳过超大 block：0

测试规则：

- ORCID 仅用于计算 TP/FP/FN。
- 同一篇论文内的作者对不参与合并评估，避免把论文作者列表内的不同作者误当作重复实体。
- 旧 `baseline_exact_context` 与新 `framework_v1` 使用同一评估器，保证指标可比。

## 真实测试结果

### Crossref ORCID 数据

| 算法 | 候选对 Precision | 候选对 Recall | 候选对 F1 | 聚类 Precision | 聚类 Recall | 聚类 F1 | B³ F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_exact_context | 99.649% | 47.568% | 64.396% | 98.894% | 63.504% | 77.343% | 86.575% |
| framework_v1 balanced | 99.653% | 46.975% | 63.851% | 99.258% | 69.068% | 81.456% | 88.632% |
| framework_v1 conservative | 99.664% | 42.376% | 59.467% | 99.234% | 61.507% | 75.943% | 86.915% |

结论：在 Crossref 大规模数据上，`framework_v1 balanced` 的候选对 F1 与 baseline 基本持平，但聚类 Recall 提升 5.564 个百分点，聚类 F1 提升 4.113 个百分点，B³ F1 提升 2.056 个百分点。与上一版整体跳过超大 block 的结果相比，Crossref 聚类 F1 从 78.395% 提升到 81.456%，B³ F1 从 87.139% 提升到 88.632%，并且聚类 precision 仍保持 99% 以上。

### 导师 DOI ORCID 数据

| 算法 | 候选对 Precision | 候选对 Recall | 候选对 F1 | 聚类 Precision | 聚类 Recall | 聚类 F1 | B³ F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_exact_context | 99.133% | 45.241% | 62.129% | 99.136% | 54.098% | 69.998% | 91.437% |
| framework_v1 balanced | 99.203% | 53.657% | 69.645% | 99.152% | 65.477% | 78.870% | 93.293% |
| framework_v1 conservative | 99.337% | 52.535% | 68.724% | 99.271% | 64.210% | 77.981% | 93.046% |

结论：在导师 DOI 数据上，`framework_v1 balanced` 明显优于 baseline：候选对 F1 提升 7.516 个百分点，聚类 F1 提升 8.872 个百分点，B³ F1 提升 1.856 个百分点，同时 precision 仍保持 99% 以上。

## 当前判断

当前最好的版本是 `framework_v1 balanced`。

它已经证明导师所说的“还有优化空间”是存在的：在导师 DOI 数据和 Crossref 聚类指标上都有真实提升。该版本适合作为文章二的第一版自研算法框架和后续与 ISTINA 现行算法比较的基线。

但它还不能直接声明为最终生产级版本：

- precision 已基本达到生产系统可接受水平（候选对与聚类 precision 均 >99%）。
- recall 仍不足，尤其 Crossref 大规模数据的 B³ F1 为 88.632%，距离 95% 以上的强生产目标还有差距。
- 主要错误来源仍是中文拼音式同名作者：常见姓名在同机构、同团队、相似共同作者网络中容易产生误合并；过度收紧会显著降低 recall。

## 2026-06-28 迭代记录：首字母姓名保护规则

本轮测试了一个更保守的规则：对于 `K Liu` / `K. Liu` 这类只有首字母的 exact-name 情况，不再允许仅凭共同作者相似度合并，而要求同时有机构相似度支持。

该规则在两个大规模数据集上均未通过验证，因此没有采用为最终算法：

| 数据集 | profile | 候选对 Precision | 候选对 Recall | 聚类 Precision | 聚类 Recall | B³ F1 | 结论 |
|---|---|---:|---:|---:|---:|---:|---|
| Crossref ORCID | balanced | 99.636% | 43.742% | 99.184% | 59.341% | 83.237% | recall 明显下降 |
| 导师 DOI ORCID | balanced | 98.983% | 35.102% | 98.932% | 45.956% | 89.544% | precision 跌破 99%，不可采用 |

因此当时的最终版本仍保持 `framework_v1 balanced`。本轮只保留工程清理：删除未参与判定的中文姓氏频率死特征，并固定加权 Jaccard 的求和顺序，使结果文件中的浮点样例可重复；核心指标与上一版 final 结果一致。

## 2026-06-28 迭代记录：超大 block 的 exact-name 子阻塞

本轮针对 Crossref 中 26 个被整体跳过的超大 block 做了最小候选生成优化：仍不进行超大 block 内全量两两比较，只在其中按 exact normalized full name 分组，并且只比较不超过 `max_block_size=200` 的子 block。

诊断显示，被跳过的 26 个大 block 中包含 99,911 个真实同人对，其中 89,008 个位于 exact-name 子 block 内。启用该策略后，Crossref 额外恢复 742 个 exact-name 子 block、111,455 个候选对；导师 DOI 数据没有超大 block，因此结果不变。

该策略已采用为当前 final 版本。它不改变 pairwise 判定规则，只改善候选召回边界。

## 2026-06-28 生产质量门禁

新增 `experiments/author_disambiguation_quality_gate.py`，用于统一汇总 baseline 与当前算法的结果，并给出生产可用性判断。默认门槛：

- 候选对 precision ≥ 99%
- 聚类 pairwise precision ≥ 99%
- B³ F1 ≥ 95%

当前 `framework_v1 balanced` 可以作为文章二的自研算法基线，但尚未通过生产最终门槛：precision 已达标，B³ F1 在 Crossref ORCID 与导师 DOI ORCID 两个数据集上仍未达到 95%。因此文稿中应表述为“已在真实数据上显著改善聚类质量的可解释基线框架”，而不是“最终生产系统”。

## 下一步实验方向

1. 与 ISTINA 现行算法做同数据、同标签、同指标的大规模比较。
2. 加入更多生产特征：email、机构 ID/ROR、国家/城市、题名/关键词/期刊、完整共同作者图，而不是只用姓名和自由文本机构。
3. 在当前规则框架上增加可解释的监督 pairwise 模型，例如 logistic regression / gradient boosting，用当前规则分数和上下文特征做输入。
4. GNN 暂不作为第一版生产算法，应作为后续对比模型：只有在强规则/监督 baseline 之上还能显著提升，才作为文章二创新点之一。

## 复现实验命令

```powershell
python experiments\evaluate_author_disambiguation_framework.py --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" --output results\article2_framework_v1_final_balanced_crossref_orcid_20260628.json --algorithm framework_v1 --profile balanced --max-block-size 200

python experiments\evaluate_author_disambiguation_framework.py --dataset "runs\advisor_doi_20260507\advisor_doi_crossref_api_authors.json" --output results\article2_framework_v1_final_balanced_advisor_orcid_20260628.json --algorithm framework_v1 --profile balanced --max-block-size 200

python experiments\evaluate_author_disambiguation_framework.py --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" --output results\article2_baseline_exact_context_crossref_orcid_20260628.json --algorithm baseline_exact_context --profile conservative --max-block-size 200

python experiments\evaluate_author_disambiguation_framework.py --dataset "runs\advisor_doi_20260507\advisor_doi_crossref_api_authors.json" --output results\article2_baseline_exact_context_advisor_orcid_20260628.json --algorithm baseline_exact_context --profile conservative --max-block-size 200

python experiments\author_disambiguation_quality_gate.py --warn-only --output results\article2_quality_gate_summary_20260628.json --pair "Crossref ORCID" results\article2_baseline_exact_context_crossref_orcid_20260628.json results\article2_framework_v1_final_balanced_crossref_orcid_20260628.json --pair "Advisor DOI ORCID" results\article2_baseline_exact_context_advisor_orcid_20260628.json results\article2_framework_v1_final_balanced_advisor_orcid_20260628.json
```

完整测试：

```powershell
pytest -q
python -m compileall -q src experiments tests
```
