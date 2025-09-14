# ChineseNameProcessor - 中文姓名处理模块

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/istina/chinese-name-processor)

**Русский** | **中文** | **English**

ИСТИНА系统中文姓名处理和验证模块 - 版本2.0.0重大更新

## 🚀 快速开始 / Quick Start

```bash
# 安装 / Installation
pip install -e .

# 基本使用 / Basic Usage
from src import create_default_processor

processor = create_default_processor()
result = processor.process_name("李小明")
print(f"姓氏: {result.components.surname}")
print(f"名字: {result.components.first_name}")
print(f"置信度: {result.confidence_score:.3f}")
```

## 📁 项目结构 / Project Structure

```
C:\program 1 in 2025\
├── src/                    # 源代码 / Source code
│   ├── chinese_name_processor.py    # 核心处理器 / Core processor
│   ├── transliteration_db.py        # 音译数据库 / Transliteration database
│   └── surname_trie.py              # Trie树实现 / Trie implementation
├── tests/                  # 测试文件 / Test files
├── docs/                   # 文档 / Documentation
│   └── README_ChineseNameProcessor.md  # 详细文档 / Detailed docs
├── examples/               # 示例代码 / Example code
├── utils/                  # 工具脚本 / Utility scripts
├── setup.py               # 安装配置 / Setup configuration
├── requirements.txt       # 依赖列表 / Dependencies
└── LICENSE               # 许可证 / License
```

## ✨ 新功能 v2.0.0 / New Features v2.0.0

- ✅ **Trie树高性能搜索** - O(n)→O(m)性能提升
- ✅ **混合文字处理** - 支持"张John", "David李"格式
- ✅ **动态语料库学习** - 自动发现新姓氏
- ✅ **扩展音译数据库** - 支持变体和连字符
- ✅ **多级置信度评估** - 7级精确评分系统
- ✅ **关键错误修复** - 6个重要问题解决

## 📊 性能指标 / Performance Metrics

- **处理速度**: 300-2000 姓名/秒
- **准确率**: 有效案例100%
- **内存使用**: Trie优化，低内存消耗
- **并发支持**: 线程安全设计

## 🧪 测试 / Testing

```bash
# 运行所有测试 / Run all tests
python -m pytest tests/

# 特定功能测试 / Specific feature tests
python tests/test_trie_integration.py
python tests/test_mixed_script.py
python tests/test_corpus_learning.py
```

## 📖 文档 / Documentation

详细文档请参阅：[完整文档](docs/README_ChineseNameProcessor.md)

## 🏛️ ИСТИНА系统集成 / ISTINA System Integration

本模块专为莫斯科国立大学ИСТИНА系统设计，支持：
- 科学计量数据处理
- 作者姓名标准化
- 多语言姓名识别
- 大规模数据验证

## 👥 作者 / Authors

**Ма Цзясин (Ma Jiaxin)**
博士生 / PhD Student
莫斯科国立大学计算机科学系 / MSU Computer Science Department
导师: д.ф.-м.н. профессор Васенин В.А.

## 📄 许可证 / License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

© 2025 Moscow State University ISTINA Development Team