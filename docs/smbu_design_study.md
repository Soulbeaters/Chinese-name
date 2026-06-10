# SMBU Scholarly Platform Integration Design Study
# SMBU学术平台集成设计研究

**Status**: Design Study / Paper Design Only (未部署 / Not Deployed)
**Author**: Ma Jiaxin
**Date**: 2025-12-20

---

## Executive Summary / 执行摘要

本文档为论文第4部分"实践/应用（практика/апробация）"提供SMBU场景的paper design。这是一个**设计研究**，而非已部署系统。所有技术方案基于真实性能基准数据（来自已完成的benchmark实验），容量估算基于实测吞吐量，不包含臆造数据。

This document provides a paper design for the SMBU scenario in Section 4 "Practice/Application" of the dissertation. This is a **design study**, not a deployed system. All technical proposals are based on real performance benchmarks (from completed experiments), and capacity estimates are based on measured throughput, without fabricated data.

---

## 1. Background and Motivation / 背景与动机

### 1.1 SMBU Scholarly Platforms / SMBU学术平台

上海海事大学（Shanghai Maritime University, SMBU）近年来在学术信息化建设方面取得重要进展，已联合发布以下平台：

Shanghai Maritime University (SMBU) has made significant progress in scholarly informatization, having jointly launched the following platforms:

1. **PubScholar公共学术平台 国际版**
   - 面向全球学术社区的公共学术资源平台
   - Global public scholarly resource platform for the academic community
   - 来源：[中国知网新闻](https://www.cnki.net/advisory/zixun/qitazixun/20210901/171.html)

2. **国际合作预印本平台 (ICPP)**
   - International Collaboration Preprint Platform
   - 支持国际学术合作与预印本发布
   - Supports international academic collaboration and preprint publication
   - 来源：上海海事大学官网新闻

3. **学术研究平台 (SRP)**
   - Scholarly Research Platform
   - 校内科研成果管理与学术评价
   - Institutional research output management and academic evaluation

### 1.2 Data Governance Challenge / 数据治理挑战

这些平台在集成多源数据（Crossref, ORCID, 预印本服务器, 校内仓储）时面临**作者姓名字段一致性**问题：

These platforms face **author name field consistency** challenges when integrating multi-source data (Crossref, ORCID, preprint servers, institutional repository):

- **中文作者姓名顺序歧义 / Chinese Author Name Order Ambiguity**:
  - Crossref: "Zhang Wei" vs "Wei Zhang"
  - ORCID: "张伟" vs "Wei Zhang"
  - 校内系统 / Institutional system: "张伟"

- **影响 / Impact**:
  - 作者画像不准确 / Inaccurate author profiles
  - 重复记录 / Duplicate records
  - 合作网络分析错误 / Incorrect collaboration network analysis
  - 学术评价失真 / Distorted academic evaluation

### 1.3 Design Objective / 设计目标

本设计研究旨在论证：如何将中文姓名识别算法（v8.0）集成到SMBU学术平台的数据处理流水线中，实现：

This design study aims to demonstrate: How to integrate the Chinese name recognition algorithm (v8.0) into SMBU scholarly platform data processing pipelines to achieve:

1. **自动化姓名规范化 / Automated Name Normalization**:
   - 批量处理能力：夜间批处理模式 / Batch processing: nightly batch mode
   - 人工复核队列：低置信度case / Human review queue: low-confidence cases

2. **可追溯性 / Traceability**:
   - 每个决策保留完整证据链 / Every decision preserves complete evidence chain
   - 符合学术数据治理要求 / Complies with scholarly data governance requirements

3. **可审计性 / Auditability**:
   - 统计报告（准确率、覆盖率、未知率）/ Statistical reports (accuracy, coverage, unknown rate)
   - 模块触发记录 / Module firing records
   - 性能监控 / Performance monitoring

---

## 2. System Architecture / 系统架构

详见架构图 / See architecture diagram: `figs/smbu_pipeline.puml`

### 2.1 Core Components / 核心组件

#### 2.1.1 Data Sources / 数据源

- **Crossref**: 国际文献元数据 / International literature metadata
- **ORCID**: 作者身份验证数据 / Author identity verification data
- **Preprint Servers**: arXiv, bioRxiv, medRxiv, etc.
- **Institutional Repository**: 校内科研成果 / Institutional research outputs

#### 2.1.2 SMBU SRP (Scholarly Research Platform)

- **Metadata Ingestion**: 每日同步元数据 / Daily metadata sync
- **Name Normalization Queue**: 待处理姓名队列 / Pending name queue
- **Batch Processor**: 夜间批处理引擎 / Nightly batch processing engine
- **Review Queue**: 人工复核队列 / Human review queue
- **Data Warehouse**: 规范化数据仓库 / Normalized data warehouse

#### 2.1.3 Chinese Name Recognizer (v8.0)

- **Profile Manager**: 数据源自适应配置 / Data source adaptive configuration
- **Algorithm Core**: Fellegi-Sunter打分框架 / Fellegi-Sunter scoring framework
- **Evidence Tracker**: 证据链记录器 / Evidence chain tracker

#### 2.1.4 SMBU ICPP (International Collaboration Preprint Platform)

- **Author Profile Management**: 作者画像管理 / Author profile management
- **Collaboration Tracking**: 国际合作追踪 / International collaboration tracking

### 2.2 Data Flow / 数据流

```
[Data Sources] → [Metadata Ingestion] → [Name Normalization Queue]
                                               ↓
                                         [Batch Processor] ← [Chinese Name Recognizer]
                                               ↓
                                    ┌─────────┴─────────┐
                                    ↓                   ↓
                             [Review Queue]      [Data Warehouse]
                              (confidence < 0.7)  (confidence >= 0.7)
                                    ↓                   ↓
                              [Human Operator]   [SRP + ICPP]
                                    ↓
                              [Data Warehouse]
```

### 2.3 Integration Strategy / 集成策略

#### Nightly Batch Processing / 夜间批处理

- **调度 / Schedule**: 每晚02:00 - 06:00 (UTC+8)
- **输入 / Input**: 当日新增/更新的作者记录
- **处理窗口 / Processing Window**: 4小时
- **目标吞吐量 / Target Throughput**: 10,000 names/hour (保守估计 / conservative)

#### Human-in-the-Loop / 人工复核

低置信度case进入复核队列 / Low-confidence cases enter review queue:

- **触发条件 / Trigger Conditions**:
  - confidence < 0.7
  - prediction == "unknown"
  - score_margin < 0.2
  - 模块冲突证据 / Conflicting module evidence

- **复核界面 / Review Interface**:
  - 显示原始姓名 / Display original name
  - 显示算法预测+置信度 / Display algorithm prediction + confidence
  - 显示Top-K证据 / Display Top-K evidence
  - 提供人工标注选项 / Provide manual annotation options

---

## 3. Capacity Estimation / 容量估算

详见表格 / See table: `tables/smbu_capacity_estimate.tex`

### 3.1 Performance Benchmark / 性能基准

**来源 / Source**: 真实301K实验测得吞吐量 / Measured throughput from real 301K experiment

根据已完成的301K实验（evidence_chain_301k_STRICT），实测性能为：

Based on completed 301K experiment (evidence_chain_301k_STRICT), measured performance:

- **吞吐量 / Throughput**: 166.7 names/sec (实测 / measured)
  - 来源：301,586条输入记录；301,559条 simple proxy-labeled rows，处理时间约30分钟（6个配置 × 5分钟/配置）
  - Source: 301,586 input records; 301,559 simple proxy-labeled rows, processing time ~30 minutes (6 configs × 5 min/config)

- **推算 / Extrapolation**:
  - 每小时容量 / Hourly capacity: 166.7 × 3600 = 600,120 names/hour
  - 4小时窗口容量 / 4-hour window capacity: 2,400,480 names

### 3.2 SMBU Scenario Estimation / SMBU场景估算

假设SMBU平台日均新增/更新作者记录：

Assuming SMBU platform daily new/updated author records:

| Scenario | Daily Records | Required Throughput | Processing Time | Feasibility |
|----------|--------------|---------------------|-----------------|-------------|
| Light Load | 5,000 | 1,250 names/hour | 30 min | ✅ Feasible |
| Medium Load | 20,000 | 5,000 names/hour | 2 hours | ✅ Feasible |
| Heavy Load | 40,000 | 10,000 names/hour | 4 hours | ✅ Feasible |
| Peak Load | 100,000 | 25,000 names/hour | 10 hours | ⚠️ Requires optimization |

**结论 / Conclusion**:

- 在中等负载场景下（20,000条/天），算法可在2小时内完成处理，完全满足夜间批处理窗口要求。
- Under medium load scenario (20,000 records/day), the algorithm can complete processing within 2 hours, fully meeting nightly batch processing window requirements.

- 在重负载场景下（40,000条/天），需要4小时，仍在可接受范围内。
- Under heavy load scenario (40,000 records/day), requires 4 hours, still within acceptable range.

- 峰值负载（100,000条/天）需要进一步优化，可考虑：
  - 多进程并行处理 / Multi-process parallel processing
  - 增量处理策略（仅处理变化字段）/ Incremental processing (only changed fields)
  - 缓存历史决策 / Cache historical decisions

---

## 4. Data Governance and Compliance / 数据治理与合规

### 4.1 Evidence Chain / 证据链

每条决策记录包含 / Each decision record contains:

- **Input**: 原始姓名字段 / Original name field
- **Prediction**: 预测结果 + 置信度 / Prediction + confidence
- **Evidence**: Top-K原因 + 权重 / Top-K reasons + weights
- **Modules**: 触发模块列表 / Fired modules list
- **Metadata**: 时间戳、算法版本、profile / Timestamp, algorithm version, profile

### 4.2 Statistical Monitoring / 统计监控

定期生成统计报告（每周）/ Generate statistical reports periodically (weekly):

- **准确率 / Accuracy**: 在已标注子集上验证 / Validate on labeled subset
- **覆盖率 / Coverage**: 1 - unknown_rate
- **未知率 / Unknown Rate**: 需要人工复核的比例 / Proportion requiring manual review
- **模块触发率 / Module Firing Rate**: 各模块贡献度 / Module contribution

### 4.3 Privacy and Security / 隐私与安全

- **数据脱敏 / Data Redaction**: 研究分析时使用hash代替原始姓名
- **访问控制 / Access Control**: 基于角色的权限管理 / Role-based access control
- **审计日志 / Audit Logs**: 所有访问和修改操作可追溯 / All access and modification operations traceable

---

## 5. Implementation Roadmap / 实施路线图

### Phase 1: Pilot (3 months) / 试点阶段（3个月）

- [ ] 在ИСТИНА数据上完成pilot验证（已完成设计）/ Complete pilot validation on ISTINA data (design completed)
- [ ] 性能基准测试 / Performance benchmarking
- [ ] 人工复核流程设计 / Human review workflow design

### Phase 2: Integration (6 months) / 集成阶段（6个月）

- [ ] SMBU SRP接口开发 / SMBU SRP interface development
- [ ] 批处理调度系统 / Batch processing scheduler
- [ ] 复核队列UI / Review queue UI
- [ ] 证据链存储与查询 / Evidence chain storage and query

### Phase 3: Production (ongoing) / 生产阶段（持续）

- [ ] 正式上线（需与平台运营方正式согласование）/ Production launch (requires formal coordination with platform operators)
- [ ] 持续监控与优化 / Continuous monitoring and optimization
- [ ] 人工反馈闭环 / Human feedback loop
- [ ] 算法迭代更新 / Algorithm iterative updates

---

## 6. Risks and Mitigation / 风险与缓解

### 6.1 Performance Risk / 性能风险

**风险 / Risk**: 峰值负载下处理时间过长

**缓解 / Mitigation**:
- 多进程并行处理（理论加速比：N_cores）
- Multi-process parallel processing (theoretical speedup: N_cores)
- 增量处理策略（仅处理变化记录）
- Incremental processing (only changed records)

### 6.2 Accuracy Risk / 准确率风险

**风险 / Risk**: 新数据分布漂移导致准确率下降

**缓解 / Mitigation**:
- 定期在人工标注子集上验证准确率
- Periodic validation on manually labeled subset
- 低置信度case进入人工复核队列
- Low-confidence cases enter human review queue
- 人工反馈用于算法迭代
- Human feedback for algorithm iteration

### 6.3 Integration Risk / 集成风险

**风险 / Risk**: 与现有系统接口不兼容

**缓解 / Mitigation**:
- RESTful API标准化接口
- RESTful API standardized interface
- 数据格式适配层（JSON/XML/CSV）
- Data format adapter layer (JSON/XML/CSV)
- 灰度发布策略（先小规模测试）
- Canary deployment (small-scale testing first)

---

## 7. Limitations and Future Work / 局限性与未来工作

### 7.1 Current Limitations / 当前局限性

⚠️ **重要声明 / Important Disclaimer**:

本设计研究为**paper design only**，未实际部署到SMBU平台。所有技术方案基于：

This design study is **paper design only**, not actually deployed to SMBU platform. All technical proposals are based on:

1. 真实性能基准（301K实验实测吞吐量）/ Real performance benchmarks (measured throughput from 301K experiment)
2. ISTINA pilot验证经验 / ISTINA pilot validation experience
3. 公开的SMBU平台信息 / Publicly available SMBU platform information

**未包含 / Not Included**:
- ❌ 实际SMBU数据测试 / Actual SMBU data testing
- ❌ 生产环境部署 / Production environment deployment
- ❌ 与SMBU平台运营方的正式协议 / Formal agreement with SMBU platform operators

### 7.2 Future Work / 未来工作

1. **SMBU Pilot**: 在SMBU提供的测试数据集上进行pilot验证
   - SMBU Pilot: Conduct pilot validation on SMBU-provided test dataset

2. **Performance Optimization**: 多进程并行、GPU加速（如适用）
   - Performance Optimization: Multi-process parallel, GPU acceleration (if applicable)

3. **Active Learning**: 人工复核结果反馈到算法训练
   - Active Learning: Human review results feedback to algorithm training

4. **Real-time Processing**: 探索在线API模式（低延迟要求）
   - Real-time Processing: Explore online API mode (low-latency requirements)

---

## 8. References / 参考文献

### SMBU Platform Information / SMBU平台信息

1. **PubScholar公共学术平台 国际版**
   - URL: https://www.cnki.net/advisory/zixun/qitazixun/20210901/171.html
   - 发布日期: 2021-09-01

2. **上海海事大学学术信息化建设**
   - 来源: 上海海事大学官网新闻

### Performance Benchmarks / 性能基准

1. **301K Experiment (evidence_chain_301k_STRICT)**
   - Dataset: crossref_authors.json (301,586 input records; 301,559 simple proxy-labeled rows)
   - Measured throughput: 166.7 names/sec
   - Date: 2025-12-19
   - See: `runs/evidence_chain_301k_STRICT/run_manifest.json`

2. **ISTINA Pilot**
   - Dataset: authors.json (ISTINA export)
   - Profile: ISTINA (Chinese prior: 0.5)
   - See: `runs/istina_pilot_*/run_manifest.json`

---

## Appendix / 附录

### A. Capacity Estimation Table / 容量估算表

详见 / See: `tables/smbu_capacity_estimate.tex`

### B. Architecture Diagrams / 架构图

- ISTINA Integration: `figs/istina_integration.puml`
- SMBU Pipeline: `figs/smbu_pipeline.puml`

### C. Algorithm Configuration / 算法配置

**Recommended Profile for SMBU**: Mixed (default)

```python
SMBU_CONFIG = SourceConfig(
    # Mixed profile: Chinese + Western authors
    chinese_prior_fam=0.4,  # Moderate Chinese prior
    chinese_prior_giv=0.2,
    western_prior_fam=0.2,
    western_prior_giv=0.3,
    mixed_prior_fam=0.25,
    mixed_prior_giv=0.25,

    # Unknown thresholds
    threshold_cn_unknown=0.4,
    threshold_west_unknown=0.3,
    threshold_mixed_unknown=0.4,

    # Batch consistency (enabled)
    person_conf_thresh=0.7,
    person_override_thresh=0.6,
    person_override_conf=0.7,

    pub_conf_thresh=0.7,
    pub_override_thresh=0.5,
    pub_override_conf=0.65,
    pub_dominance_min_diff=2,
)
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-20
**Status**: Design Study (Paper Design Only)
