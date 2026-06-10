# 论文资产索引 / Paper Assets Index

**作者**: Ma Jiaxin
**日期**: 2025-12-20
**项目**: Chinese Name Processing System v8.0
**用途**: 博士论文第2-4章引用文件清单

---

## 目录 / Contents

1. [第二部分：Evidence Chain (301k实验)](#第二部分evidence-chain-301k实验)
2. [第三部分：Ablation Analysis](#第三部分ablation-analysis)
3. [第四部分：ISTINA Pilot](#第四部分istina-pilot)
4. [补充材料 / Supplementary Materials](#补充材料--supplementary-materials)

---

## 第二部分：Evidence Chain (301k实验)

### 统计报告 / Statistical Reports

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_global.tex` | Table 2.1: Confidence Intervals | 主要质量指标表格 | LaTeX (booktabs) |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_global.md` | Section 2.2: Accuracy Analysis | Markdown参考 | Markdown |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_global.json` | - | 机器可读数据 | JSON |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_end_to_end.tex` | Table 2.2: End-to-End Metrics | 端到端指标 | LaTeX |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_conditional.tex` | Table 2.3: Conditional Metrics | 条件指标 | LaTeX |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_coverage.tex` | Table 2.4: Coverage Metrics | 覆盖率指标 | LaTeX |

**关键特性**:
- Unknown Rate显示4位小数（A1修复）
- 包含count字段便于解读小比例
- Wilson 95% CI置信区间
- Crossref raw-name sanity benchmark: 301,586 input records; 301,559
  simple proxy-labeled rows. This proxy label is for reproducibility checks
  only and must not be described as manual ground truth.

---

## 第三部分：Ablation Analysis

### 触发子集分析 / Triggered Subsets Analysis

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/triggered_subsets/ablation_triggered_subsets.md` | Section 3.1: Module Impact Analysis | 模块影响分析叙述 | Markdown |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/triggered_subsets/ablation_triggered_subsets.json` | - | 机器可读数据 | JSON |

**关键特性**:
- 数据驱动叙述（A2修复）
- 子集规模和占比
- McNemar显著性检验
- baseline vs ablation accuracy对比

### 模块覆盖率 / Module Coverage

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/events/baseline/module_coverage.md` | Section 3.2: Module Coverage | 模块覆盖率分析 | Markdown |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/events/baseline/module_coverage.json` | - | 机器可读数据 | JSON |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/events/baseline/reason_counts.csv` | Figure 3.1: Reason Distribution | 原因分布柱状图数据 | CSV |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/events/baseline/score_margin_stats.json` | Figure 3.2: Score Margin Distribution | 分数边界分布 | JSON |

**关键特性**:
- 统一三层定义（A4修复）：evaluated/fired/effective
- 明确effective由baseline vs ablation对比得出
- 不依赖counterfactual推理

### 样本案例 / Sanity Samples

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/sanity_samples/ablation_sanity_samples.jsonl` | Appendix A: Sample Cases | 案例分析 | JSONL |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/sanity_samples/ablation_sanity_samples.md` | Appendix A: Sample Analysis | 样本分析叙述 | Markdown |

**关键特性**:
- 修复抽样逻辑（A3）：优先effective子集
- 每个模块25个样本
- 包含baseline/ablation/ground_truth对比

---

## 第四部分：ISTINA Pilot

### 主要报告 / Main Reports

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/istina_pilot_10k_final/reports/istina_pilot_summary.md` | Section 4.1: ISTINA Integration | Pilot总结报告 | Markdown |
| `runs/istina_pilot_10k_final/dataset_card.md` | Section 4.2: Data Description | 数据集描述 | Markdown |

### LaTeX表格 / LaTeX Tables

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/istina_pilot_10k_final/tables/istina_pilot_quality.tex` | Table 4.1: Quality Metrics | 质量指标表 | LaTeX (booktabs) |
| `runs/istina_pilot_10k_final/tables/istina_pilot_perf.tex` | Table 4.2: Performance Benchmark | 性能基准表 | LaTeX (booktabs) |

**表格内容**:
- **Quality**: Accuracy, Unknown Rate, Error Rate (with CI)
- **Performance**: Throughput (names/sec), Latency percentiles (p50/p95/p99)

### 脱敏日志样本 / Redacted Log Samples

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/istina_pilot_10k_final/logs/istina_batch_redacted_200.jsonl` | Supplementary Material S1 | 脱敏决策日志样本 | JSONL |
| `runs/istina_pilot_10k_final/logs/istina_batch_redaction_policy.md` | Data Availability Statement | 脱敏策略文档 | Markdown |
| `runs/istina_pilot_10k_final/logs/istina_batch_redaction_policy.json` | - | 机器可读策略 | JSON |

**脱敏规则**:
- **input_tokens**: 完全不写入decision_events.jsonl（designed to align with GDPR Art. 25/32 principles; enhances data security）
- **record_id**: 使用SHA-256单向哈希（不可逆，确保匿名性）
- **保留字段**: reasons_topk, fired_modules, effective_modules
- **scores/score_margin**: 允许为null（诚实口径，算法不提供真实分布时设为null）
- 设计遵循GDPR Art. 25/32和152-FZ数据最小化原则（最终合规性以机构审查为准）

### 性能基准 / Performance Benchmark

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/istina_pilot_10k_final/performance_benchmark.json` | Table 4.2, Section 4.3 | 完整性能基准数据 | JSON |

**包含指标**:
- throughput_names_per_sec
- latency_ms (avg/p50/p95/p99/min/max)
- total_time_sec
- git_commit_short
- machine_info

### 图表素材 / Figures

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `figs/istina_integration.puml` | Figure 4.1: Integration Architecture | ISTINA集成架构图 | PlantUML |
| `figs/smbu_pipeline.puml` | Figure 4.2: Batch Processing Pipeline | 批处理流程图 | PlantUML |

**生成PNG**:
```bash
# 使用PlantUML转换为PNG
plantuml figs/istina_integration.puml
plantuml figs/smbu_pipeline.puml
```

**输出**:
- `figs/istina_integration.png`
- `figs/smbu_pipeline.png`

---

## 补充材料 / Supplementary Materials

### 复现性元数据 / Reproducibility Metadata

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/run_manifest.json` | Appendix B: Reproducibility | 完整运行元数据 | JSON |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/repro/dirty_patch.diff` | Appendix B | Git diff patch（若is_dirty=true） | Diff |
| `runs/evidence_chain_301k_P0_P5_FINAL_V2/env.txt` | Appendix B | 环境依赖 | Text |

**run_manifest包含**:
- git_commit_sha & is_dirty status
- random_seed & config_hash
- dataset_sha256
- n_records_total & n_records_labeled
- python_version & platform
- timestamp_utc

### 决策事件日志 / Decision Event Logs

| 文件路径 | 论文引用位置 | 用途 | 格式 |
|---------|------------|------|------|
| `runs/istina_pilot_10k_final/events/baseline/decision_events.jsonl` | Supplementary Material S2 | 完整决策链（无raw tokens） | JSONL |
| `runs/istina_pilot_10k_final/events/baseline/module_coverage.json` | Section 4.4 | 模块覆盖率统计 | JSON |

**注意**: decision_events.jsonl **不包含** input_tokens字段（A2要求）

---

## 快速引用指南 / Quick Reference Guide

### 论文各章节对应文件 / Chapter-File Mapping

#### Chapter 2: Method Validation (Evidence Chain)

| 章节 | 表/图 | 文件 |
|-----|------|------|
| 2.1 | Table 2.1 | `statistics/stats_ci_global.tex` |
| 2.2 | Figure 2.1 | `events/baseline/reason_counts.csv` → bar chart |
| 2.3 | - | `statistics/stats_ci_end_to_end.tex` |

#### Chapter 3: Ablation Analysis

| 章节 | 表/图 | 文件 |
|-----|------|------|
| 3.1 | - | `triggered_subsets/ablation_triggered_subsets.md` |
| 3.2 | - | `events/baseline/module_coverage.md` |
| 3.3 | Table 3.1 | `triggered_subsets/ablation_triggered_subsets.json` → format to tex |
| Appendix A | - | `sanity_samples/ablation_sanity_samples.md` |

#### Chapter 4: Practice Application (ISTINA Pilot)

| 章节 | 表/图 | 文件 |
|-----|------|------|
| 4.1 | - | `reports/istina_pilot_summary.md` |
| 4.2 | Table 4.1 | `tables/istina_pilot_quality.tex` |
| 4.3 | Table 4.2 | `tables/istina_pilot_perf.tex` |
| 4.4 | Figure 4.1 | `figs/istina_integration.png` |
| 4.5 | Figure 4.2 | `figs/smbu_pipeline.png` |

### Data Availability Statement建议文本 / Suggested Data Availability Text

```
The experiment results, including quality metrics, performance benchmarks, and
module coverage statistics, are available in the runs/ directory. To protect
privacy, we provide:

1. A 200-line redacted sample of decision logs (istina_batch_redacted_200.jsonl)
   with input names replaced by SHA-256 hashes and statistical features
2. Complete redaction policy documentation (istina_batch_redaction_policy.md)
3. Run manifests with git commit, seed, and configuration hashes for reproducibility

The redaction process is designed to align with GDPR Article 25 (Data Protection
by Design), Article 32 (Security of Processing), and Russian Federal Law 152-FZ
principles. Final compliance is subject to institutional review.

Full dataset and raw logs are available upon reasonable request to qualified
researchers, subject to data use agreements.
```

---

## 论文引用片段示例 / Paper Citation Examples

### Table 4.1: ISTINA Pilot Quality Metrics

**LaTeX 引用 / LaTeX Citation**:
```latex
\input{runs/istina_pilot_10k_final/tables/istina_pilot_quality.tex}
```

**说明文本示例 / Example Caption Text**:
```
Table 4.1 shows the quality metrics of the Chinese name order identification
algorithm on ISTINA pilot data (N=9,999). The algorithm achieved 62.75%
accuracy with 19.97% unknown rate, indicating a conservative threshold policy
that prefers abstention over incorrect prediction.
```

**正文引用示例 / Example In-Text Reference**:
```
The ISTINA pilot validation (Table 4.1) demonstrates that the algorithm
achieves 62.75% accuracy on real-world Russian academic data, with a
coverage of 80.03% (unknown rate: 19.97%).
```

---

### Table 4.2: ISTINA Pilot Performance

**LaTeX 引用 / LaTeX Citation**:
```latex
\input{runs/istina_pilot_10k_final/tables/istina_pilot_perf.tex}
```

**说明文本示例 / Example Caption Text**:
```
Table 4.2 presents the performance metrics measured on 10,000 ISTINA records.
The algorithm achieves a throughput of 4,055 names/sec with sub-millisecond
latency (P99 < 0.5ms) and zero exceptions, demonstrating production readiness.
All timing measurements use real wall-clock timing (time.perf_counter()).
```

**正文引用示例 / Example In-Text Reference**:
```
Performance benchmarks (Table 4.2) show that the algorithm processes over
4,000 names per second with P99 latency under 0.5ms, meeting production
deployment requirements.
```

---

### Section 4.1: ISTINA Integration Summary

**引用文件 / Reference File**:
`runs/istina_pilot_10k_final/reports/istina_pilot_summary.md`

**正文引用示例 / Example In-Text Reference**:
```
The ISTINA pilot experiment validates the algorithm on 10,000 records from
a production academic information system. The algorithm employs a conservative
threshold policy, achieving 62.75% accuracy while maintaining an unknown rate
of 19.97% to avoid incorrect predictions.
```

---

### Supplementary Material S1: Redacted Decision Logs

**引用文件 / Reference File**:
`runs/istina_pilot_10k_final/logs/istina_batch_redacted_200.jsonl`

**正文引用示例 / Example In-Text Reference**:
```
A redacted sample of 200 decision events is provided in Supplementary
Material S1. All personally identifiable information has been replaced
with one-way SHA-256 hashes, designed to align with GDPR Art. 25/32 and
152-FZ principles. The complete redaction policy is documented in
Supplementary Material S2.
```

---

### Data Availability Statement (完整示例)

```
The ISTINA Pilot dataset consists of 10,000 records extracted from the
ІСТИНА (Intelligent System for Thematic Investigation of Scientific-Metric
Data) information system, a Russian academic database. Due to privacy
requirements, the full dataset requires a data use agreement with the
data steward.

A redacted sample of 200 decision events is provided as Supplementary
Material S1 (runs/istina_pilot_10k_final/logs/istina_batch_redacted_200.jsonl),
with personally identifiable information (PII) removed through one-way
SHA-256 hashing. The redaction policy is documented in Supplementary
Material S2 (runs/istina_pilot_10k_final/logs/istina_batch_redaction_policy.md).

All experimental artifacts, including performance benchmarks (throughput:
4,055 names/sec, latency: <0.5ms P99), decision event logs (without raw
tokens), and statistical reports with 95% confidence intervals, are
available in the replication package at runs/istina_pilot_10k_final/.
Git commit: 0419229, random seed: 42.

For access to the full dataset, please contact the ISTINA data steward.
```

---

## 文件检查清单 / File Checklist

运行以下命令验证所有论文引用文件存在：

```bash
# Evidence Chain (301k)
ls runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_global.{json,md,tex}
ls runs/evidence_chain_301k_P0_P5_FINAL_V2/triggered_subsets/ablation_triggered_subsets.{json,md}
ls runs/evidence_chain_301k_P0_P5_FINAL_V2/events/baseline/module_coverage.{json,md}
ls runs/evidence_chain_301k_P0_P5_FINAL_V2/sanity_samples/ablation_sanity_samples.{jsonl,md}

# ISTINA Pilot (10k)
ls runs/istina_pilot_10k_final/reports/istina_pilot_summary.md
ls runs/istina_pilot_10k_final/tables/istina_pilot_{quality,perf}.tex
ls runs/istina_pilot_10k_final/logs/istina_batch_redacted_200.jsonl
ls runs/istina_pilot_10k_final/logs/istina_batch_redaction_policy.md
ls runs/istina_pilot_10k_final/performance_benchmark.json

# Figures
ls figs/istina_integration.{puml,png}
ls figs/smbu_pipeline.{puml,png}
```

---

## 更新日志 / Changelog

- **2025-12-20**: 初始版本，包含301k和ISTINA pilot完整索引
- **2025-12-20**: 添加Data Availability Statement建议文本
- **2025-12-20**: 添加快速引用指南和文件检查清单
- **2025-12-21**: 更新所有路径为 `istina_pilot_10k_final` (唯一最终包)
- **2025-12-21**: 添加论文引用片段示例 (Table 4.1/4.2, Section 4.1, Supplementary S1)

---

**文档版本**: 1.1 (Final & Locked)
**最后更新**: 2025-12-21
**维护者**: Ma Jiaxin
**状态**: ✅ 可用于论文引用 - Ready for Submission
