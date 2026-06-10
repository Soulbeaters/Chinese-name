# 论文级可复现实验记录工具链 / Paper-Level Reproducible Experiment Toolchain

**作者 / Author:** Ма Цзясин (Ma Jiaxin)
**版本 / Version:** v1.0
**日期 / Date:** 2025-12-19

---

## 概述 / Overview

本工具链为中文姓氏识别算法v8.0提供完整的可复现实验记录功能。

This toolchain provides complete reproducible experiment recording capabilities for the Chinese Surname Identifier v8.0 algorithm.

**核心功能 / Key Features:**
- ✅ 自动记录完整的实验环境（Git版本、Python环境、系统信息）
- ✅ 性能指标测量（Wall time、CPU time、内存使用）
- ✅ 消融实验支持（Ablation study）
- ✅ 数据集统计分析和Dataset Card自动生成
- ✅ 多次运行统计（均值和标准差）
- ✅ JSON和CSV格式结果输出

---

## 安装 / Installation

### 1. 安装依赖 / Install Dependencies

```bash
cd "C:\program 1 in 2025"
pip install -r requirements.txt
```

**必需依赖 / Required Dependencies:**
- `PyYAML>=5.4` - 用于消融实验配置 / For ablation config
- `psutil>=5.8.0` - 用于性能监控 / For performance monitoring
- `pypinyin>=0.44.0` - 用于拼音转换 / For Pinyin conversion

### 2. 验证安装 / Verify Installation

```bash
python experiments/run_bench.py --help
```

---

## 快速开始 / Quick Start

### 基础用法 / Basic Usage

```bash
# 运行单个数据集 / Run single dataset
python experiments/run_bench.py test_data/sample_test.json

# 运行多个数据集 / Run multiple datasets
python experiments/run_bench.py \
    "C:\istina\materia 材料\测试表单\crossref_authors.json" \
    "C:\istina\materia 材料\测试表单\dois.json"
```

### 使用消融实验配置 / With Ablation Configuration

```bash
# 使用预定义的消融配置运行完整实验 / Run full experiment with predefined ablation configs
python experiments/run_bench.py \
    "C:\istina\materia 材料\测试表单\crossref_authors.json" \
    --ablation experiments/ablation.yaml \
    --repeats 3
```

### 自定义输出目录 / Custom Output Directory

```bash
python experiments/run_bench.py \
    test_data/sample_test.json \
    --output runs/my_experiment_name \
    --repeats 5
```

---

## 输出结构 / Output Structure

运行实验后，会在 `runs/` 目录下生成以下结构：

After running experiments, the following structure is generated in the `runs/` directory:

```
runs/<timestamp>__git-<sha>/
├── run_manifest.json          # 运行清单 / Run manifest
│   ├── timestamp_utc          # UTC时间戳
│   ├── git_info               # Git仓库信息
│   ├── command_line           # 命令行参数
│   ├── python_version         # Python版本
│   ├── system_info            # 系统信息（CPU、RAM等）
│   └── algorithm_version      # 算法版本 (v8.0)
│
├── env.txt                    # 环境信息 / Environment info
│   ├── Python version
│   ├── Platform
│   └── pip freeze output
│
├── results/                   # 结果文件 / Results
│   ├── metrics.csv            # CSV格式指标
│   └── metrics.json           # JSON格式指标
│       ├── config_name        # 配置名称
│       ├── dataset            # 数据集名称
│       ├── n_records          # 记录数
│       ├── accuracy           # 准确率
│       ├── unknown_rate       # Unknown比例
│       ├── wall_time_s        # 墙上时钟时间（秒）
│       ├── cpu_user_s         # 用户态CPU时间
│       ├── cpu_sys_s          # 系统态CPU时间
│       ├── peak_rss_mb        # 峰值内存（MB）
│       └── names_per_sec      # 吞吐量（姓名/秒）
│
├── datasets/                  # 数据集信息 / Dataset info
│   ├── <name>.sha256          # 数据集SHA-256哈希
│   ├── <name>.stats.json      # 数据集统计信息
│   └── <name>.dataset_card.md # Dataset Card（半自动生成）
│
└── logs/                      # 日志文件 / Log files
    ├── stdout.log
    └── stderr.log
```

---

## 消融实验 / Ablation Studies

### 配置文件 / Configuration File

消融实验配置文件位于 `experiments/ablation.yaml`。

The ablation configuration file is located at `experiments/ablation.yaml`.

**预定义配置 / Predefined Configurations:**

1. **baseline** - 完整v8.0系统，所有特性启用
2. **ablation_no_source_prior** - 禁用数据源先验
3. **ablation_no_western_exclusion** - 禁用西方姓氏排除规则
4. **ablation_no_batch_consistency** - 禁用批量一致性调整
5. **ablation_no_person_consistency** - 仅禁用作者级一致性
6. **ablation_no_pub_consistency** - 仅禁用文章级一致性

### 自定义配置 / Custom Configuration

编辑 `experiments/ablation.yaml` 添加新的消融配置：

Edit `experiments/ablation.yaml` to add new ablation configurations:

```yaml
my_custom_config:
  name: "my_experiment_name"
  description: "实验描述 / Experiment description"
  disable_source_prior: false
  disable_western_exclusion: false
  disable_batch_consistency: false
  enable_person_consistency: true
  enable_pub_consistency: true
```

**开关说明 / Switch Description:**

- `disable_source_prior` - 禁用数据源特定先验分数
- `disable_western_exclusion` - 禁用西方姓氏排除规则
- `disable_batch_consistency` - 禁用批量一致性（person + publication）
- `enable_person_consistency` - 启用作者级一致性调整
- `enable_pub_consistency` - 启用文章级一致性调整

---

## Dataset Card 生成 / Dataset Card Generation

每个数据集会自动生成一个 Dataset Card（基于Hugging Face格式）。

A Dataset Card is automatically generated for each dataset (based on Hugging Face format).

**自动填充字段 / Auto-filled Fields:**
- Composition（样本统计）
- Name characteristics（姓名特征）
- Token distribution（Token分布）
- Special characters（特殊字符统计）

**需要手工补充的字段（标记为TODO）/ Manual Fields (marked TODO):**
- Motivation（动机）
- Source & Collection（来源和收集方法）
- Filtering（过滤步骤）
- Labeling（标注方法）
- Limitations（限制）

---

## 性能测量 / Performance Measurement

### 跨平台支持 / Cross-platform Support

工具链支持Windows和Linux平台的性能测量。

The toolchain supports performance measurement on both Windows and Linux.

**Windows:** 使用 `psutil` 库
**Linux:** 使用 `resource` 模块（优先）或 `psutil`

### 测量指标 / Metrics

- **wall_time_s** - 墙上时钟时间（使用`time.perf_counter()`）
- **cpu_user_s** - 用户态CPU时间
- **cpu_sys_s** - 系统态CPU时间
- **peak_rss_mb** - 峰值常驻集大小（内存）
- **names_per_sec** - 吞吐量（每秒处理姓名数）

### 重复运行 / Repeated Runs

默认配置：
- 重复次数：3次（可通过`--repeats`参数修改）
- Warmup：1次（可通过`--skip-warmup`跳过）
- 结果：丢弃warmup，计算均值和标准差

---

## 命令行参数 / Command-line Arguments

```bash
python experiments/run_bench.py [-h] [--ablation ABLATION] [--output OUTPUT]
                                [--repeats REPEATS] [--skip-warmup]
                                datasets [datasets ...]
```

**位置参数 / Positional Arguments:**
- `datasets` - 数据集文件路径（支持多个）

**可选参数 / Optional Arguments:**
- `--ablation ABLATION` - 消融实验配置文件路径（YAML格式）
- `--output OUTPUT` - 输出目录路径（默认：`runs/<timestamp>__git-<sha>`）
- `--repeats REPEATS` - 重复运行次数（默认：3）
- `--skip-warmup` - 跳过预热运行

---

## 示例 / Examples

### 示例1: 基础基准测试 / Example 1: Basic Benchmark

```bash
python experiments/run_bench.py \
    "C:\istina\materia 材料\测试表单\crossref_authors.json"
```

**输出 / Output:**
```
输出目录 / Output directory: C:\program 1 in 2025\runs\20251218_220417__git-e4d88f1

处理数据集 / Processing dataset: crossref_authors
  分析数据集统计信息 / Analyzing dataset statistics...
  加载了 410724 条记录 / Loaded 410724 records

  运行配置 / Running config: v8.0_baseline
    预热运行 / Warmup run...
    重复 1/3 / Repeat 1/3...
    重复 2/3 / Repeat 2/3...
    重复 3/3 / Repeat 3/3...

保存结果 / Saving results...

完成！结果保存在 / Done! Results saved in: C:\program 1 in 2025\runs\20251218_220417__git-e4d88f1
```

### 示例2: 完整消融实验 / Example 2: Full Ablation Study

```bash
python experiments/run_bench.py \
    "C:\istina\materia 材料\测试表单\crossref_authors.json" \
    "C:\istina\materia 材料\测试表单\dois.json" \
    --ablation experiments/ablation.yaml \
    --repeats 3 \
    --output runs/full_ablation_study
```

这将运行所有6个配置（baseline + 5个ablation），每个配置重复3次。

This runs all 6 configurations (baseline + 5 ablations), each repeated 3 times.

### 示例3: 快速测试（跳过warmup）/ Example 3: Quick Test (Skip Warmup)

```bash
python experiments/run_bench.py \
    test_data/sample_test.json \
    --repeats 2 \
    --skip-warmup
```

---

## 数据集格式 / Dataset Format

### JSON格式 / JSON Format

```json
[
  {
    "firstname": "Wei",
    "lastname": "Zhang",
    "true_position": "given_first",
    "orcid": "",
    "affiliation": "Tsinghua University, Beijing, China",
    "doi": "10.1000/test001",
    "source": "CROSSREF",
    "person_id": "optional_person_id",
    "publication_id": "optional_pub_id"
  }
]
```

### JSONL格式 / JSONL Format

```jsonl
{"firstname": "Wei", "lastname": "Zhang", "true_position": "given_first", ...}
{"firstname": "Poyarkov", "lastname": "N.A.", "true_position": "family_first", ...}
```

**必需字段 / Required Fields:**
- `firstname` - given/first-name field used as algorithm input
- `lastname` - family/last-name field used as algorithm input
- `true_position` - explicit human/advisor label for evaluation (`given_first` or `family_first`)

**可选字段 / Optional Fields:**
- `affiliation` - 机构信息
- `source` - 数据源（CROSSREF / ORCID / ISTINA）
- `doi` - 文章DOI
- `orcid` - ORCID标识符
- `person_id` - 作者ID（用于一致性调整）
- `publication_id` - 文章ID（用于一致性调整）

---

## 结果分析 / Result Analysis

### 读取结果 / Reading Results

**Python示例 / Python Example:**

```python
import json
import pandas as pd

# 读取JSON格式 / Read JSON format
with open('runs/<run_id>/results/metrics.json', 'r') as f:
    results = json.load(f)

# 读取CSV格式 / Read CSV format
df = pd.read_csv('runs/<run_id>/results/metrics.csv')

# 筛选平均值结果 / Filter mean results
mean_results = df[df['accuracy_mean'].notna()]
print(mean_results[['config_name', 'accuracy_mean', 'wall_time_s_mean']])
```

### 比较不同配置 / Comparing Configurations

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('runs/<run_id>/results/metrics.csv')
mean_df = df[df['accuracy_mean'].notna()]

# 绘制准确率对比 / Plot accuracy comparison
mean_df.plot(x='config_name', y='accuracy_mean', kind='bar')
plt.ylabel('Accuracy')
plt.title('Ablation Study: Accuracy Comparison')
plt.show()
```

---

## 故障排除 / Troubleshooting

### 问题1: 缺少依赖 / Issue 1: Missing Dependencies

**错误 / Error:** `ImportError: No module named 'yaml'`

**解决方案 / Solution:**
```bash
pip install PyYAML psutil
```

### 问题2: 内存不足 / Issue 2: Out of Memory

**症状 / Symptom:** 处理大型数据集时内存溢出

**解决方案 / Solution:**
- 减少 `--repeats` 参数
- 使用较小的数据集子集
- 增加系统RAM

### 问题3: Git信息获取失败 / Issue 3: Git Info Retrieval Failed

**症状 / Symptom:** `commit_sha: "unknown"`

**解决方案 / Solution:**
- 确保项目在Git仓库中
- 确保Git已安装并在PATH中
- 检查`.git`目录是否存在

---

## 高级用法 / Advanced Usage

### 自定义性能测量 / Custom Performance Measurement

```python
from experiments.performance_metrics import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.start()

# 你的代码 / Your code here
result = my_algorithm(data)

metrics = monitor.stop(n_records=len(data))
print(f"Wall time: {metrics.wall_time_s:.4f}s")
print(f"Throughput: {metrics.names_per_sec:.2f} names/sec")
```

### 自定义Dataset分析 / Custom Dataset Analysis

```python
from experiments.dataset_analyzer import DatasetAnalyzer, generate_dataset_card

analyzer = DatasetAnalyzer("path/to/dataset.json")
stats = analyzer.analyze()

print(f"Records: {stats.n_records}")
print(f"Unique names: {stats.n_unique_names}")

# 生成Dataset Card
generate_dataset_card(stats, "output_path.md")
```

---

## 项目结构 / Project Structure

```
experiments/
├── README.md                  # 本文档 / This document
├── run_bench.py               # 主脚本 / Main script
├── ablation.yaml              # 消融实验配置 / Ablation config
├── performance_metrics.py     # 性能测量模块 / Performance module
└── dataset_analyzer.py        # 数据集分析模块 / Dataset analysis module
```

---

## 引用 / Citation

如果在研究中使用本工具链，请引用：

If you use this toolchain in your research, please cite:

```bibtex
@software{ma2025chinese_bench,
  author = {Ma, Jiaxin},
  title = {Paper-Level Reproducible Experiment Toolchain for Chinese Name Processing v8.0},
  year = {2025},
  url = {https://github.com/Soulbeaters/Chinese-name}
}
```

---

## 贡献 / Contributing

欢迎贡献！请提交Pull Request或Issue。

Contributions are welcome! Please submit a Pull Request or Issue.

---

## 许可证 / License

研究项目 / Research Project
莫斯科国立大学 / Lomonosov Moscow State University

---

## 联系方式 / Contact

**作者 / Author:** Ма Цзясин (Ma Jiaxin)
**GitHub:** https://github.com/Soulbeaters
**项目 / Project:** https://github.com/Soulbeaters/Chinese-name

---

*最后更新 / Last Updated: 2025-12-19*
