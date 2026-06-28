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
  2. `istina_hypergraph_proxy`：按当前论文其他署名候选集中的历史合著关系打分；
  3. `framework_v1_profile`：用当前 `framework_v1 balanced` pairwise 规则做 profile linking；不能高置信判断时输出 UNKNOWN。
  4. `risk_controlled_hybrid`：先接受 `framework_v1_profile` 的高置信结果；若 framework 输出 UNKNOWN，则仅在 ISTINA hypergraph proxy 的历史合著支持分数 `>= 1.0` 时接受其 LINK，否则输出 UNKNOWN。

结果文件：

```text
results/article2_istina_proxy_online_crossref_orcid_20260628.json
results/article2_istina_proxy_online_advisor_orcid_20260628.json
```

复现实验命令：

```powershell
python experiments\evaluate_istina_hypergraph_proxy.py --dataset "C:\istina\materia 材料\测试表单\crossref_authors.json" --output results\article2_istina_proxy_online_crossref_orcid_20260628.json --cutoff-year 2021 --max-profile-mentions 30 --hypergraph-support-threshold 1.0

python experiments\evaluate_istina_hypergraph_proxy.py --dataset "runs\advisor_doi_20260507\advisor_doi_crossref_api_authors.json" --output results\article2_istina_proxy_online_advisor_orcid_20260628.json --cutoff-year 2021 --max-profile-mentions 30 --hypergraph-support-threshold 1.0
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
| istina_hypergraph_proxy | 97.552% | 97.552% | 97.552% | 0.000% | 93.345% |
| framework_v1_profile | 99.590% | 84.423% | 91.382% | 15.229% | 72.430% |
| risk_controlled_hybrid | 99.545% | 89.672% | 94.351% | 9.918% | 74.528% |

### 5.2 Linkable end-to-end

在“真值作者存在于 history”的 35,787 条 test mention 上评估，候选生成漏召也计入：

| 方法 | Precision | Recall | F1 | UNKNOWN |
|---|---:|---:|---:|---:|
| name_most_frequent | 93.539% | 92.729% | 93.133% | 0.866% |
| istina_hypergraph_proxy | 97.286% | 96.443% | 96.862% | 0.866% |
| framework_v1_profile | 99.550% | 83.463% | 90.800% | 16.159% |
| risk_controlled_hybrid | 99.508% | 88.652% | 93.767% | 10.909% |

### 5.3 New-author / truth-not-in-history 风险

在 46,548 条“真值作者不在 history”的 test mention 上看误链接风险：

| 方法 | False-link rate | No-prediction rate | False links / N |
|---|---:|---:|---:|
| name_most_frequent | 11.425% | 88.575% | 5,318 / 46,548 |
| istina_hypergraph_proxy | 11.425% | 88.575% | 5,318 / 46,548 |
| framework_v1_profile | 0.455% | 99.545% | 212 / 46,548 |
| risk_controlled_hybrid | 0.975% | 99.025% | 454 / 46,548 |

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
| istina_hypergraph_proxy | 99.429% | 99.429% | 99.429% | 0.000% | 97.937% |
| framework_v1_profile | 100.000% | 79.807% | 88.770% | 20.193% | 64.444% |
| risk_controlled_hybrid | 100.000% | 91.923% | 95.791% | 8.077% | 74.921% |

### 6.2 Linkable end-to-end

| 方法 | Precision | Recall | F1 | UNKNOWN |
|---|---:|---:|---:|---:|
| name_most_frequent | 99.167% | 96.914% | 98.027% | 2.272% |
| istina_hypergraph_proxy | 99.342% | 97.085% | 98.201% | 2.272% |
| framework_v1_profile | 99.890% | 77.925% | 87.551% | 21.989% |
| risk_controlled_hybrid | 99.905% | 89.756% | 94.559% | 10.159% |

### 6.3 New-author / truth-not-in-history 风险

| 方法 | False-link rate | No-prediction rate | False links / N |
|---|---:|---:|---:|
| name_most_frequent | 2.545% | 97.455% | 324 / 12,729 |
| istina_hypergraph_proxy | 2.545% | 97.455% | 324 / 12,729 |
| framework_v1_profile | 0.244% | 99.756% | 31 / 12,729 |
| risk_controlled_hybrid | 0.275% | 99.725% | 35 / 12,729 |

## 7. 判断

这组实验支持一个更稳的文章二定位：

1. 旧 ISTINA 超图思想在 linkable 场景更强，尤其是整篇论文作者组合归属。
2. 当前 `framework_v1` 不应被写成“替代旧算法”的主张。
3. 当前 `framework_v1` 的价值在风险控制：它显著降低 new-author / truth-not-in-history 场景的误链接。
4. `risk_controlled_hybrid` 是当前最适合作为文章二扩展点的三分决策层：它牺牲少量 NEW 场景保守性，换取明显更高的 linkable 召回，同时仍把 new-author false-link 控制在约 1% 或以下。
5. 文章二更合理的方向是：

   ```text
   旧 ISTINA 作者消歧算法复现与比较
   + 统一 benchmark
   + 风险导向的三分决策扩展（LINK / NEW / UNKNOWN）
   + 后续可选图特征或 GNN
   ```

## 8. 下一步

1. 如果能获得真实 ISTINA 导出的 `worker_id / article_id / author_position / aliases` 历史数据，应直接复现旧 C++ 算法或实现更严格的等价 Python 版本。
2. 增加 hard-case 子集：
   - 完全同名；
   - 同姓同 initials；
   - 同机构同名；
   - 中文拼音姓名；
   - 新作者 NEW cases。
3. 在 `istina_hypergraph_proxy` 输出后增加三分决策层，测试是否能保留旧算法召回，同时把 new-author false-link 降到接近 `framework_v1`。
4. GNN 不作为当前主线，除非它能在旧超图/三分决策 baseline 之上稳定提升。
