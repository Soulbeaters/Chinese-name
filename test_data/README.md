# 测试数据集 / Тестовый набор данных / Test Dataset

## 数据概述 / Обзор данных / Data Overview

本目录包含项目测试所需的样本数据集。这是从完整ORCID数据集中提取的代表性样本，用于验证中文姓名处理和作者识别系统。

Эта директория содержит образцы наборов данных, необходимых для тестирования проекта. Это репрезентативная выборка из полного набора данных ORCID для верификации обработки китайских имён и системы идентификации авторов.

This directory contains sample datasets required for project testing. This is a representative sample from the full ORCID dataset for verifying Chinese name processing and author identification system.

---

## 数据文件 / Файлы данных / Data Files

### sample_orcid_data.json (0.86 MB)

**描述 / Описание / Description:**
样本ORCID数据集，包含带ORCID标识符的作者记录和相关出版物信息。

Образец набора данных ORCID с записями авторов с идентификаторами ORCID и информацией о соответствующих публикациях.

Sample ORCID dataset containing author records with ORCID identifiers and related publication information.

**统计信息 / Статистика / Statistics:**
- ORCID作者 / Авторов с ORCID / ORCID authors: 100
- 总作者记录 / Всего записей авторов / Total author records: 1,000
- 相关出版物 / Связанных публикаций / Related publications: 100

**数据结构 / Структура данных / Data Structure:**
```json
{
  "works": {},                    // 文章数据 / Данные о работах
  "all_authors": [],              // 所有作者记录 / Все записи авторов
  "orcid_authors": {},            // 带ORCID的作者 / Авторы с ORCID
  "orcid_publications": {},       // ORCID作者的出版物 / Публикации авторов ORCID
  "author_coauthors": {},         // 合著者关系 / Отношения соавторства
  "statistics": {}                // 统计信息 / Статистика
}
```

**字段说明 / Описание полей / Field Descriptions:**

#### all_authors (列表 / Список / List)
```json
{
  "original_name": "Wei-Hua Li",
  "given": "Wei-Hua",
  "family": "Li",
  "orcid": "0000-0002-4054-2643",
  "affiliation": ["College of ..."],
  "sequence": "first"
}
```

#### orcid_authors (字典 / Словарь / Dictionary)
```json
{
  "0000-0002-4054-2643": {
    "orcid": "0000-0002-4054-2643",
    "given": "Wei-Hua",
    "family": "Li",
    "name": "Wei-Hua Li",
    "authenticated": false,
    "affiliation": [...]
  }
}
```

---

## 数据来源 / Источник данных / Data Source

### 完整数据集 / Полный набор данных / Full Dataset

**位置 / Местоположение / Location:**
`real_orcid_data/` 目录（不在GitHub仓库中）

**大小 / Размер / Size:** ~490 MB

**内容 / Содержание / Contents:**
- `full_orcid_data.json` (343 MB) - 完整ORCID数据
- `crossref_authors_formatted.json` (87 MB) - Crossref作者数据
- `article_authors_map.json` (53 MB) - 文章-作者映射
- `orcid_history.json` (6.5 MB) - ORCID历史记录

**完整数据统计 / Полная статистика / Full Statistics:**
- 总文章数 / Всего работ: 31,502
- 总作者记录 / Всего записей авторов: 410,724
- 带ORCID作者 / Авторов с ORCID: 1,333
- 相关出版物 / Связанных публикаций: 1,309

### 样本数据说明 / О выборке / Sample Description

**样本选择方法 / Метод выборки / Sampling Method:**
- 随机选择前100个ORCID作者 / Первые 100 авторов с ORCID / First 100 ORCID authors
- 包含相关的出版物和合著者信息 / Включает связанные публикации и соавторов / Includes related publications and coauthors
- 保持数据结构完整性 / Сохраняет целостность структуры / Maintains data structure integrity

**样本代表性 / Репрезентативность / Representativeness:**
- ✅ 包含中文作者姓名 / Содержит китайские имена
- ✅ 包含ORCID认证记录 / Содержит записи с ORCID
- ✅ 包含多机构信息 / Содержит информацию о разных учреждениях
- ✅ 适合功能验证和演示 / Подходит для верификации и демонстрации

---

## 数据用途 / Использование данных / Data Usage

### 1. 功能测试 / Функциональное тестирование / Functional Testing
验证中文姓名处理、拼音转换、俄语转写等核心功能。

Верификация основных функций обработки китайских имён, конвертации пиньинь, русской транслитерации.

Verify core functions of Chinese name processing, Pinyin conversion, and Russian transliteration.

### 2. 系统演示 / Демонстрация системы / System Demonstration
为导师和评审展示系统功能。

Демонстрация функциональности системы для научного руководителя и рецензентов.

Demonstrate system functionality to advisor and reviewers.

### 3. 可复现研究 / Воспроизводимые исследования / Reproducible Research
其他研究者可以使用样本数据验证结果。

Другие исследователи могут использовать образцы для верификации результатов.

Other researchers can use sample data to verify results.

---

## 使用方法 / Использование / Usage

### 快速开始 / Быстрый старт / Quick Start

```bash
# Clone项目
git clone https://github.com/Soulbeaters/Chinese-name.git
cd Chinese-name

# 安装依赖
pip install -r requirements.txt

# 使用样本数据运行测试
python comprehensive_test_v5.py --test-data test_data/sample_orcid_data.json

# 运行完整验证
python comprehensive_validation_v5.py --data test_data/sample_orcid_data.json
```

### 完整数据使用 / Использование полных данных / Full Data Usage

如需使用完整数据集进行大规模测试：

Для крупномасштабного тестирования с полным набором данных:

For large-scale testing with the full dataset:

1. **联系项目维护者获取完整数据 / Свяжитесь с maintainer для получения полных данных / Contact project maintainer for full data**
   - Email: (提供联系方式)
   - GitHub: [@Soulbeaters](https://github.com/Soulbeaters)

2. **自行从Crossref和ORCID API收集数据 / Самостоятельный сбор данных из API / Collect data yourself from APIs**
   - 使用项目中的数据收集脚本
   - 需要网络连接和API访问权限

---

## 数据质量 / Качество данных / Data Quality

### 数据完整性 / Целостность / Integrity
- ✅ JSON格式验证通过
- ✅ 所有必需字段完整
- ✅ ORCID格式规范
- ✅ 无重复记录

### 数据准确性 / Точность / Accuracy
- ✅ 数据来自官方Crossref和ORCID数据库
- ✅ ORCID标识符经过验证
- ✅ 作者姓名保持原始格式
- ✅ 机构信息准确

### 隐私保护 / Защита конфиденциальности / Privacy Protection
- ✅ 所有数据来自公开学术数据库
- ✅ 不包含个人联系方式
- ✅ ORCID是公开研究者标识符
- ✅ 符合数据使用政策

---

## 数据更新 / Обновления / Updates

**当前版本 / Текущая версия / Current Version:** 1.0.0
**创建日期 / Дата создания / Creation Date:** 2025-11-11
**数据来源日期 / Дата данных / Data Source Date:** 2025-10-10

**更新频率 / Частота обновлений / Update Frequency:**
- 样本数据：根据项目需求不定期更新
- Образцы данных: обновляются по мере необходимости
- Sample data: Updated as needed for project requirements

---

## 性能基准 / Производительность / Performance Benchmarks

使用样本数据的典型性能指标：

Типичные показатели производительности с образцами данных:

Typical performance metrics with sample data:

**中文姓名识别 / Распознавание китайских имён / Chinese Name Recognition:**
- 处理速度 / Скорость: ~0.5秒/1000条记录
- 准确率 / Точность: >95%

**拼音转换 / Конвертация пиньинь / Pinyin Conversion:**
- 处理速度 / Скорость: ~0.2秒/1000条记录
- 准确率 / Точность: >98%

**俄语转写 / Русская транслитерация / Russian Transliteration:**
- 处理速度 / Скорость: ~0.3秒/1000条记录
- 准确率 / Точность: >90%

---

## 引用说明 / Цитирование / Citation

如果在研究中使用此数据集，请引用：

Если вы используете этот набор данных в исследованиях, пожалуйста, цитируйте:

If you use this dataset in research, please cite:

```
Ma Jiaxin. (2025). Chinese Name Processing System for Academic Publications.
Moscow State University.
GitHub: https://github.com/Soulbeaters/Chinese-name
Data: Sample from Crossref and ORCID public databases
```

---

## 相关资源 / Связанные ресурсы / Related Resources

### 官方API文档 / Официальная документация API / Official API Documentation
- [Crossref API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [ORCID API](https://info.orcid.org/documentation/api-tutorials/)

### 数据标准 / Стандарты данных / Data Standards
- [ORCID标识符规范](https://support.orcid.org/hc/en-us/articles/360006897674)
- [DOI规范](https://www.doi.org/doi-handbook/)

---

## 许可证 / Лицензия / License

样本数据用于科研和教育目的，遵循MIT许可证。数据来源于Crossref和ORCID公开数据库。

Образцы данных предназначены для исследовательских и образовательных целей, следуют лицензии MIT. Данные получены из публичных баз данных Crossref и ORCID.

Sample data is for research and educational purposes, following the MIT license. Data is sourced from Crossref and ORCID public databases.

---

## 联系方式 / Контакты / Contact

如有关于数据的问题或需要完整数据集，请联系：

По вопросам о данных или для получения полного набора данных обращайтесь:

For questions about the data or to obtain the full dataset, please contact:

**项目维护者 / Maintainer:** Ма Цзясин (Ma Jiaxin)
**机构 / Учреждение / Institution:** МГУ имени М.В. Ломоносова
**GitHub:** https://github.com/Soulbeaters/Chinese-name
**仓库 / Репозиторий / Repository:** https://github.com/Soulbeaters/Chinese-name
