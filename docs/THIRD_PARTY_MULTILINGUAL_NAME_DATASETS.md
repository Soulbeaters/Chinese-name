# 第三方多语言姓名数据源调研与引用清单

调研日期：2026-06-25  
适用项目：项目一 / 中文姓名输入规范化与姓氏顺序验证

## 1. 目的

本文档整理可用于补充当前 Crossref/ISTINA 实验的第三方姓名数据，重点回答：

1. 数据是否包含结构化的 given name、family name、姓名变体或原文字母形式；
2. 是否能够支持非中文姓名识别、姓名顺序判断或姓氏词典扩展；
3. 下载方式、格式、许可和推荐引用是什么；
4. 数据与 Crossref、ORCID、OpenAlex 等来源之间是否可能重叠；
5. 如何构建无作者、无姓名对、无 DOI 泄漏的第三方测试集。

## 2. 结论摘要

| 数据源 | 最适合的用途 | 结构化 given/family | 原文/多语标签 | 许可 | 独立性评价 | 优先级 |
|---|---|---:|---:|---|---|---:|
| ORCID Public Data File | 研究人员姓名、其他姓名、国家和机构上下文 | 是 | 部分，依赖用户填写 | CC0 1.0 | 人员层面较独立，但 works 可能与 Crossref 重叠 | 1 |
| Wikidata Dumps | 原文字母姓名、多语言 labels/aliases、国籍和语言上下文 | 部分，需要 P735/P734 等属性 | 强 | 结构化数据 CC0 | 与当前语料独立性较好，但人工编辑噪声较大 | 1 |
| JMnedict | 日文姓氏、名字、汉字形式和读法 | 类型级区分 | 强（日文汉字/假名） | CC BY-SA 4.0，须署名及遵守更新条件 | 独立词典资源 | 1 |
| OpenAlex Snapshot | 大规模作者、姓名变体、ORCID、论文和机构上下文 | 不保证稳定拆分 | 有姓名变体，原文覆盖不均 | CC0 | 汇聚 Crossref/ORCID 等来源，不能视为完全独立 | 2 |
| US Census 2010 Surnames | 英文/美国环境姓氏频率、排名和覆盖验证 | 仅姓氏 | 弱 | 官方政府数据；页面未单列专门数据许可 | 独立的聚合姓氏表，但地域偏差明显 | 2 |

推荐组合：

- **第三方测试集主体**：ORCID + Wikidata，按 ORCID/QID 去重，并排除当前语料中的作者、DOI 和姓名对；
- **日文专项词典与压力测试**：JMnedict；
- **国际出版上下文和作者变体补充**：OpenAlex，但必须排除 Crossref/ORCID 重叠；
- **英语/美国姓氏频率基线**：US Census，只使用 surname、count、rank，不把 race/ethnicity 比例作为姓名顺序预测特征。

## 3. ORCID Public Data File

### 3.1 官方来源

- [Working with the Public Data File](https://info.orcid.org/documentation/integration-guide/working-with-bulk-data/)
- [ORCID Record Schema](https://info.orcid.org/documentation/integration-guide/orcid-record/)
- [ORCID Public Data File 2025](https://doi.org/10.23640/07243.30375589)
- [Public Data File Use Policy](https://info.orcid.org/public-data-file-use-policy/)

### 3.2 已核对信息

- ORCID 每年发布一次公共数据文件；2025 文件是截至 **2025-10-01** 的公共注册记录快照。
- 2025 数据集 DOI 为 `10.23640/07243.30375589`。
- 数据采用 XML；2025 分为一个 summaries 文件和 11 个 activities 文件。
- 记录模式中与本项目直接相关的字段包括：
  - `given-names`；
  - `family-name`；
  - `credit-name`；
  - 可重复的 `other names`；
  - 国家/地区；
  - education、employment、works 和外部标识符。
- 只包含公开信息。family name、其他姓名、国家和活动数据可能因隐私设置或用户未填写而缺失。
- 2025 数据文件以 **CC0 1.0 Universal** 发布。

### 3.3 对项目的价值

- 结构化 given/family 字段可以训练或验证“姓名角色概率”，但不得同时作为模型输入和同一记录的评价标签。
- `credit-name` 与 `other names` 可用于构建同一人的姓名变体组。
- ORCID iD 可用于按人隔离 train/dev/test，避免同一作者跨集合。
- 国家、机构和 works 可用于构建文化/出版上下文，但应作为可选证据，不应替代姓名本身。

### 3.4 风险

- 数据是用户自报和机构写入的混合体，拆分字段可能仍有错误。
- works 中的 DOI 与当前 Crossref 数据可能大量重叠。
- ORCID 记录不一定提供一个可靠的“原始显示顺序”。若要评价顺序检测，需要额外保存 observed full name，并与结构化字段对齐。

## 4. OpenAlex Snapshot

### 4.1 官方来源

- [OpenAlex Developers Overview](https://developers.openalex.org/)
- [Data Downloads](https://developers.openalex.org/download/overview)
- [Snapshot Data Format](https://developers.openalex.org/download/snapshot-format)
- [Authors Schema](https://developers.openalex.org/api-reference/authors)
- [OpenAlex paper, arXiv:2205.01833](https://doi.org/10.48550/arXiv.2205.01833)

### 4.2 已核对信息

- OpenAlex 官方说明完整数据集可用，并以 **CC0** 开放。
- 快照按实体组织，例如 `/data/authors/` 和 `/data/works/`，使用 `updated_date` 分区和 manifest 文件。
- Author 实体/接口可提供：
  - `display_name`；
  - `display_name_alternatives`；
  - `raw_author_names`、`full_name`；
  - ORCID；
  - works count；
  - affiliations、last known institutions 及 country code；
  - works API URL。

### 4.3 对项目的价值

- `raw_author_names` 和 `display_name_alternatives` 可用于测试姓名变体和不同来源写法。
- ORCID 可用于与 ORCID Public Data File 对齐，形成多来源一致性标签。
- works/institutions 可用于真实 publication/person consistency 测试，而不只使用合成的统一顺序。
- 适合检查同一作者在不同出版商中的顺序、缩写、连字符和变音符变化。

### 4.4 风险

- OpenAlex 聚合 Crossref、ORCID 等来源，因此**不能直接称为完全独立的第三方金标准**。
- OpenAlex 的 author disambiguation 和姓名标准化本身可能出错。
- 用作最终测试集时必须排除：
  - 当前训练集出现过的 DOI；
  - 当前训练集出现过的 ORCID/OpenAlex author ID；
  - 当前训练集出现过的规范化姓名对。

## 5. Wikidata Dumps

### 5.1 官方来源

- [Wikidata Database Download](https://www.wikidata.org/wiki/Wikidata:Database_download)
- [Wikidata JSON/RDF dump directory](https://dumps.wikimedia.org/wikidatawiki/entities/)
- [Wikidata paper](https://doi.org/10.1145/2629489)

### 5.2 已核对信息

- 官方推荐 JSON dump；完整实体 dump 通常按周创建。
- 每个实体对象可逐行解析，适合流式处理而不必一次载入内存。
- 结构化主命名空间数据采用 **CC0**；其他命名空间文字可能采用 CC BY-SA。
- 可用于姓名研究的主要内容：
  - 多语言 labels 和 aliases；
  - `P735` given name；
  - `P734` family name；
  - `P1559` name in native language；
  - `P1477` birth name；
  - `P27` country of citizenship；
  - `P1412` languages spoken, written or signed。

### 5.3 推荐抽取条件

仅保留：

- `instance of (P31) = human (Q5)`；
- 至少具有 label/alias；
- 优先要求同时具有 P735 和 P734；
- 若用于原文字母/转写实验，要求至少存在两种语言标签，或存在 P1559；
- 保存 QID、每个 label 的 language tag、aliases 及属性来源。

### 5.4 风险

- Wikidata 是协作编辑知识库，不是专门的姓名金标准。
- P735/P734/P1559 完整性随国家、时代和人物知名度变化。
- 著名人物分布会导致职业、地区和历史时期偏差。
- 标签顺序是语言相关的，不应把英文 label 顺序直接当作所有语言的真实姓名顺序。

## 6. JMnedict / ENAMDICT

### 6.1 官方来源

- [JMnedict/ENAMDICT Documentation](https://www.edrdg.org/enamdict/enamdict_doc.html)
- [EDRDG Dictionary Licence](https://www.edrdg.org/edrdg/licence.html)

### 6.2 已核对信息

- JMnedict 是 UTF-8 XML 格式的 Japanese Multilingual Named Entity Dictionary。
- 数据包含日文专名，包括姓氏、名字、完整人名、地名、公司名和其他专名。
- 文档列出的主要分类及大致规模包括：
  - surname (`s`)：约 138,500；
  - 未分类 person name (`u`)：约 139,000；
  - given name (`g`)：约 64,600；
  - female given name (`f`)：约 106,300；
  - male given name (`m`)：约 14,500；
  - full person name (`h`)：约 30,500。
- XML 文件可从官方 EDRDG 下载入口获取。
- EDRDG 当前通用字典许可为 **Creative Commons Attribution-ShareAlike 4.0**，要求署名、保留许可信息，并要求使用方定期更新数据。

### 6.3 对项目的价值

- 可把日文汉字/假名姓名与 reading 对齐，再生成受控的拉丁转写。
- 能区分 surname、given name 和 full person name，可补充当前手工日文姓氏列表。
- 适合专门评价 `Ito`, `Kawamura`, `Yamaguchi`, `Ouchi` 等日文罗马字姓名。

### 6.4 许可注意

- 如果将大量 JMnedict 条目或其派生词典随项目重新分发，应保留 EDRDG 署名、许可链接和 CC BY-SA 条件。
- 在把派生词典并入当前代码仓库前，应单独确认 ShareAlike 对派生数据文件的影响。
- 比较稳妥的第一阶段是：将 JMnedict 用作外部评价集或离线审计资源，不直接复制整个词典进入发布包。

## 7. US Census 2010 Surname Data

### 7.1 官方来源

- [Frequently Occurring Surnames from the 2010 Census](https://www.census.gov/topics/population/genealogy/data/2010_surnames.html)
- [Complete surname ZIP/CSV](https://www2.census.gov/topics/genealogy/2010surnames/names.zip)
- [Technical documentation PDF](https://www2.census.gov/topics/genealogy/2010surnames/surnames.pdf)

### 7.2 已核对信息

- 数据包含 2010 Census 中出现至少 100 次的姓氏。
- 完整列表包含 **162,253** 个姓氏，另有 top-1000 Excel 文件。
- 数据是聚合统计，不包含具体个人信息。
- 可用字段包括 surname、rank、count/proportion，以及人口统计比例。
- 技术文档说明数据处理中删除了部分标点和空格，例如复合姓和带撇号姓可能被压缩。这一点会影响姓名标准化实验。

### 7.3 对项目的价值与限制

- 适合作为英语/美国环境下姓氏频率和覆盖率的独立基线。
- 可验证当前 Western surname dictionary 是否漏掉高频姓氏。
- 不能提供 given name，也不能单独提供姓名顺序标签。
- 数据具有美国人口结构偏差，不应当作全球姓氏分布。
- 建议只使用 surname、count、rank。为避免公平性和代理变量风险，不建议把 race/ethnicity 比例用于自动姓名顺序判断。
- 官方页面未单列专门的数据许可文本；公开发布派生文件前，应再次核对 U.S. Census Bureau 的使用条款和署名要求。

## 8. 推荐的第三方数据集结构

最终统一表建议至少包含：

| 字段 | 说明 |
|---|---|
| `source` | ORCID / OpenAlex / Wikidata / JMnedict / Census |
| `source_person_id` | ORCID iD、OpenAlex author ID、Wikidata QID 等 |
| `given_name` | 结构化 given name；没有时为空 |
| `family_name` | 结构化 family name；没有时为空 |
| `observed_full_name` | 来源中真实显示的姓名字符串，不是人工拼接字符串 |
| `native_name` | 原文字母形式 |
| `romanized_name` | 来源给出的或按明确标准生成的转写 |
| `aliases` | 姓名变体列表 |
| `language_tag` | BCP 47 或来源语言标签 |
| `country_code` | ISO 3166 国家/地区代码，允许为空 |
| `publication_id` | DOI/OpenAlex work ID；词典数据为空 |
| `expected_order` | given_first / family_first / unknown；必须说明标注方法 |
| `label_provenance` | structured_fields / manual / aligned_alias / dictionary |
| `license` | CC0、CC BY-SA 等 |
| `retrieved_at` | 数据获取日期 |

## 9. 无泄漏评估协议

第三方数据不能直接混入当前 301k 数据后再报告同一数据上的提升。推荐：

1. 规范化后计算 `given_name + family_name` 的姓名对哈希；
2. 排除当前训练/开发数据出现过的姓名对；
3. 按 ORCID/OpenAlex/QID 排除同一人跨集合；
4. 按 DOI/作品 ID 排除同一出版物跨集合；
5. OpenAlex 与 Crossref 必须额外按 DOI 去重；
6. 至少保留一个完全冻结、从不参与阈值选择的第三方测试集；
7. 按语言/文化区域分别报告错误和 UNKNOWN，不只报告总体平均；
8. 同时报告：
   - observed full-name order；
   - 合成 given-first/family-first 压力测试；
   - 非中文姓氏子集；
   - 原文字母与拉丁转写子集。

建议的最低分层：中文、日文、韩文、越南文、阿拉伯文、斯拉夫/西里尔文、西欧拉丁文、南亚姓名。每层应尽量获得至少数千条人工或高可靠结构化记录。

## 10. 推荐实施顺序

### 阶段 A：低成本、高价值

1. 下载 JMnedict，建立日文 surname/given/full-name 外部审计表；
2. 下载 US Census 完整姓氏列表，只抽取 surname/count/rank；
3. 下载 ORCID 2025 summaries 文件，先不下载全部 activities；
4. 从 ORCID 抽取公开 given/family/credit/other names、国家和 ORCID iD；
5. 与当前数据按 ORCID、DOI 和姓名对去重。

### 阶段 B：多语原文与上下文

1. 从 Wikidata dump 流式抽取 Q5 人物的 P735/P734/P1559 和多语言 labels/aliases；
2. 从 OpenAlex Authors/Works 提取 raw names、姓名变体、ORCID、机构和作品；
3. 只把与现有训练数据无重叠的部分放入冻结测试集。

### 阶段 C：论文实验

1. 比较 dictionary-only、token-role model、publication consistency 和组合模型；
2. 报告按语言分层的 error/UNKNOWN/coverage；
3. 对模型新增证据做消融实验；
4. 单独报告 OpenAlex 重叠风险和 JMnedict 许可处理；
5. 论文中不把结构化字段泄漏产生的 100% 结果作为算法准确率。

## 11. 可直接用于论文的参考文献

1. ORCID. (2025). *ORCID Public Data File 2025* [Data set]. Figshare. https://doi.org/10.23640/07243.30375589
2. Priem, J., Piwowar, H., & Orr, R. (2022). *OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts*. arXiv:2205.01833. https://doi.org/10.48550/arXiv.2205.01833
3. Vrandečić, D., & Krötzsch, M. (2014). Wikidata: A free collaborative knowledgebase. *Communications of the ACM, 57*(10), 78–85. https://doi.org/10.1145/2629489
4. Electronic Dictionary Research and Development Group. (n.d.). *ENAMDICT/JMnedict documentation*. Retrieved June 25, 2026, from https://www.edrdg.org/enamdict/enamdict_doc.html
5. Electronic Dictionary Research and Development Group. (n.d.). *General dictionary licence statement*. Retrieved June 25, 2026, from https://www.edrdg.org/edrdg/licence.html
6. Comenetz, J. (2016). *Frequently occurring surnames in the 2010 Census*. U.S. Census Bureau. https://www2.census.gov/topics/genealogy/2010surnames/surnames.pdf
7. OpenAlex. (n.d.). *Snapshot data format*. Retrieved June 25, 2026, from https://developers.openalex.org/download/snapshot-format
8. Wikidata contributors. (n.d.). *Wikidata: Database download*. Retrieved June 25, 2026, from https://www.wikidata.org/wiki/Wikidata:Database_download

## 12. BibTeX 草案

```bibtex
@misc{orcid2025public,
  author    = {{ORCID}},
  title     = {ORCID Public Data File 2025},
  year      = {2025},
  howpublished = {Figshare data set},
  doi       = {10.23640/07243.30375589}
}

@article{priem2022openalex,
  author  = {Jason Priem and Heather Piwowar and Richard Orr},
  title   = {OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts},
  journal = {arXiv preprint arXiv:2205.01833},
  year    = {2022},
  doi     = {10.48550/arXiv.2205.01833}
}

@article{vrandecic2014wikidata,
  author  = {Denny Vrande\v{c}i\'{c} and Markus Kr\"{o}tzsch},
  title   = {Wikidata: A Free Collaborative Knowledgebase},
  journal = {Communications of the ACM},
  volume  = {57},
  number  = {10},
  pages   = {78--85},
  year    = {2014},
  doi     = {10.1145/2629489}
}

@misc{edrdg_jmnedict,
  author       = {{Electronic Dictionary Research and Development Group}},
  title        = {ENAMDICT/JMnedict Documentation},
  howpublished = {\url{https://www.edrdg.org/enamdict/enamdict_doc.html}},
  note         = {Accessed 2026-06-25}
}

@techreport{comenetz2016surnames,
  author      = {Joshua Comenetz},
  title       = {Frequently Occurring Surnames in the 2010 Census},
  institution = {U.S. Census Bureau},
  year        = {2016},
  url         = {https://www2.census.gov/topics/genealogy/2010surnames/surnames.pdf}
}
```

## 13. 引用与使用注意

- 论文中应分别引用“数据集本身”和“描述该资源的论文/官方文档”。
- ORCID、OpenAlex 和 Wikidata 可按其 CC0 条款使用，但仍应进行学术署名。
- JMnedict 不是 CC0；复制或发布派生数据时必须遵守 CC BY-SA 4.0 和 EDRDG 署名/更新条件。
- US Census 数据应引用官方数据页和 Comenetz (2016) 技术文档。
- 在论文提交前重新检查所有网页、版本号、访问日期和许可页面；本清单记录的是 2026-06-25 核对到的状态。

## 14. Additional source used in the final optimization: SSA National Names

- Official download: [National baby-name data](https://www.ssa.gov/oact/babynames/names.zip)
- Official file documentation: [Beyond the Top 1000 Names](https://www.ssa.gov/oact/babynames/limits.html)
- Official methodology and qualifications: [Background information for popular names](https://www.ssa.gov/oact/babynames/background.html)
- Download verified on 2026-06-25; SHA-256:
  `CD78E975ED7BB358E018DD62FBE14CED89295E9581C49172CA4EEDCB011B3724`.

The archive contains yearly US first-name counts derived from Social Security
card applications. It is not a global given-name census: names with fewer than
five occurrences in a year are suppressed, spellings are not merged, and the
historical coverage depends on Social Security registration. In this project it
is combined with Census surname counts only as a conservative normalized role
fallback; it is not used as a nationality or ethnicity classifier.

Suggested reference:

> U.S. Social Security Administration. (2026). *National data: Popular baby
> names*. Retrieved June 25, 2026, from
> https://www.ssa.gov/oact/babynames/limits.html
