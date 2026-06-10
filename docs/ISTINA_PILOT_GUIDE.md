# ISTINA Pilot 完整使用指南
# ISTINA Pilot Complete Usage Guide

**Version**: 1.0
**Date**: 2025-12-20
**Author**: Ma Jiaxin

---

## 概述 / Overview

ISTINA Pilot工具链为论文第4部分"实践/应用（практика/апробация）"提供完整的可复现、可审计的试验平台。本工具链严格遵循"不得捏造数据"原则，所有数值均从真实运行artifacts读取生成。

The ISTINA Pilot toolchain provides a complete, reproducible, and auditable experimental platform for Section 4 "Practice/Application" of the dissertation. This toolchain strictly follows the "no fabricated data" principle - all values are read from real run artifacts.

---

## 快速开始 / Quick Start

### 前置条件 / Prerequisites

1. **Python 3.11+**
2. **环境变量 / Environment Variables**:
   ```bash
   export ISTINA_LOG_SALT="your_secure_random_string_here"
   ```
   ⚠️ **重要 / Important**: Salt必须保密，用于哈希record_id和token

3. **ИСТИНА测试数据 / ISTINA Test Data**:
   - 路径 / Path: `C:\istina\materia 材料\测试表单\authors.json`
   - 格式 / Format: JSON array of author records
   - 必需字段 / Required fields: `original_name` (or `full_name`/`name`)
   - 可选字段 / Optional fields: `lastname`, `firstname` (用于ground truth)

### 一键运行完整Pilot / One-Command Full Pilot

```bash
cd "C:\program 1 in 2025"

# Step 1: Run ISTINA pilot (with validation)
python scripts/run_istina_pilot.py \
  --input "C:\istina\materia 材料\测试表单\authors.json" \
  --out_dir "runs/istina_pilot_20251220_demo" \
  --profile ISTINA \
  --seed 20251220 \
  --sample_lines 200 \
  --validate 1

# Step 2: Generate redacted logs (if not auto-generated)
python scripts/redact_logs.py \
  --input "runs/istina_pilot_20251220_demo/logs/istina_batch_full.jsonl" \
  --output "runs/istina_pilot_20251220_demo/logs/istina_batch_redacted_200.jsonl" \
  --policy "runs/istina_pilot_20251220_demo/logs/istina_batch_redaction_policy.md" \
  --salt_env ISTINA_LOG_SALT \
  --seed 20251220 \
  --sample_lines 200

# Step 3: Validate deliverables
python -m experiments.validate_deliverables "runs/istina_pilot_20251220_demo"

# Step 4: (Optional) Generate dynamic status report
python -m experiments.generate_paper_report --output "ISTINA_PILOT_STATUS.md"
```

---

## 详细说明 / Detailed Instructions

### 1. 运行ISTINA Pilot / Run ISTINA Pilot

#### 命令参数 / Command Arguments

```bash
python scripts/run_istina_pilot.py \
  --input <ISTINA_EXPORT_PATH> \        # ИСТИНА导出数据路径 (required)
  --out_dir <OUTPUT_DIR> \              # 输出目录 (required)
  --profile ISTINA \                    # 算法profile (default: ISTINA)
  --seed 20251220 \                     # 随机种子 (default: 20251220)
  --max_records 0 \                     # 最大处理记录数 (0=all, default: 0)
  --write_full_log 1 \                  # 写入完整日志 (default: 1)
  --redact_salt_env ISTINA_LOG_SALT \   # Salt环境变量名 (default: ISTINA_LOG_SALT)
  --sample_lines 200 \                  # 脱敏样本行数 (default: 200)
  --validate 1                          # 运行验证 (default: 1)
```

#### 输出结构 / Output Structure

运行成功后，输出目录包含以下文件：

After successful run, the output directory contains:

```
runs/istina_pilot_YYYYMMDD_HHMMSS/
├── run_manifest.json                  # 运行元数据 / Run metadata
├── env.txt                            # 环境信息 / Environment info
├── dataset_card.md                    # 数据集卡片 / Dataset card
├── reports/
│   └── istina_pilot_summary.md        # 试验摘要报告 / Pilot summary report
├── logs/
│   ├── istina_batch_full.jsonl        # 完整日志（含input_tokens）/ Full logs
│   ├── istina_batch_redacted_200.jsonl # 脱敏样本（200行）/ Redacted sample
│   └── istina_batch_redaction_policy.md # 脱敏策略说明 / Redaction policy
├── events/
│   └── baseline/
│       ├── decision_events.jsonl      # 决策事件日志 / Decision events
│       ├── module_coverage.json       # 模块覆盖率 / Module coverage
│       └── module_coverage.md
├── statistics/
│   ├── stats_ci_global.json           # 统计报告（索引）/ Stats index
│   ├── stats_ci_global.md
│   ├── stats_ci_global.tex
│   ├── stats_ci_global_end_to_end.*   # End-to-end metrics (primary)
│   ├── stats_ci_global_conditional.*  # Conditional accuracy
│   └── stats_ci_global_coverage.*     # Coverage metrics
├── tables/
│   ├── istina_pilot_quality.tex       # 质量指标表 / Quality metrics table
│   └── istina_pilot_perf.tex          # 性能指标表 / Performance metrics table
└── figs/
    ├── istina_integration.puml        # 架构图：ISTINA集成 / Architecture: ISTINA integration
    └── smbu_pipeline.puml             # 架构图：SMBU流水线 / Architecture: SMBU pipeline
```

### 2. 日志脱敏 / Log Redaction

#### 为何需要脱敏 / Why Redaction

- **保护个人隐私 / Protect Privacy**: 移除原始姓名tokens
- **符合GDPR和152-FZ / GDPR & 152-FZ Compliance**
- **论文可提交 / Paper Submission**: 脱敏样本可随论文附件提交

#### 脱敏规则 / Redaction Rules

**移除字段 / Removed Fields**:
- `input_tokens`: 原始tokens完全移除 / Original tokens completely removed

**替换为 / Replaced With**:
- `input_tokens_redacted`: 每个token包含 / Each token contains:
  - `tok_hash`: SHA-256(salt + normalized_token)[:16]
  - `len`: Token长度 / Token length
  - `script`: 字符集类型 / Script type (latin/cyrillic/han/mixed/other)
  - `shape`: 形状模式 / Shape pattern (X=upper, x=lower, 9=digit, *=other)
  - `has_hyphen`: 是否含连字符 / Has hyphen
  - `has_apostrophe`: 是否含撇号 / Has apostrophe
  - `has_dot`: 是否含点号 / Has dot

**保留字段 / Preserved Fields**:
- `prediction`: 预测结果 / Prediction result
- `scores`: 分数分布 / Score distribution
- `score_margin`: 决策边界 / Decision margin
- `reasons_topk`: Top-K证据 / Top-K evidence (**可解释性关键 / Key for interpretability**)
- `fired_modules`: 触发模块 / Fired modules
- `latency_ms`: 处理延迟 / Processing latency

#### 采样策略 / Sampling Strategy

200行样本按优先级采样（确定性，可复现）:

200-line sample prioritized sampling (deterministic, reproducible):

1. **Unknown predictions**: prediction.label == "unknown"
2. **Low margin**: score_margin < 0.2 (决策边界附近)
3. **Exceptions**: exception != null
4. **Random fill**: 均匀随机补齐 / Uniform random fill

### 3. 验证交付物 / Validate Deliverables

```bash
python -m experiments.validate_deliverables "runs/istina_pilot_YYYYMMDD_HHMMSS"
```

#### 验证检查项 / Validation Checks

1. **文件完整性 / File Completeness**:
   - 检测run_type (ISTINA_PILOT vs evidence_chain)
   - 验证所有必需文件存在
   - 警告可选文件缺失

2. **N一致性 / N Consistency**:
   - N_total在所有文件中一致 / N_total consistent across all files
   - N_labeled在统计文件中一致 / N_labeled consistent in stats files
   - run_manifest.json与stats_ci_global.json对齐

3. **点估计一致性 / Point Estimate Consistency**:
   - accuracy在manifest和stats中一致（容差1e-6）
   - unknown_rate, error_rate一致

#### 验证通过标准 / Pass Criteria

✅ **VALIDATION PASSED** if:
- 所有必需文件存在 / All required files exist
- N_total和N_labeled一致 / N_total and N_labeled consistent
- 点估计一致性 / Point estimates consistent
- 无错误 / No errors

❌ **VALIDATION FAILED** if:
- 任何必需文件缺失 / Any required file missing
- N不一致 / N inconsistent
- 点估计不一致 / Point estimates inconsistent

### 4. 生成动态状态报告 / Generate Dynamic Status Report

```bash
python -m experiments.generate_paper_report --output "ISTINA_PILOT_STATUS.md"
```

此报告汇总所有已完成的实验（包括ISTINA pilot和evidence-chain实验）。

This report summarizes all completed experiments (including ISTINA pilot and evidence-chain experiments).

---

## 论文使用 / Paper Usage

### LaTeX表格插入 / LaTeX Table Insertion

#### 质量指标表 / Quality Metrics Table

```latex
\input{runs/istina_pilot_YYYYMMDD_HHMMSS/tables/istina_pilot_quality.tex}
```

#### 性能指标表 / Performance Metrics Table

```latex
\input{runs/istina_pilot_YYYYMMDD_HHMMSS/tables/istina_pilot_perf.tex}
```

#### SMBU容量估算表 / SMBU Capacity Estimation Table

```latex
\input{tables/smbu_capacity_estimate.tex}
```

### PlantUML架构图 / PlantUML Architecture Diagrams

#### ISTINA集成架构 / ISTINA Integration Architecture

```latex
% 在论文中引用 / Reference in paper:
\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{figs/istina_integration.png}
\caption{ИСТИНА系统集成架构 / ISTINA System Integration Architecture}
\label{fig:istina_integration}
\end{figure}
```

**生成PNG / Generate PNG** (需要PlantUML环境 / Requires PlantUML):
```bash
plantuml figs/istina_integration.puml
plantuml figs/smbu_pipeline.puml
```

或使用在线渲染器 / Or use online renderer:
- https://www.plantuml.com/plantuml/uml/

#### SMBU流水线架构 / SMBU Pipeline Architecture

```latex
\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{figs/smbu_pipeline.png}
\caption{SMBU学术平台集成设计 / SMBU Scholarly Platform Integration Design}
\label{fig:smbu_pipeline}
\end{figure}
```

### 文本引用 / Text References

#### ISTINA Pilot摘要 / ISTINA Pilot Summary

从`reports/istina_pilot_summary.md`复制相关段落到论文正文。

Copy relevant paragraphs from `reports/istina_pilot_summary.md` to paper body.

#### SMBU设计研究 / SMBU Design Study

从`docs/smbu_design_study.md`引用设计方案和容量估算。

Reference design proposals and capacity estimates from `docs/smbu_design_study.md`.

#### 脱敏日志样本 / Redacted Log Sample

可在论文附录中展示部分脱敏日志（例如5-10条）以证明可追溯性和可解释性：

You can show partial redacted logs (e.g., 5-10 entries) in the paper appendix to demonstrate traceability and interpretability:

```json
{
  "ts": "2025-12-20T10:30:45.123456Z",
  "run_id": "istina_pilot_20251220_120000",
  "record_id_hash": "a1b2c3d4e5f67890",
  "source": "ISTINA",
  "profile": "ISTINA",
  "input_tokens_redacted": [
    {"tok_hash": "f1e2d3c4b5a69870", "len": 5, "script": "cyrillic", "shape": "Xxxxx"},
    {"tok_hash": "9876543210abcdef", "len": 8, "script": "cyrillic", "shape": "Xxxxxxxx"}
  ],
  "prediction": {"label": "family_first", "confidence": 0.87},
  "scores": {"family_first": 0.87, "given_first": 0.10, "unknown": 0.03},
  "score_margin": 0.77,
  "reasons_topk": [
    {"code": "CYRILLIC_PATRONYMIC_PATTERN", "weight": 1.0},
    {"code": "BATCH_PUB_CONSISTENCY", "weight": 0.8}
  ],
  "fired_modules": ["source_prior", "batch_consistency"],
  "latency_ms": 12
}
```

---

## 故障排查 / Troubleshooting

### 问题1: Salt环境变量未设置 / Salt Environment Variable Not Set

**症状 / Symptom**:
```
[WARNING] Environment variable ISTINA_LOG_SALT not set. Using empty salt.
```

**解决 / Solution**:
```bash
export ISTINA_LOG_SALT="your_secure_random_string_here"
```

或在Python脚本启动前设置 / Or set before running Python script:
```bash
ISTINA_LOG_SALT="xxx" python scripts/run_istina_pilot.py ...
```

### 问题2: 验证失败 - 文件缺失 / Validation Failed - Missing Files

**症状 / Symptom**:
```
[ERROR] Missing required file: tables/istina_pilot_quality.tex
VALIDATION FAILED
```

**解决 / Solution**:
- 检查run_istina_pilot.py是否成功完成所有步骤
- Check if run_istina_pilot.py completed all steps successfully
- 查看完整输出日志 / Review full output logs
- 重新运行pilot / Re-run pilot

### 问题3: N不一致 / N Inconsistency

**症状 / Symptom**:
```
[ERROR] N consistency validation failed: N_total mismatch
```

**解决 / Solution**:
- 这通常是P0-P5改进未正确应用的信号
- This usually indicates P0-P5 improvements not properly applied
- 确保使用最新版本的statistical_tests.py
- Ensure using latest version of statistical_tests.py
- 检查generate_statistical_report调用是否传递n_records_total
- Check if generate_statistical_report call passes n_records_total

### 问题4: 性能慢 / Slow Performance

**症状 / Symptom**:
处理速度远低于预期（< 10 names/sec）

**可能原因 / Possible Causes**:
1. CPU负载过高 / High CPU load
2. 磁盘I/O瓶颈 / Disk I/O bottleneck
3. 数据格式问题（大量异常）/ Data format issues (many exceptions)

**解决 / Solution**:
- 使用--max_records先测试小规模数据
- Test with small data first using --max_records
- 监控CPU和磁盘使用率 / Monitor CPU and disk usage
- 检查decision_events中exception比例 / Check exception rate in decision_events

---

## 进阶使用 / Advanced Usage

### 自定义Profile / Custom Profile

如果需要为特定数据源创建自定义profile，编辑`src/config_v8.py`:

To create custom profile for specific data source, edit `src/config_v8.py`:

```python
CUSTOM_CONFIG = SourceConfig(
    chinese_prior_fam=0.4,
    chinese_prior_giv=0.2,
    western_prior_fam=0.2,
    western_prior_giv=0.3,
    # ... other parameters
)

SOURCE_CONFIGS["CUSTOM"] = CUSTOM_CONFIG
```

然后使用 / Then use:
```bash
python scripts/run_istina_pilot.py --profile CUSTOM ...
```

### 批量处理多个数据源 / Batch Process Multiple Data Sources

```bash
for dataset in istina_2024.json istina_2025.json; do
  python scripts/run_istina_pilot.py \
    --input "C:\istina\materia 材料\测试表单\$dataset" \
    --out_dir "runs/istina_pilot_$(basename $dataset .json)" \
    --profile ISTINA \
    --validate 1
done
```

### 提取特定模块的证据 / Extract Evidence for Specific Modules

```python
import json

# Load decision events
with open("runs/istina_pilot_*/events/baseline/decision_events.jsonl") as f:
    events = [json.loads(line) for line in f]

# Filter events where specific module fired
batch_consistency_events = [
    e for e in events
    if "batch_consistency" in e.get("fired_modules", [])
]

print(f"Batch consistency fired in {len(batch_consistency_events)} cases")
```

---

## 性能基准参考 / Performance Benchmark Reference

基于真实301K实验 (evidence_chain_301k_STRICT):

Based on real 301K experiment (evidence_chain_301k_STRICT):

- **吞吐量 / Throughput**: 166.7 names/sec
- **数据集规模 / Dataset Size**: 301,586 input records; 301,559 simple proxy-labeled rows
- **处理时间 / Processing Time**: ~30 minutes (6 configs)
- **单配置时间 / Per-Config Time**: ~5 minutes
- **实验ID / Experiment ID**: evidence_chain_301k_STRICT
- **日期 / Date**: 2025-12-19

**推算容量 / Extrapolated Capacity**:
- 每小时 / Per Hour: 600,120 names
- 4小时窗口 / 4-Hour Window: 2,400,480 names

**ISTINA Pilot预期性能 / Expected ISTINA Pilot Performance**:
- 小规模（< 10K）/ Small Scale: 100-150 names/sec
- 中等规模（10K-50K）/ Medium Scale: 80-120 names/sec
- 大规模（> 50K）/ Large Scale: 60-100 names/sec

---

## 联系与反馈 / Contact and Feedback

**Author**: Ma Jiaxin (Ма Цзясин)
**Institution**: МГУ (Московский государственный университет)
**GitHub**: https://github.com/Soulbeaters/Chinese-name
**Email**: (见论文署名 / See paper authorship)

如有问题或建议，请在GitHub仓库提交issue。

For questions or suggestions, please submit an issue on the GitHub repository.

---

**Document Version**: 1.0
**Last Updated**: 2025-12-20
