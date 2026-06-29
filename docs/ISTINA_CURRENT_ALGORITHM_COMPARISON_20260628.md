# ISTINA 现行作者消歧算法源码审计与同口径对比（2026-06-28）

## 1. 源码定位结论

本地审计路径：

`C:\istina\消歧算法及gnn，在istina内原型`

核心结论：

- 旧作者消歧核心在 `disambiguation-authors-master.zip` 中。
- Django 主系统接入层是单文件 `managers.py` 中的 `WorkerManager.get_disambiguation(...)`。
- `crossref-import-master.zip` 只有 README 和目录骨架，不能作为可执行算法源码。
- `graph-similarity-master.zip` 是独立图相似/ML 原型，不是 ISTINA 当前作者消歧服务入口。

关键旧算法文件：

```text
disambiguation-authors/core/disambiguation_authors_model.cpp
disambiguation-authors/core/disambiguation_authors_model_builder.cpp
disambiguation-authors/core/bibliographic_data_source.h
disambiguation-authors/test/data_source_t.cpp
disambiguation-authors/test/article_iterator.cpp
disambiguation-authors/test/article_t.cpp
```

Django 接入层：

```text
workers/managers.py
WorkerManager.get_disambiguation(...)
WorkerManager.get_similar(...)
WorkerManager.get_difflib_similar(...)
WorkerManager.get_very_similar(...)
WorkerManager.get_similar_smart(...)
WorkerManager.get_merge_candidates(...)
```

## 2. 为什么不能直接运行旧 C++ 服务

当前本地 zip 能支持源码审计，但不能直接作为 JSON benchmark 程序运行，原因如下：

1. `disambiguation-authors/test/test.pro` 依赖 Oracle client：

   ```text
   -lclntsh -lnnz12
   /Users/artem/instantclient_12_2-3/sdk/include
   ```

2. 测试数据源 `data_source_t.cpp` 直接查询 ISTINA 数据库表：

   ```sql
   authora
   man
   manalias
   article
   ```

3. C++ core 工程中的 `main.cpp` 是空入口，`request/response` 也基本是占位。
4. `core.pro` 引用了 `data_source_local_db.cpp` / `data_source_local_db.h`，但当前 zip 中没有这些文件。

因此，本文档中的“ISTINA hypergraph proxy”不是已编译运行的旧服务，而是根据源码结构实现的同口径 Python proxy，用于在我们已有 ORCID JSON 数据上做可复现实验。

## 3. 旧算法技术本质

旧算法不是单个姓名 pair matching，而是整篇论文的组合优化：

1. 对每个署名位置生成候选作者。
2. 将候选作者作为 vertex，将署名位置作为 label。
3. 用历史共同发表论文构造合著者 hyperedge。
4. 对 hypergraph 做 partition 和 gamma 矩阵传播。
5. 优化目标函数 `z(S)`，为一篇论文的所有署名位置选择整体最一致的作者组合。

这解释了为什么旧算法在 ISTINA 内部库中会很强：它利用的是整篇论文作者组合的历史合作结构，而不是单个作者姓名相似度。

## 4. 本轮可复现实验设计

为了和当前自研 `framework_v1` 做同口径比较，本轮新增：

```text
src/istina_hypergraph_proxy.py
experiments/evaluate_istina_hypergraph_proxy.py
tests/test_istina_hypergraph_proxy.py
```

实验口径：

- ORCID 仅作为 gold label 和历史 author id 代理，不作为特征。
- 使用 2021 年作为 history/test 切分点：
  - history：`year <= 2021`
  - test：`year > 2021`
- 只使用带 ORCID 的作者记录，与现有 gold label 范围一致。
- 姓名候选集：同 family name，并且 given name exact / prefix / initial-compatible。
- 四个方法在同一候选集上比较：
  1. `name_most_frequent`：姓名候选中历史出现次数最多者；
  2. `istina_hypergraph_proxy`：按整篇论文的候选作者组合进行历史合著支持优化，并约束同一历史作者不重复分配给同一篇论文的多个署名；
  3. `framework_v1_profile`：用当前 `framework_v1 balanced` pairwise 规则做 profile linking；不能高置信判断时输出 UNKNOWN。
  4. `risk_controlled_hybrid`：先接受 `framework_v1_profile` 的高置信结果；若 framework 输出 UNKNOWN，则仅在 ISTINA hypergraph proxy 的论文级组合选择结果具有历史合著支持分数 `>= 1.25` 时接受其 LINK，否则输出 UNKNOWN。

当前 proxy 已从逐署名单独打分升级为论文级 beam 组合选择（默认 beam size = 256），更接近旧 ISTINA C++ 服务“为整篇论文寻找最一致作者组合”的目标函数思想。

结果文件：

```text
results/article2_istina_proxy_online_crossref_orcid_20260628.json
results/article2_istina_proxy_online_advisor_orcid_20260628.json
results/article2_hybrid_threshold_sweep_20260629.json
```

复现实验命令：

```powershell
python experiments\evaluate_istina_hypergraph_proxy.py --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" --output results\article2_istina_proxy_online_crossref_orcid_20260628.json --cutoff-year 2021 --max-profile-mentions 30 --hypergraph-support-threshold 1.25

python experiments\evaluate_istina_hypergraph_proxy.py --dataset "runs\advisor_doi_20260507\advisor_doi_crossref_api_authors.json" --output results\article2_istina_proxy_online_advisor_orcid_20260628.json --cutoff-year 2021 --max-profile-mentions 30 --hypergraph-support-threshold 1.25

python experiments\sweep_istina_hybrid_thresholds.py --output results\article2_hybrid_threshold_sweep_20260629.json
```

## 5. Crossref ORCID 大规模数据结果

数据规模：

- history mentions：38,480
- history authors：16,040
- test mentions：82,335
- truth-in-history test mentions：35,787
- candidate-covered mentions：35,380
- candidate coverage vs truth-in-history：98.863%

### 5.1 共同候选集评分

只在“真值作者位于候选集内”的 35,380 条 test mention 上比较选择能力：

| 方法 | Precision | Recall | F1 | UNKNOWN | Paper exact |
|---|---:|---:|---:|---:|---:|
| name_most_frequent | 93.796% | 93.796% | 93.796% | 0.000% | 85.573% |
| istina_hypergraph_proxy | 97.834% | 97.773% | 97.803% | 0.062% | 93.865% |
| framework_v1_profile | 99.590% | 84.423% | 91.382% | 15.229% | 72.430% |
| risk_controlled_hybrid | 99.581% | 89.330% | 94.177% | 10.294% | 73.974% |

### 5.2 Linkable end-to-end

在“真值作者存在于 history”的 35,787 条 test mention 上评估，候选生成漏召也计入：

| 方法 | Precision | Recall | F1 | UNKNOWN |
|---|---:|---:|---:|---:|
| name_most_frequent | 93.539% | 92.729% | 93.133% | 0.866% |
| istina_hypergraph_proxy | 97.569% | 96.661% | 97.113% | 0.931% |
| framework_v1_profile | 99.550% | 83.463% | 90.800% | 16.159% |
| risk_controlled_hybrid | 99.543% | 88.314% | 93.593% | 11.281% |

### 5.3 New-author / truth-not-in-history 风险

在 46,548 条“真值作者不在 history”的 test mention 上看误链接风险：

| 方法 | False-link rate | No-prediction rate | False links / N |
|---|---:|---:|---:|
| name_most_frequent | 11.425% | 88.575% | 5,318 / 46,548 |
| istina_hypergraph_proxy | 11.371% | 88.629% | 5,293 / 46,548 |
| framework_v1_profile | 0.455% | 99.545% | 212 / 46,548 |
| risk_controlled_hybrid | 0.715% | 99.285% | 333 / 46,548 |

## 6. 导师 DOI ORCID 数据结果

数据规模：

- history mentions：4,118
- history authors：3,658
- test mentions：15,062
- truth-in-history test mentions：2,333
- candidate-covered mentions：2,278
- candidate coverage vs truth-in-history：97.643%

### 6.1 共同候选集评分

| 方法 | Precision | Recall | F1 | UNKNOWN | Paper exact |
|---|---:|---:|---:|---:|---:|
| name_most_frequent | 99.254% | 99.254% | 99.254% | 0.000% | 97.302% |
| istina_hypergraph_proxy | 99.561% | 99.517% | 99.539% | 0.044% | 98.254% |
| framework_v1_profile | 100.000% | 79.807% | 88.770% | 20.193% | 64.444% |
| risk_controlled_hybrid | 100.000% | 91.572% | 95.600% | 8.428% | 74.127% |

### 6.2 Linkable end-to-end

| 方法 | Precision | Recall | F1 | UNKNOWN |
|---|---:|---:|---:|---:|
| name_most_frequent | 99.167% | 96.914% | 98.027% | 2.272% |
| istina_hypergraph_proxy | 99.473% | 97.171% | 98.309% | 2.315% |
| framework_v1_profile | 99.890% | 77.925% | 87.551% | 21.989% |
| risk_controlled_hybrid | 99.904% | 89.413% | 94.368% | 10.502% |

### 6.3 New-author / truth-not-in-history 风险

| 方法 | False-link rate | No-prediction rate | False links / N |
|---|---:|---:|---:|
| name_most_frequent | 2.545% | 97.455% | 324 / 12,729 |
| istina_hypergraph_proxy | 2.530% | 97.470% | 322 / 12,729 |
| framework_v1_profile | 0.244% | 99.756% | 31 / 12,729 |
| risk_controlled_hybrid | 0.259% | 99.741% | 33 / 12,729 |

## 7. Hard-case 分组结果

这组统计用于回答“同名、initial、中文拼音、新作者边界样本”是否真实改善。`risk_controlled_hybrid` 采用论文级组合优化后，进一步扫测了 0.5 / 1.0 / 1.25 / 1.5 / 1.75 / 2.0 / 2.5 / 3.0 / 3.5 / 4.0。扫测结果保存在 `results/article2_hybrid_threshold_sweep_20260629.json`。0.5 在 Crossref 上未通过生产门槛；1.0 虽然 F1 最高，但 precision 距 99.5% 门槛过近。最终采用 1.25 作为召回与风险的生产折中点。

### 7.1 Crossref ORCID hard cases

Linkable 场景中，hybrid 的主要价值是用强历史合著图恢复 framework 输出 UNKNOWN 的样本，同时保持接近 99.5% 的 precision。

| Case | N | ISTINA proxy Recall / Wrong | framework_v1 Precision / Recall / Wrong / UNKNOWN | hybrid Precision / Recall / Wrong / UNKNOWN |
|---|---:|---:|---:|---:|
| ambiguous_candidates | 5,552 | 85.303% / 816 | 96.913% / 72.370% / 128 / 25.324% | 96.794% / 75.054% / 138 / 22.460% |
| exact_name_ambiguous | 1,852 | 86.447% / 251 | 92.221% / 71.058% / 111 / 22.948% | 92.366% / 72.516% / 111 / 21.490% |
| initial_only_signature | 5,785 | 96.802% / 154 | 99.446% / 74.434% / 24 / 25.151% | 99.410% / 87.347% / 30 / 12.135% |
| chinese_like_signature | 10,860 | 93.085% / 647 | 99.353% / 73.564% / 52 / 25.958% | 99.314% / 74.687% / 56 / 24.797% |
| framework_unknown_graph_supported | 1,746 | 99.427% / 10 | 0.000% / 0.000% / 0 / 100.000% | 99.427% / 99.427% / 10 / 0.000% |

New-author 场景中，framework_v1 最保守，hybrid 为了提高 linkable 召回会增加少量 false-link，但仍显著低于无风险控制的 ISTINA proxy。

| Case | N | ISTINA proxy false-link | framework_v1 false-link | hybrid false-link |
|---|---:|---:|---:|---:|
| new_author_with_candidates | 5,318 | 99.530% | 3.986% / 212 | 6.262% / 333 |
| ambiguous_candidates | 2,394 | 99.833% | 2.339% / 56 | 5.514% / 132 |
| exact_name_ambiguous | 538 | 100.000% | 3.346% / 18 | 5.762% / 31 |
| initial_only_signature | 10,705 | 6.782% | 0.187% / 20 | 0.710% / 76 |
| chinese_like_signature | 10,822 | 39.004% | 0.767% / 83 | 1.321% / 143 |

### 7.2 导师 DOI ORCID hard cases

| Case | N | ISTINA proxy Recall / Wrong | framework_v1 Precision / Recall / Wrong / UNKNOWN | hybrid Precision / Recall / Wrong / UNKNOWN |
|---|---:|---:|---:|---:|
| ambiguous_candidates | 77 | 87.013% / 10 | 100.000% / 75.325% / 0 / 24.675% | 100.000% / 79.221% / 0 / 20.779% |
| exact_name_ambiguous | 18 | 50.000% / 9 | 100.000% / 38.889% / 0 / 61.111% | 100.000% / 38.889% / 0 / 61.111% |
| initial_only_signature | 465 | 99.355% / 1 | 99.742% / 83.226% / 1 / 16.559% | 99.769% / 92.903% / 1 / 6.882% |
| chinese_like_signature | 173 | 92.486% / 9 | 100.000% / 61.850% / 0 / 38.150% | 100.000% / 67.630% / 0 / 32.370% |
| framework_unknown_graph_supported | 176 | 100.000% / 0 | 0.000% / 0.000% / 0 / 100.000% | 100.000% / 100.000% / 0 / 0.000% |

| Case | N | ISTINA proxy false-link | framework_v1 false-link | hybrid false-link |
|---|---:|---:|---:|---:|
| new_author_with_candidates | 324 | 99.383% | 9.568% / 31 | 10.185% / 33 |
| ambiguous_candidates | 45 | 100.000% | 4.444% / 2 | 4.444% / 2 |
| exact_name_ambiguous | 1 | 100.000% | 0.000% / 0 | 0.000% / 0 |
| initial_only_signature | 3,133 | 3.511% | 0.447% / 14 | 0.479% / 15 |
| chinese_like_signature | 1,688 | 7.583% | 0.237% / 4 | 0.237% / 4 |

结论：hard-case 结果支持文章二的定位，但不支持“完全自动替代人工审核”。hybrid 可以作为 LINK / NEW / UNKNOWN 三分决策层；其中 `framework_unknown_graph_supported` 适合自动补链，`new_author_with_candidates` 和“真实新作者但图支持强”的边界样本必须保留人工审核或更高层生产特征（机构 ID、邮箱、主题、期刊、完整共著图）再判断。

## 8. 判断

这组实验支持一个更稳的文章二定位：

1. 旧 ISTINA 超图思想在 linkable 场景更强，尤其是整篇论文作者组合归属。
2. 当前 `framework_v1` 不应被写成“替代旧算法”的主张。
3. 当前 `framework_v1` 的价值在风险控制：它显著降低 new-author / truth-not-in-history 场景的误链接。
4. `risk_controlled_hybrid` 是当前最适合作为文章二扩展点的三分决策层：它牺牲少量 NEW 场景保守性，换取明显更高的 linkable 召回；在阈值 1.25 和论文级组合优化下，new-author false-link 在 Crossref 上为 0.715%，在导师 DOI 数据上为 0.259%。
5. 文章二更合理的方向是：

   ```text
   旧 ISTINA 作者消歧算法复现与比较
   + 统一 benchmark
   + 风险导向的三分决策扩展（LINK / NEW / UNKNOWN）
   + 后续可选图特征或 GNN
   ```

## 9. 下一步

1. 如果能获得真实 ISTINA 导出的 `worker_id / article_id / author_position / aliases` 历史数据，应直接复现旧 C++ 算法或实现更严格的等价 Python 版本。
2. 增加 hard-case 子集：
   - 完全同名；
   - 同姓同 initials；
   - 同机构同名；
   - 中文拼音姓名；
   - 新作者 NEW cases。
3. 在 `istina_hypergraph_proxy` 输出后增加三分决策层，测试是否能保留旧算法召回，同时把 new-author false-link 降到接近 `framework_v1`。
4. GNN 不作为当前主线，除非它能在旧超图/三分决策 baseline 之上稳定提升。
