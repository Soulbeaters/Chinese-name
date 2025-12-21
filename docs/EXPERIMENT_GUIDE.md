# 实验运行指南 / Experiment Guide

**作者**: Ma Jiaxin
**日期**: 2025-12-20
**项目**: Chinese Name Processing System v8.0

---

## 目录 / Contents

1. [概述 / Overview](#概述--overview)
2. [第二部分：Evidence Chain 报表重建 / Part 2: Evidence Chain Report Rebuilding](#第二部分evidence-chain-报表重建--part-2-evidence-chain-report-rebuilding)
3. [第四部分：ISTINA Pilot 实验 / Part 4: ISTINA Pilot Experiments](#第四部分istina-pilot-实验--part-4-istina-pilot-experiments)
4. [验收标准 / Acceptance Criteria](#验收标准--acceptance-criteria)

---

## 概述 / Overview

本指南涵盖两类实验：

- **Evidence Chain（论文第2-3部分）**: 基于现有结果重建报表，修复格式自洽性问题
- **ISTINA Pilot（论文第4部分）**: 运行完整pilot实验，生成论文可用的脱敏样本和表格

---

## 第二部分：Evidence Chain 报表重建 / Part 2: Evidence Chain Report Rebuilding

### 目标 / Objective

在不重跑算法的情况下，修复现有301k实验报表的格式问题：

- **A1**: stats_ci去重 + 小比例格式化 (Unknown Rate <0.1% 显示4位小数+count)
- **A2**: triggered_subsets数据驱动叙述（删除硬模板）
- **A3**: sanity_samples抽样逻辑修复
- **A4**: module_coverage口径统一（evaluated/fired/effective）
- **A5**: 复现性元数据增强（git diff patch）

### 使用方法 / Usage

```bash
# 基于现有运行结果重建报表
python experiments/rebuild_reports.py --run_dir runs/evidence_chain_301k_P0_P5_FINAL_V2
```

### 输出 / Output

重建以下文件：

```
runs/evidence_chain_301k_P0_P5_FINAL_V2/
├── statistics/
│   ├── stats_ci_global.json   (重建，含count字段)
│   ├── stats_ci_global.md     (重建，小比例4位小数)
│   └── stats_ci_global.tex    (重建，booktabs格式)
├── triggered_subsets/
│   ├── ablation_triggered_subsets.json
│   └── ablation_triggered_subsets.md  (数据驱动叙述)
├── sanity_samples/
│   ├── ablation_sanity_samples.jsonl  (修复抽样逻辑)
│   └── ablation_sanity_samples.md
├── events/baseline/
│   ├── module_coverage.json   (统一口径)
│   └── module_coverage.md     (明确三层定义)
└── repro/
    └── dirty_patch.diff       (若is_dirty=true)
```

### 修复详情 / Fix Details

#### A1: Stats CI 格式修复

**修复前 (Before)**:
```markdown
| baseline | Unknown Rate | 0.00% | ... | 2 |  # 精度不足
```

**修复后 (After)**:
```markdown
| baseline | Unknown Rate | 0.0007% | [0.0002%, 0.0024%] | 2 |  # 4位小数+count
```

#### A4: Module Coverage 口径定义

**修复后定义 (Unified Definitions)**:

- **Evaluated**: 模块在该记录上被评估（输入条件满足）
- **Fired**: 触发了该模块的非默认规则
- **Effective**: baseline vs ablation输出发生变化

---

## 第四部分：ISTINA Pilot 实验 / Part 4: ISTINA Pilot Experiments

### 目标 / Objective

运行完整的ISTINA pilot实验，生成论文第4章可直接引用的交付物：

- 脱敏日志样本（200行）
- 质量报告和LaTeX表格
- 性能基准测试
- 完整验收通过

### 前置条件 / Prerequisites

#### 1. 设置Salt环境变量 / Set Salt Environment Variable

**Windows PowerShell**:
```powershell
# 生成64字符随机salt (推荐)
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$salt = [Convert]::ToBase64String($bytes)

# 设置环境变量
$env:ISTINA_LOG_SALT = $salt

# 验证
echo $env:ISTINA_LOG_SALT
```

**Linux/Mac**:
```bash
# 使用OpenSSL生成
export ISTINA_LOG_SALT=$(openssl rand -hex 32)

# 验证
echo $ISTINA_LOG_SALT
```

### 实验计划 / Experiment Plan

#### Phase 1: Smoke Test (1k records)

**目的**: 快速验证脚本是否正常工作

```powershell
# SAFE DEFAULT: 必须先设置salt
$env:ISTINA_LOG_SALT = "YOUR_SECURE_RANDOM_SALT_HERE"

python scripts/run_istina_pilot.py `
  --input "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --out_dir "runs/istina_pilot_smoke" `
  --profile ISTINA `
  --seed 42 `
  --max_records 1000 `
  --write_full_log 0 `
  --keep_raw_sampled 0 `
  --validate 1
```

**预期时间**: ~1-2分钟
**输出**: `runs/istina_pilot_smoke/`
**安全保证**:
- `--write_full_log 0`: 不生成完整raw日志（默认，安全）
- `--keep_raw_sampled 0`: 自动删除临时采样文件（默认，安全）
- 仅保留脱敏样本（redacted_200.jsonl）可用于论文提交

#### Phase 2: Mini Pilot (10k records)

**目的**: 生成论文样例和截图

```powershell
# SAFE DEFAULT: 论文最终版本（10k sample）
python scripts/run_istina_pilot.py `
  --input "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --out_dir "runs/istina_pilot_10k_final" `
  --profile ISTINA `
  --seed 42 `
  --max_records 10000 `
  --write_full_log 0 `
  --keep_raw_sampled 0 `
  --validate 1
```

**预期时间**: ~2-3秒
**输出**: `runs/istina_pilot_10k_final/`
**论文提交安全**:
- 所有默认值已设为安全模式（write_full_log=0, keep_raw_sampled=0）
- 无需手动删除任何文件，临时raw文件自动清理
- 验收脚本会检查并阻止包含原始tokens的文件混入

#### Phase 3: Full Pilot (全量)

**目的**: 完整性能基准测试

```powershell
# Full pilot（全量301k，可选）
python scripts/run_istina_pilot.py `
  --input "C:\istina\materia 材料\测试表单\crossref_authors.json" `
  --out_dir "runs/istina_pilot_full" `
  --profile ISTINA `
  --seed 42 `
  --max_records 0 `
  --write_full_log 0 `
  --keep_raw_sampled 0 `
  --validate 1
```

**安全默认**: 所有raw token files自动清理，仅保留脱敏样本

**预期时间**: ~30-60分钟（取决于数据规模）
**输出**: `runs/istina_pilot_full/`

### 输出目录结构 / Output Directory Structure

```
runs/istina_pilot_*/
├── run_manifest.json          # 运行元数据（含git、seed、N等）
├── dataset_card.md            # 数据集描述
├── env.txt                    # 环境信息
├── logs/
│   ├── istina_batch_full.jsonl            # 完整日志（仅write_full_log=1时）
│   ├── istina_batch_raw_sampled.jsonl     # 采样raw日志（write_full_log=0）
│   ├── istina_batch_redacted_200.jsonl    # 脱敏样本（可随论文提交）
│   ├── istina_batch_redaction_policy.md   # 脱敏策略文档
│   └── istina_batch_redaction_policy.json
├── events/baseline/
│   ├── decision_events.jsonl              # 决策事件（无input_tokens）
│   ├── module_coverage.json|md            # 模块覆盖率
│   ├── reason_counts.csv                  # 原因计数
│   └── score_margin_stats.json            # 分数边界统计
├── reports/
│   └── istina_pilot_summary.md            # 总结报告（论文4.1节）
├── tables/
│   ├── istina_pilot_quality.tex           # 质量表格（booktabs）
│   └── istina_pilot_perf.tex              # 性能表格（booktabs）
├── statistics/
│   ├── stats_ci_global.{json,md,tex}      # 全局统计+CI
│   ├── stats_ci_end_to_end.{json,md,tex}  # End-to-end指标
│   ├── stats_ci_conditional.{json,md,tex} # 条件指标
│   └── stats_ci_coverage.{json,md,tex}    # 覆盖率指标
└── performance_benchmark.json             # 性能基准（throughput/latency）
```

### 脱敏规则 / Redaction Rules

根据 `logs/istina_batch_redaction_policy.md`：

#### 删除/哈希字段 / Removed/Hashed Fields

- **人名**: SHA-256(salt + normalized_token)[:16]
- **input_tokens**: 完全移除，替换为统计特征：
  - `tok_hash`: 单向哈希
  - `len`: Token长度
  - `script`: 文字类型（latin/cyrillic/han/mixed）
  - `shape`: 形状模式（X=大写，x=小写，9=数字）
  - `has_hyphen`, `has_apostrophe`, `has_dot`: 布尔特征

#### 保留字段 / Preserved Fields

- **Reason codes**: 决策原因（CN_SURNAME_KNOWN等）
- **Score margin**: 分数边界（连续值）
- **Fired/effective modules**: 模块触发标记
- **Output order**: family_first/given_first/unknown

#### 合规性 / Compliance

- 按照 GDPR Article 25 & 32 设计
- 按照俄罗斯联邦152-FZ法设计
- **最终合规性以机构审查为准**

---

## 验收标准 / Acceptance Criteria

### Evidence Chain 验收 / Evidence Chain Acceptance

```bash
# 检查stats_ci是否包含count字段
cat runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_global.md | grep "Count"

# 检查Unknown Rate是否显示4位小数
cat runs/evidence_chain_301k_P0_P5_FINAL_V2/statistics/stats_ci_global.md | grep "0.0007%"

# 检查module_coverage是否定义了三层
cat runs/evidence_chain_301k_P0_P5_FINAL_V2/events/baseline/module_coverage.md | grep -E "(Evaluated|Fired|Effective)"
```

### ISTINA Pilot 验收 / ISTINA Pilot Acceptance

#### 自动验收 / Automated Validation

每次运行自动调用 `validate_deliverables.py`：

```bash
# 控制台应显示
VALIDATION PASSED
```

#### 手动检查 / Manual Checks

1. **文件完整性**:
   ```bash
   ls runs/istina_pilot_smoke/logs/istina_batch_redacted_200.jsonl
   ls runs/istina_pilot_smoke/tables/istina_pilot_quality.tex
   ls runs/istina_pilot_smoke/performance_benchmark.json
   ```

2. **无PII泄露**:
   ```bash
   # 扫描redacted样本，确保无原始人名
   python -c "
import re
import json

with open('runs/istina_pilot_smoke/logs/istina_batch_redacted_200.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        event = json.loads(line)
        # 检查是否存在input_tokens字段
        if 'input_tokens' in event:
            print('[FAIL] Found input_tokens in redacted log!')
            exit(1)

print('[PASS] No PII found in redacted log')
"
   ```

3. **LaTeX表格可编译**:
   ```bash
   # 复制tex文件到LaTeX项目并尝试编译
   # 或使用在线LaTeX编辑器（如Overleaf）测试
   ```

4. **数字一致性**:
   ```bash
   # N_total和N_labeled在所有文件中一致
   cat runs/istina_pilot_smoke/run_manifest.json | grep "n_records"
   cat runs/istina_pilot_smoke/statistics/stats_ci_global.json | grep "n_records"
   ```

---

## 常见问题 / Troubleshooting

### Q1: rebuild_reports.py报错"No predictions found"

**原因**: 301k实验未保存event logs，只有汇总统计
**解决**: 脚本会自动使用run_manifest.json中的results_summary，属于正常行为

### Q2: ISTINA pilot报错"ISTINA_LOG_SALT not set"

**原因**: 未设置环境变量
**解决**: 按照上述"前置条件"步骤设置salt

### Q3: validation失败"Missing required file"

**原因**: 脚本运行不完整或中途报错
**解决**:
1. 检查控制台输出，找到第一个报错
2. 确认input数据路径正确
3. 确认salt已设置
4. 重新运行实验

### Q4: redacted样本仍包含PII

**原因**: redact_logs.py逻辑问题
**解决**:
1. 检查 `scripts/redact_logs.py` 的hash逻辑
2. 确认salt非空
3. 手动运行redact_logs.py单独测试

---

## 进阶使用 / Advanced Usage

### 自定义参数 / Custom Parameters

```bash
# 使用自定义seed
python scripts/run_istina_pilot.py --seed 12345 ...

# 修改redacted样本行数
python scripts/run_istina_pilot.py --sample_lines 500 ...

# 调试模式：保留临时raw采样文件（仅用于调试，勿提交）
python scripts/run_istina_pilot.py --keep_raw_sampled 1 ...

# 调试模式：生成完整raw日志（仅用于调试，勿提交）
python scripts/run_istina_pilot.py --write_full_log 1 ...

# 关闭自动验收
python scripts/run_istina_pilot.py --validate 0 ...
```

### 性能优化 / Performance Optimization

- **小数据集测试**: 使用`--max_records 100`快速迭代
- **并行运行**: 可同时运行多个不同seed的实验（注意磁盘I/O）
- **内存优化**: Full pilot时使用`--write_full_log 0`减少内存占用

---

## 论文引用清单 / Paper Citation Checklist

### 第二部分（Evidence Chain）可引用文件:

- `statistics/stats_ci_global.tex` → 论文Table 2
- `triggered_subsets/ablation_triggered_subsets.md` → 论文Section 3.2
- `events/baseline/module_coverage.md` → 论文Section 3.3
- `sanity_samples/ablation_sanity_samples.jsonl` → 论文Appendix A

### 第四部分（ISTINA Pilot）可引用文件:

- `reports/istina_pilot_summary.md` → 论文Section 4.1
- `tables/istina_pilot_quality.tex` → 论文Table 4
- `tables/istina_pilot_perf.tex` → 论文Table 5
- `logs/istina_batch_redacted_200.jsonl` → 论文Supplementary Material
- `logs/istina_batch_redaction_policy.md` → 论文Data Availability Statement
- `figs/*.png` → 论文Figure 3, 4

---

## 更新日志 / Changelog

- **2025-12-20**: 初始版本，包含rebuild_reports.py和ISTINA pilot完整指南
- **2025-12-20**: 添加B0-B5所有参数和验收标准

---

**文档版本**: 1.0
**最后更新**: 2025-12-20
**维护者**: Ma Jiaxin
