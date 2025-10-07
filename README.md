# Chinese Name Processing System / Система обработки китайских имен

**Author / Автор:** Ма Цзясин (Ma Jiaxin)
**Institution / Учреждение:** Московский государственный университет имени М.В.Ломоносова (МГУ)
**Project / Проект:** ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных

---

## Overview / Обзор

Comprehensive Chinese name processing system for scientometric databases.

Комплексная система обработки китайских имен для наукометрических баз данных.

### Core Features / Основные возможности

- ✅ **Name order detection** / Определение порядка имени (姓-名 vs 名-姓)
- ✅ **First author identification** / Определение первого автора
- ✅ **Author list parsing** / Разбор списков авторов
- ✅ **Multi-language transliteration** / Многоязычная транслитерация
  - Chinese → Pinyin (English) / Китайский → Пиньинь
  - Chinese → Palladius (Russian) / Китайский → Палладий
- ✅ **41,923 character coverage** / Покрытие 41,923 иероглифов
- ✅ **387 surname database** / База 387 фамилий

---

## Installation / Установка

```bash
git clone https://github.com/Soulbeaters/Chinese-name.git
cd Chinese-name
pip install -r requirements.txt
```

**Requirements / Требования:** Python 3.11+, pypinyin 0.55.0+

---

## Quick Start / Быстрый старт

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

```bash
pytest tests/ -v
```

**Result / Результат:** 31/31 tests pass (100%)

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

*Last Updated: October 2025*
