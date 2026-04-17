# -*- coding: utf-8 -*-
"""
数据集分析模块 / Dataset Analysis Module

用于分析数据集的统计特性并生成Dataset Card
Analyzes dataset statistics and generates Dataset Cards

作者: Ma Jiaxin
日期: 2025-12-19
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from collections import Counter
import re


@dataclass
class DatasetStatistics:
    """
    数据集统计信息 / Dataset statistics
    """
    # 基本信息 / Basic information
    name: str
    file_path: str
    file_size_mb: float
    file_sha256: str

    # 样本统计 / Sample statistics
    n_records: int
    n_unique_names: int
    n_unique_affiliations: int
    n_unique_dois: int

    # 姓名长度分布 / Name length distribution
    name_length_min: int
    name_length_max: int
    name_length_mean: float
    name_length_median: float

    # Token数量分布 / Token count distribution
    token_count_min: int
    token_count_max: int
    token_count_mean: float
    token_count_median: float

    # 特殊字符统计 / Special character statistics
    has_comma_ratio: float          # 含逗号的比例 / Ratio with comma
    has_hyphen_ratio: float         # 含连字符的比例 / Ratio with hyphen
    has_abbreviation_ratio: float   # 含缩写的比例 / Ratio with abbreviation
    has_chinese_char_ratio: float   # 含中文字符的比例 / Ratio with Chinese characters

    # 机构统计 / Affiliation statistics
    has_affiliation_ratio: float    # 有机构信息的比例 / Ratio with affiliation
    top_affiliations: List[tuple]   # Top 10 机构 / Top 10 affiliations

    def to_dict(self) -> dict:
        """转换为字典 / Convert to dictionary"""
        return asdict(self)


class DatasetAnalyzer:
    """
    数据集分析器 / Dataset Analyzer
    """

    def __init__(self, file_path: str):
        """
        初始化数据集分析器 / Initialize dataset analyzer

        Args:
            file_path: 数据集文件路径 / Dataset file path
        """
        self.file_path = Path(file_path)
        self.name = self.file_path.stem
        self.records = []

    def load_data(self) -> None:
        """
        加载数据 / Load data

        支持JSON和JSONL格式 / Supports JSON and JSONL formats
        """
        with open(self.file_path, 'r', encoding='utf-8') as f:
            if self.file_path.suffix == '.jsonl':
                # JSONL格式 / JSONL format
                self.records = [json.loads(line) for line in f if line.strip()]
            else:
                # JSON格式 / JSON format
                self.records = json.load(f)

    def compute_sha256(self) -> str:
        """
        计算文件的SHA256哈希 / Compute file SHA256 hash

        Returns:
            SHA256哈希值 / SHA256 hash value
        """
        sha256_hash = hashlib.sha256()
        with open(self.file_path, 'rb') as f:
            # 分块读取以处理大文件 / Read in chunks for large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def analyze(self) -> DatasetStatistics:
        """
        执行完整分析 / Perform complete analysis

        Returns:
            DatasetStatistics 对象
        """
        # 加载数据 / Load data
        self.load_data()

        # 计算文件大小 / Calculate file size
        file_size_mb = self.file_path.stat().st_size / (1024 * 1024)

        # 计算哈希 / Compute hash
        file_sha256 = self.compute_sha256()

        # 提取姓名列表 / Extract names
        names = [rec.get('original_name', '') for rec in self.records]
        names = [n for n in names if n]

        # 提取机构列表 / Extract affiliations
        affiliations = [rec.get('affiliation', '') for rec in self.records]
        affiliations_non_empty = [a for a in affiliations if a]

        # 提取DOI列表 / Extract DOIs
        dois = [rec.get('doi', '') for rec in self.records]
        dois = [d for d in dois if d]

        # 基本统计 / Basic statistics
        n_records = len(self.records)
        n_unique_names = len(set(names))
        n_unique_affiliations = len(set(affiliations_non_empty))
        n_unique_dois = len(set(dois))

        # 姓名长度分布 / Name length distribution
        name_lengths = [len(name) for name in names]
        name_length_min = min(name_lengths) if name_lengths else 0
        name_length_max = max(name_lengths) if name_lengths else 0
        name_length_mean = sum(name_lengths) / len(name_lengths) if name_lengths else 0.0
        name_length_median = sorted(name_lengths)[len(name_lengths) // 2] if name_lengths else 0

        # Token数量分布 / Token count distribution
        token_counts = [len(name.split()) for name in names]
        token_count_min = min(token_counts) if token_counts else 0
        token_count_max = max(token_counts) if token_counts else 0
        token_count_mean = sum(token_counts) / len(token_counts) if token_counts else 0.0
        token_count_median = sorted(token_counts)[len(token_counts) // 2] if token_counts else 0

        # 特殊字符统计 / Special character statistics
        has_comma_count = sum(1 for name in names if ',' in name)
        has_hyphen_count = sum(1 for name in names if '-' in name)
        has_abbreviation_count = sum(1 for name in names if re.search(r'\b[A-Z]\.$', name))
        has_chinese_count = sum(1 for name in names if re.search(r'[\u4e00-\u9fff]', name))

        n = len(names) if names else 1
        has_comma_ratio = has_comma_count / n
        has_hyphen_ratio = has_hyphen_count / n
        has_abbreviation_ratio = has_abbreviation_count / n
        has_chinese_char_ratio = has_chinese_count / n

        # 机构统计 / Affiliation statistics
        has_affiliation_ratio = len(affiliations_non_empty) / n_records if n_records > 0 else 0.0
        affiliation_counter = Counter(affiliations_non_empty)
        top_affiliations = affiliation_counter.most_common(10)

        return DatasetStatistics(
            name=self.name,
            file_path=str(self.file_path),
            file_size_mb=round(file_size_mb, 2),
            file_sha256=file_sha256,
            n_records=n_records,
            n_unique_names=n_unique_names,
            n_unique_affiliations=n_unique_affiliations,
            n_unique_dois=n_unique_dois,
            name_length_min=name_length_min,
            name_length_max=name_length_max,
            name_length_mean=round(name_length_mean, 2),
            name_length_median=name_length_median,
            token_count_min=token_count_min,
            token_count_max=token_count_max,
            token_count_mean=round(token_count_mean, 2),
            token_count_median=token_count_median,
            has_comma_ratio=round(has_comma_ratio, 4),
            has_hyphen_ratio=round(has_hyphen_ratio, 4),
            has_abbreviation_ratio=round(has_abbreviation_ratio, 4),
            has_chinese_char_ratio=round(has_chinese_char_ratio, 4),
            has_affiliation_ratio=round(has_affiliation_ratio, 4),
            top_affiliations=top_affiliations
        )


def generate_dataset_card(stats: DatasetStatistics, output_path: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    生成Dataset Card (Markdown格式) / Generate Dataset Card (Markdown format)

    Args:
        stats: 数据集统计信息 / Dataset statistics
        output_path: 输出文件路径 / Output file path
        metadata: 可选的API元数据 / Optional API metadata
    """
    # API元数据部分 / API metadata section
    api_section = ""
    if metadata:
        api_section = "\n### API & Collection Metadata\n\n"
        if 'api_version' in metadata:
            api_section += f"**API Version:** {metadata['api_version']}\n\n"
        if 'query_url' in metadata:
            api_section += f"**Query URL:** `{metadata['query_url']}`\n\n"
        if 'query_params' in metadata:
            api_section += "**Query Parameters:**\n"
            for key, value in metadata['query_params'].items():
                api_section += f"- `{key}`: {value}\n"
            api_section += "\n"
        if 'response_headers' in metadata:
            api_section += "**Response Headers (Rate Limiting):**\n"
            for key, value in metadata['response_headers'].items():
                api_section += f"- `{key}`: {value}\n"
            api_section += "\n"
        if 'collection_time' in metadata:
            api_section += f"**Collection Time Window:** {metadata['collection_time']['start']} to {metadata['collection_time']['end']}\n\n"
        if 'user_agent' in metadata:
            api_section += f"**User Agent:** {metadata['user_agent']}\n\n"
        if 'polite_pool' in metadata:
            api_section += f"**Polite Pool:** {metadata['polite_pool']}\n\n"

    card_content = f"""# Dataset Card: {stats.name}

**Generated by:** Chinese Name Processing System v8.0
**Date:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}

---

## Dataset Description

### Motivation

**TODO**: 描述创建此数据集的动机和目的。
**TODO**: Describe the motivation and purpose for creating this dataset.

---

### Source & Collection

**TODO**: 描述数据来源和收集方法。
**TODO**: Describe the data source and collection methodology.
{api_section}
**File Information:**
- File path: `{stats.file_path}`
- File size: {stats.file_size_mb} MB
- SHA-256: `{stats.file_sha256}`

---

### Filtering

**TODO**: 描述数据过滤和清洗步骤。
**TODO**: Describe data filtering and cleaning procedures.

---

### Composition (自动填充 / Auto-filled)

**Sample Count:**
- Total records: {stats.n_records:,}
- Unique names: {stats.n_unique_names:,}
- Unique affiliations: {stats.n_unique_affiliations:,}
- Unique DOIs: {stats.n_unique_dois:,}

**Name Characteristics:**
- Length range: {stats.name_length_min} - {stats.name_length_max} characters
- Average length: {stats.name_length_mean:.2f} characters
- Median length: {stats.name_length_median} characters

**Token Distribution:**
- Token count range: {stats.token_count_min} - {stats.token_count_max} tokens
- Average tokens: {stats.token_count_mean:.2f}
- Median tokens: {stats.token_count_median}

**Special Characters:**
- Names with commas: {stats.has_comma_ratio*100:.2f}%
- Names with hyphens: {stats.has_hyphen_ratio*100:.2f}%
- Names with abbreviations: {stats.has_abbreviation_ratio*100:.2f}%
- Names with Chinese characters: {stats.has_chinese_char_ratio*100:.2f}%

**Affiliation Coverage:**
- Records with affiliation: {stats.has_affiliation_ratio*100:.2f}%

**Top 10 Affiliations:**
"""

    for i, (affil, count) in enumerate(stats.top_affiliations, 1):
        card_content += f"{i}. {affil[:100]}... ({count:,} records)\n"

    card_content += """
---

### Labeling

**TODO**: 描述数据标注方法和质量保证措施。
**TODO**: Describe data labeling methodology and quality assurance measures.

---

### Limitations

**TODO**: 描述数据集的已知限制和注意事项。
**TODO**: Describe known limitations and considerations for this dataset.

**Known biases:**
- TODO: List any known biases in the dataset

**Representativeness:**
- TODO: Discuss how representative this dataset is of the target population

**Data quality issues:**
- TODO: Document any known data quality issues

---

## Usage Recommendations

**Recommended uses:**
- TODO: Describe recommended use cases

**Not recommended for:**
- TODO: Describe scenarios where this dataset should not be used

---

## Citation

**TODO**: 提供数据集的引用信息。
**TODO**: Provide citation information for this dataset.

---

*This dataset card was automatically generated. Please fill in the TODO sections with appropriate information.*
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(card_content)


if __name__ == "__main__":
    # 测试示例 / Test example
    import sys
    if len(sys.argv) > 1:
        analyzer = DatasetAnalyzer(sys.argv[1])
        stats = analyzer.analyze()
        print(json.dumps(stats.to_dict(), indent=2, ensure_ascii=False))

        output_path = sys.argv[1].replace('.json', '.dataset_card.md')
        generate_dataset_card(stats, output_path)
        print(f"\nDataset card generated: {output_path}")
    else:
        print("Usage: python dataset_analyzer.py <dataset_file>")
