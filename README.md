# Chinese Name Processing System / Система обработки китайских имен

**Author / Автор:** Ма Цзясин (Ma Jiaxin)
**Institution / Учреждение:** Московский государственный университет имени М.В.Ломоносова (МГУ)
**Project / Проект:** ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных

---

## Overview / Обзор

Comprehensive Chinese name processing system for scientometric databases.

Комплексная система обработки китайских имен для наукометрических баз данных.

### Core Features / Основные возможности

- ✅ **v8.0 Surname Position Identifier** / Идентификатор позиции фамилии v8.0 **[LATEST]**
  - Fellegi-Sunter style scoring framework / Фреймворк оценки в стиле Fellegi-Sunter
  - **Crossref: 95.8%** accuracy (v7: 86.25%) / Точность на Crossref
  - **ORCID: 96.35%** accuracy (v7: 90.47%) / Точность на ORCID
  - **ISTINA: 80.03%** accuracy (v7: 80.0%) / Точность на ИСТИНА
  - Source-specific strategies (Crossref/ORCID/ISTINA) / Стратегии для разных источников
  - Batch consistency adjustment / Пакетная коррекция согласованности
  - Single syllable optimization / Оптимизация одно слоговых имен
- ✅ **Name order detection** / Определение порядка имени (姓-名 vs 名-姓)
- ✅ **First author identification** / Определение первого автора
- ✅ **Author list parsing** / Разбор списков авторов
- ✅ **Multi-language transliteration** / Многоязычная транслитерация
  - Chinese → Pinyin (English) / Китайский → Пиньинь
  - Chinese → Palladius (Russian) / Китайский → Палладий
- ✅ **41,923 character coverage** / Покрытие 41,923 иероглифов
- ✅ **387 surname database** (+40 variant mappings, +289 exclusions) / База 387 фамилий

---

## Installation / Установка

```bash
git clone https://github.com/Soulbeaters/Chinese-name.git
cd Chinese-name
pip install -r requirements.txt
```

**Requirements / Требования:** Python 3.11+, pypinyin 0.55.0+

### Test Data / Тестовые данные

项目包含样本测试数据集，位于 `test_data/` 目录：

Проект включает образец тестового набора данных в директории `test_data/`:

The project includes a sample test dataset in the `test_data/` directory:

**数据文件 / Файлы данных / Data Files:**
- `sample_orcid_data.json` (0.86MB)
  - 100 ORCID authors / 100 авторов с ORCID
  - 1,000 author records / 1,000 записей авторов
  - 100 related publications / 100 связанных публикаций

**数据来源 / Источник / Source:**
- ✅ Sample from Crossref and ORCID public databases / Выборка из публичных баз данных
- ✅ No personal privacy information / Без личных данных
- ✅ For system verification and reproducible research / Для верификации и воспроизводимых исследований

**详细说明 / Подробное описание / Detailed Description:**
查看 [`test_data/README.md`](test_data/README.md) 获取完整的数据说明文档。

См. [`test_data/README.md`](test_data/README.md) для полной документации по данным.

See [`test_data/README.md`](test_data/README.md) for complete data documentation.

**完整数据集下载 / Скачать полный набор данных / Full Dataset Download:**

GitHub仓库中包含样本数据（0.86MB），完整测试数据集（~490MB）可通过Google Drive获取：

Репозиторий GitHub содержит образцы данных (0.86MB), полный набор тестовых данных (~490MB) доступен через Google Drive:

The GitHub repository contains sample data (0.86MB), the full test dataset (~490MB) is available via Google Drive:

🔗 **[下载完整数据集 / Скачать полные данные / Download Full Dataset](https://drive.google.com/drive/folders/1BHyZJt8MhTPz6isMRoBIT2NVQuf1H6Eq?usp=sharing)**

**完整数据集内容 / Содержание полного набора / Full Dataset Contents:**
- `full_orcid_data.json` (343 MB) - 31,502篇文章，410,724条作者记录
- `crossref_authors_formatted.json` (87 MB) - Crossref格式化作者数据
- `article_authors_map.json` (53 MB) - 文章-作者映射关系
- `orcid_history.json` (6.5 MB) - ORCID历史记录数据

---

## Quick Start / Быстрый старт

### v8.0 Surname Position Identifier (LATEST / ПОСЛЕДНЯЯ ВЕРСИЯ)

```python
from src.surname_identifier_v8 import identify_surname_position_v8

# Single record identification / Идентификация одной записи
order, confidence, reason = identify_surname_position_v8(
    original_name="Tianxiang Tang",
    affiliation="Tsinghua University, Beijing, China",
    source="CROSSREF"  # CROSSREF / ORCID / ISTINA
)

print(f"Order: {order}")           # "given_first"
print(f"Confidence: {confidence}") # 0.92
print(f"Reason: {reason}")         # "CHINESE: CN_SURNAME_LAST_ONLY, FIRST_VALID_PY_NAME(2syl)..."

# More examples / Дополнительные примеры
identify_surname_position_v8("David Smith")[0]              # "given_first"
identify_surname_position_v8("Zhang Tianxiang", source="ISTINA")[0]  # "family_first"
identify_surname_position_v8("Liu W.")[0]                   # "family_first" (abbreviation)

# Batch processing with consistency adjustment / Пакетная обработка с коррекцией
from src.surname_identifier_v8 import batch_identify_surname_position_v8, NameRecord

records = [
    NameRecord(record_id="1", name_raw="Tang Tianxiang", person_id="P001", source="CROSSREF"),
    NameRecord(record_id="2", name_raw="Tianxiang Tang", person_id="P001", source="CROSSREF"),
]

decisions = batch_identify_surname_position_v8(
    records,
    enable_person_consistency=True,  # Person-level consistency
    enable_pub_consistency=True      # Publication-level consistency
)

for rid, decision in decisions.items():
    print(f"{rid}: {decision.order} (conf: {decision.confidence:.2f})")
```

### Original Chinese Name Processing / Обработка китайских имён

```python
from src.chinese_name_processor import create_default_processor
from data import to_pinyin_string, to_russian

# Initialize / Инициализация
processor = create_default_processor()

# Process name / Обработка имени
result = processor.process_name("马嘉星")
print(f"Surname: {result.components.surname}")      # 马
print(f"Given name: {result.components.first_name}") # 嘉星

# Detect order / Определение порядка
order = processor.detect_name_order("Zhang Ming")
print(f"Order: {order['detected_order']}")  # SURNAME_FIRST

# Parse authors / Разбор авторов
authors = processor.parse_author_list("Zhang San; Li Ming; Wang Wu")
for author in authors:
    print(f"{author['surname']} {author['given_name']}")
    print(f"First author: {author['is_first_author']}")

# Transliteration / Транслитерация
print(to_pinyin_string("马嘉星"))  # MA JIA XING
print(to_russian("马嘉星"))        # Мацзясин
```

---

## Project Structure / Структура проекта

```
Chinese-name/
├── src/                          # Core logic (348 lines)
│   ├── chinese_name_processor.py # Main processor
│   └── name_order_detector.py    # Order detection
├── data/                         # Databases (416 lines)
│   ├── chinese_surnames.py       # 387 surnames
│   ├── chinese_chars.py          # 41,923 characters
│   ├── pinyin_mapping.py         # Pinyin transliteration
│   └── palladius_mapping.py      # Russian transliteration
├── tests/                        # Test suite
│   └── test_name_order_detector.py # 31 tests (100% pass)
├── examples/                     # Usage examples
│   └── demo.py                   # Complete demonstration
└── README.md                     # Documentation
```

---

## Testing / Тестирование

### Unit Tests / Модульные тесты

```bash
pytest tests/ -v
```

**Result / Результат:** 31/31 tests pass (100%)

### Comprehensive Testing / Комплексное тестирование

The project includes comprehensive test scripts with command-line parameter support for flexible data source configuration and multilingual output (Chinese, Russian, English).

Проект включает комплексные тестовые скрипты с поддержкой параметров командной строки для гибкой настройки источников данных и многоязычного вывода (китайский, русский, английский).

#### Quick Start / Быстрый старт

```bash
# v5.0 comprehensive test (default: advisor data, Russian output)
# v5.0 комплексный тест (по умолчанию: данные руководителя, русский вывод)
python comprehensive_test_v5.py

# v5.0 comprehensive validation (default: advisor data, Russian output)
# v5.0 комплексная валидация (по умолчанию: данные руководителя, русский вывод)
python comprehensive_validation_v5.py
```

#### Using Custom Data Paths / Использование пользовательских путей

```bash
# Specify custom data path
# Указать пользовательский путь к данным
python comprehensive_test_v5.py --data-path "C:/custom/path/crossref_authors.json"

# Specify output file path
# Указать путь к выходному файлу
python comprehensive_test_v5.py \
    --data-path "C:/custom/data.json" \
    --output "C:/custom/results.json"

# English output
# Английский вывод
python comprehensive_test_v5.py --language en

# Chinese output
# Китайский вывод
python comprehensive_validation_v5.py --language zh
```

#### View Help Information / Просмотр справки

```bash
python comprehensive_test_v5.py --help
python comprehensive_validation_v5.py --help
```

**Features / Особенности / 功能特性:**
- ✅ Flexible data paths / Гибкие пути к данным / 灵活的数据路径
- ✅ Multilingual output (zh/ru/en) / Многоязычный вывод / 多语言输出
- ✅ Quality validation / Проверка качества / 质量验证
- ✅ Detailed reports / Детальные отчеты / 详细报告

**Default Data Path / Путь к данным по умолчанию:**
- `C:\istina\materia 材料\测试表单\crossref_authors.json`

---

## API Reference / Справочник API

### ChineseNameProcessor

```python
processor = create_default_processor()

# Process name / Обработка имени
result = processor.process_name(name: str) → NameResult

# Detect order / Определение порядка
order = processor.detect_name_order(name: str) → Dict
# Returns: order_value (1: surname-first, 0: undetermined, -1: given-first)

# Parse authors / Разбор авторов
authors = processor.parse_author_list(authors: str) → List[Dict]

# Batch processing / Пакетная обработка
results = processor.batch_detect_name_orders(names: List[str]) → List[Dict]
```

### Data Module / Модуль данных

```python
from data import (
    to_pinyin_string,      # Chinese → Pinyin
    to_russian,            # Chinese → Russian
    is_surname,            # Check if surname
    get_surname_from_text, # Extract surname
)
```

---

## Technical Specifications / Технические характеристики

| Feature / Особенность | Value / Значение |
|----------------------|------------------|
| Code size / Размер кода | 764 lines |
| Character coverage / Покрытие символов | 41,923 |
| Surname database / База фамилий | 387 |
| Processing speed / Скорость | ~227K names/sec |
| Test coverage / Покрытие тестами | 100% (31/31) |

### Name Order Detection / Определение порядка

Algorithm based on ISTINA system / Алгоритм на основе системы ИСТИНА:

1. Frequency analysis (threshold ≥30) / Частотный анализ (порог ≥30)
2. Initial detection / Определение инициалов
3. Patronymic recognition / Распознавание отчеств
4. Order value: **1** (姓-名), **0** (undetermined), **-1** (名-姓)

---

## Data Sources / Источники данных

- **Surnames / Фамилии:** China 2020 census / Перепись Китая 2020
- **Characters / Символы:** pypinyin library / библиотека pypinyin (41,923)
- **Palladius / Палладий:** Standard Russian transliteration system

---

## ISTINA Integration / Интеграция с ИСТИНА

Compatible with ISTINA scientometric system / Совместимость с системой ИСТИНА:

- ✅ Order value system (1, 0, -1) / Система значений порядка
- ✅ First author separation / Разделение первого автора
- ✅ Frequency threshold (≥30) / Порог частоты
- ✅ Batch processing / Пакетная обработка

---

## Running Demo / Запуск демонстрации

```bash
python examples/demo.py
```

**Output examples / Примеры вывода:**

```
马嘉星:
  Surname: 马, Given name: 嘉星
  Pinyin: MA JIA XING
  Russian: Мацзясин

欧阳锋:
  Surname: 欧阳, Given name: 锋
  Pinyin: OU YANG FENG
  Russian: Оуянфэн
```

---

## License / Лицензия

Research project at Lomonosov Moscow State University.

Исследовательский проект МГУ имени М.В.Ломоносова.

---

## Author / Автор

**Ма Цзясин (Ma Jiaxin)**
PhD Student, Computer Science
Lomonosov Moscow State University

**Research Focus / Направление исследований:**
Data Input and Verification in Interactive Scientometric Systems
Ввод и верификация данных в интерактивных наукометрических системах

---

## Contact / Контакты

- GitHub: https://github.com/Soulbeaters
- Repository: https://github.com/Soulbeaters/Chinese-name

---

*Last Updated: November 2025 (v8.0)*
