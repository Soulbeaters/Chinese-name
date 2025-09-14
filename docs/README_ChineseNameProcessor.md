# ChineseNameProcessor - Модуль обработки китайских имён для системы ИСТИНА

## Описание / Description

**Русский:**
Данный модуль реализует объектно-ориентированный подход к обработке и верификации китайских имён в рамках системы ИСТИНА (Интеллектуальная Система Тематического Исследования НАукометрических данных). Модуль разработан для решения проблемы 1.1 из отчёта по научно-исследовательской деятельности: переход от процедурного к объектно-ориентированному подходу для повышения надёжности и поддерживаемости кода.

**English:**
This module implements an object-oriented approach to processing and verifying Chinese names within the ISTINA system (Intelligent System for Thematic Investigation of Scientometric data). The module was developed to address problem 1.1 from the research activity report: transitioning from procedural to object-oriented approach to improve code reliability and maintainability.

**中文:**
该模块在ИСТИНА系统（智能科学计量数据专题研究系统）框架内实现了中文姓名处理和验证的面向对象方法。该模块旨在解决科研活动报告中的问题1.1：从过程化方法转向面向对象方法，以提高代码的可靠性和可维护性。

---

## Автор / Author / 作者

**Ма Цзясин** (Ma Jiaxin)
Аспирант кафедры вычислительных технологий
Московский Государственный Университет им. М.В. Ломоносова
Научный руководитель: д.ф.-м.н. профессор **Васенин В.А.**

---

## Архитектура модуля / Module Architecture / 模块架构

### Основные классы / Main Classes / 主要类

#### 1. `ChineseNameProcessor`
**Русский:** Основной класс-координатор, предоставляющий единый интерфейс для обработки китайских имён.

**English:** Main coordinator class providing unified interface for Chinese name processing.

**中文:** 主要协调器类，为中文姓名处理提供统一接口。

**Возможности / Capabilities / 功能:**
- Распознавание чистых китайских имён (иероглифы) / Pure Chinese name recognition (characters) / 纯中文姓名识别（汉字）
- Обработка транслитерированных имён (пиньинь, система Палладия, Уэйд-Джайлс) / Transliterated name processing (pinyin, Palladius, Wade-Giles systems) / 音译姓名处理（拼音、俄文转写、威妥玛系统）
- **НОВОЕ:** Анализ имён со смешанным письмом (китайский + латиница) / **NEW:** Mixed script name analysis (Chinese + Latin) / **新功能:** 混合文字姓名分析（中文+拉丁文）
- **НОВОЕ:** Высокопроизводительный поиск с Trie-деревом / **NEW:** High-performance search with Trie tree / **新功能:** 基于Trie树的高性能搜索
- Верификация с многоуровневой оценкой достоверности / Multi-level confidence scoring verification / 多级可信度评估验证
- **НОВОЕ:** Генерация детального пути принятия решений / **NEW:** Detailed decision path generation / **新功能:** 详细决策路径生成

#### 2. `SurnameDatabase`
**Русский:** Класс управления базой данных китайских фамилий с поддержкой эффективного поиска.

**English:** Chinese surname database management class with efficient search support.

**中文:** 中文姓氏数据库管理类，支持高效搜索。

**Функционал / Functionality / 功能:**
- **ОБНОВЛЕНО:** Поиск по иероглифам, пиньинь, системе Палладия и Уэйд-Джайлс / **UPDATED:** Search by characters, pinyin, Palladius and Wade-Giles systems / **已更新:** 按汉字、拼音、俄文转写和威妥玛系统搜索
- **УЛУЧШЕНО:** Поддержка составных фамилий с Trie-оптимизацией / **IMPROVED:** Compound surname support with Trie optimization / **已改进:** 带Trie优化的复合姓氏支持
- Динамическое добавление новых фамилий / Dynamic addition of new surnames / 动态添加新姓氏
- **НОВОЕ:** Обучение на текстовых корпусах (learn_from_text_corpus) / **NEW:** Learning from text corpora (learn_from_text_corpus) / **新功能:** 从文本语料库学习 (learn_from_text_corpus)
- **НОВОЕ:** Расширенная база транслитераций с вариантами написания / **NEW:** Extended transliteration database with spelling variants / **新功能:** 扩展的音译数据库支持拼写变体
- JSON импорт/экспорт / JSON import/export / JSON导入/导出

#### 3. Классы данных / Data Classes / 数据类

- **`NameComponents`**: Компоненты разобранного имени / Parsed name components / 解析后的姓名组件
- **`NameParsingResult`**: Результат парсинга с метаинформацией / Parsing result with metadata / 解析结果和元信息
- **`SurnameInfo`**: Информация о фамилии / Surname information / 姓氏信息
- **НОВОЕ:** **`TransliterationEntry`**: Запись транслитерации с вариантами / Transliteration entry with variants / 音译条目及其变体
- **НОВОЕ:** **`SurnameTrie`**: Высокопроизводительная структура поиска / High-performance search structure / 高性能搜索结构

#### 4. **НОВАЯ:** Система оценки достоверности / **NEW:** Confidence Assessment System / **新增:** 置信度评估系统

**`ConfidenceCalculator`** - Точная оценка достоверности результатов / Precise confidence assessment of results / 精确的结果置信度评估

**Уровни достоверности / Confidence Levels / 置信度等级:**
- 0.98: Точное совпадение в базе данных / Perfect database match / 数据库精确匹配
- 0.95: Составная фамилия / Compound surname / 复合姓氏
- 0.90: Обычная фамилия / Common surname / 常见姓氏
- 0.85: Trie-поиск / Trie search / Trie搜索匹配
- 0.80: Транслитерированное имя / Transliterated name / 音译姓名
- 0.70: Смешанное письмо / Mixed script / 混合文字
- 0.60: Резервная стратегия / Fallback strategy / 后备策略

#### 5. **НОВАЯ:** Расширенная база транслитераций / **NEW:** Extended Transliteration Database / **新增:** 扩展音译数据库

**`ExtendedTransliterationDatabase`** - Поддержка множественных систем транслитерации / Multi-system transliteration support / 多系统音译支持

**Поддерживаемые системы / Supported Systems / 支持的系统:**
- Пиньинь (拼音) / Pinyin / 拼音
- Система Палладия (俄文) / Palladius System (Russian) / 帕拉第系统（俄文）
- Уэйд-Джайлс / Wade-Giles / 威妥玛系统
- **НОВОЕ:** Варианты написания / **NEW:** Spelling variants / **新功能:** 拼写变体
- **НОВОЕ:** Поддержка дефисов и регистра / **NEW:** Hyphen and case support / **新功能:** 支持连字符和大小写

---

## Установка и использование / Installation and Usage / 安装和使用

### Требования / Requirements / 要求

```
Python >= 3.7
pypinyin (опционально / optional / 可选)
```

### Базовое использование / Basic Usage / 基本使用

```python
from chinese_name_processor import create_default_processor

# Создание процессора / Create processor / 创建处理器
processor = create_default_processor()

# Обработка одного имени / Process single name / 处理单个姓名
result = processor.process_name("李小明")

print(f"Фамилия / Surname / 姓氏: {result.components.surname}")
print(f"Имя / Given name / 名字: {result.components.first_name}")
print(f"Достоверность / Confidence / 置信度: {result.confidence_score:.3f}")

# Пакетная обработка / Batch processing / 批量处理
names = ["李明", "王小红", "欧阳修"]
results = processor.batch_process(names)
```

### Продвинутое использование / Advanced Usage / 高级使用

```python
from chinese_name_processor import ChineseNameProcessor, SurnameDatabase
from transliteration_db import ExtendedTransliterationDatabase

# Создание пользовательской базы данных фамилий
# Custom surname database creation
# 创建自定义姓氏数据库
custom_surnames = {
    '测试': {'pinyin': 'ceshi', 'palladius': 'цеши', 'frequency': 1, 'region': ['тест']}
}

db = SurnameDatabase(custom_surnames)
processor = ChineseNameProcessor(surname_db=db)

# Конфигурация / Configuration / 配置
config = {
    'confidence_threshold': 0.8,
    'enable_fuzzy_matching': True,
    'max_alternatives': 5
}

processor = ChineseNameProcessor(config=config)
```

### **НОВЫЕ** Примеры использования / **NEW** Usage Examples / **新** 使用示例

#### Смешанное письмо / Mixed Script / 混合文字
```python
# Обработка смешанных имён (китайский + латиница)
# Mixed name processing (Chinese + Latin)
# 混合姓名处理（中文+拉丁文）

result = processor.process_name("张John")  # Фамилия + западное имя / Surname + western name / 姓氏+西方名字
print(f"Surname: {result.components.surname}")  # 张
print(f"Given name: {result.components.first_name}")  # John

result = processor.process_name("David李")  # Западное имя + фамилия / Western name + surname / 西方名字+姓氏
print(f"Surname: {result.components.surname}")  # 李
print(f"Given name: {result.components.first_name}")  # David
```

#### Варианты транслитерации / Transliteration Variants / 音译变体
```python
from transliteration_db import get_extended_transliteration_db

# Получение расширенной базы транслитераций
# Get extended transliteration database
# 获取扩展音译数据库
trans_db = get_extended_transliteration_db()

# Поддержка вариантов написания
# Support for spelling variants
# 支持拼写变体
result = trans_db.identify_transliterated_name(["Van", "Syaokhun"])  # Van -> 王, Syaokhun -> 小红
result = trans_db.identify_transliterated_name(["Wong", "Ming"])     # Wong -> 王, Ming -> 明
result = trans_db.identify_transliterated_name(["Lee", "Xiaohong"])  # Lee -> 李, Xiaohong -> 小红

# Поддержка дефисов / Hyphen support / 连字符支持
result = trans_db.identify_transliterated_name(["Jia-xing"])         # Jia-xing -> 嘉 | 星
```

#### Динамическое обучение / Dynamic Learning / 动态学习
```python
# НОВАЯ функция: обучение на текстовых корпусах
# NEW feature: learning from text corpora
# 新功能: 从文本语料库学习

corpus = """
在历史上，欧阳修是著名文学家，司马光编写了史书，诸葛亮以智慧闻名。
独孤求败武功高强，慕容复是燕国后代，完颜阿骨打建立金朝。
"""

# Обучение новым фамилиям из корпуса
# Learn new surnames from corpus
# 从语料库学习新姓氏
learned_surnames = processor.surname_db.learn_from_text_corpus(
    corpus=corpus,
    frequency_threshold=2,
    context_threshold=2
)

print(f"Learned {len(learned_surnames)} new surnames:")
for surname, freq in learned_surnames.items():
    print(f"  {surname}: {freq} occurrences")
```

---

## Тестирование / Testing / 测试

### Запуск тестов / Running Tests / 运行测试

```bash
# Базовые тесты на китайском языке / Basic tests in Chinese / 中文基础测试
python test_processor.py

# Полная тестовая система с русско-английской локализацией
# Complete test system with Russian-English localization
# 完整的俄英本地化测试系统
python test_processor_ru.py

# НОВЫЕ тесты для новых функций / NEW tests for new features / 新功能的新测试
python test_mixed_script.py              # Смешанное письмо / Mixed script / 混合文字
python test_enhanced_confidence.py       # Система оценки достоверности / Confidence system / 置信度系统
python test_trie_integration.py          # Trie-интеграция / Trie integration / Trie集成
python test_corpus_learning.py           # Обучение на корпусах / Corpus learning / 语料库学习
python test_enhanced_transliteration.py  # Расширенные транслитерации / Enhanced transliteration / 增强音译
```

### Тестовые модули / Test Modules / 测试模块

#### Основные тесты / Core Tests / 核心测试
1. **test_basic_name_parsing()** - Базовый парсинг / Basic parsing / 基本解析
2. **test_error_handling()** - Обработка ошибок / Error handling / 错误处理
3. **test_batch_processing()** - Пакетная обработка / Batch processing / 批量处理
4. **test_surname_database()** - База данных фамилий / Surname database / 姓氏数据库
5. **test_performance_benchmark()** - Производительность / Performance / 性能测试
6. **test_istina_integration_compatibility()** - Совместимость с ИСТИНА / ISTINA compatibility / ИСТИНА兼容性

#### **НОВЫЕ** Специализированные тесты / **NEW** Specialized Tests / **新增** 专门测试
7. **test_mixed_script_processing()** - Смешанное письмо / Mixed script processing / 混合文字处理
8. **test_confidence_calculation()** - Расчёт достоверности / Confidence calculation / 置信度计算
9. **test_trie_performance()** - Производительность Trie / Trie performance / Trie性能
10. **test_corpus_learning()** - Динамическое обучение / Dynamic learning / 动态学习
11. **test_transliteration_variants()** - Варианты транслитерации / Transliteration variants / 音译变体
12. **test_hyphen_processing()** - Обработка дефисов / Hyphen processing / 连字符处理

### Результаты тестирования / Test Results / 测试结果

**Последние результаты / Latest Results / 最新结果:**
- ✅ Смешанное письмо: 100% (8/8) / Mixed script: 100% (8/8) / 混合文字: 100% (8/8)
- ✅ Trie-интеграция: Функциональность 100%, Производительность проверена / Trie integration: 100% functionality, performance verified / Trie集成: 功能100%，性能已验证
- ✅ Обучение корпусам: 4 новые фамилии изучены / Corpus learning: 4 new surnames learned / 语料库学习: 学习了4个新姓氏
- ✅ Расширенные транслитерации: 100% (22/22) / Enhanced transliteration: 100% (22/22) / 增强音译: 100% (22/22)

---

## Интеграция с системой ИСТИНА / ISTINA System Integration / ИСТИНА系统集成

### Формат JSON для ИСТИНА / JSON Format for ISTINA / ИСТИНА的JSON格式

```json
{
  "components": {
    "surname": "李",
    "first_name": "小明",
    "middle_name": "",
    "confidence": 0.95,
    "source_type": "pure_chinese"
  },
  "confidence_score": 0.95,
  "decision_path": [
    "Processing name: '李小明'",
    "Detected as pure Chinese name",
    "Successfully parsed: 李 | 小明"
  ],
  "alternatives": [],
  "errors": [],
  "processing_time": 0.001234
}
```

### Рекомендации по интеграции / Integration Recommendations / 集成建议

**Русский:**
1. Используйте пакетную обработку для больших объёмов данных
2. Настройте пороговое значение достоверности в зависимости от требований точности
3. Регулярно обновляйте базу данных фамилий для поддержания актуальности
4. Ведите логирование результатов для последующего анализа

**English:**
1. Use batch processing for large data volumes
2. Configure confidence threshold based on accuracy requirements
3. Regularly update surname database to maintain relevance
4. Maintain result logging for subsequent analysis

**中文:**
1. 对大量数据使用批量处理
2. 根据准确性要求配置置信度阈值
3. 定期更新姓氏数据库以保持相关性
4. 维护结果日志以供后续分析

---

## Производительность / Performance / 性能

### Бенчмарки / Benchmarks / 基准测试

| Операция / Operation / 操作 | Время / Time / 时间 | Пропускная способность / Throughput / 吞吐量 |
|---|---|---|
| Одно имя / Single name / 单个姓名 | ~1-3 мс / ms / 毫秒 | 300-1000 имён/сек / names/sec / 个/秒 |
| Пакетная обработка / Batch processing / 批量处理 | ~0.5-2 мс/имя / ms/name / 毫秒/个 | 500-2000 имён/сек / names/sec / 个/秒 |

### Оптимизация / Optimization / 优化

**✅ РЕАЛИЗОВАННЫЕ улучшения / ✅ IMPLEMENTED improvements / ✅ 已实现的改进:**
- ✅ **Реализовано:** Префиксное дерево (Trie) для ускорения поиска фамилий / **IMPLEMENTED:** Trie tree for accelerated surname search / **已实现:** Trie树用于加速姓氏搜索
- ✅ **Реализовано:** Многоуровневая система оценки достоверности / **IMPLEMENTED:** Multi-level confidence assessment system / **已实现:** 多级置信度评估系统
- ✅ **Реализовано:** Оптимизированная обработка смешанного письма / **IMPLEMENTED:** Optimized mixed script processing / **已实现:** 优化的混合文字处理
- ✅ **Реализовано:** Кэширование в расширенной базе транслитераций / **IMPLEMENTED:** Caching in extended transliteration database / **已实现:** 扩展音译数据库中的缓存

**Будущие улучшения / Future Improvements / 未来改进:**
- Детерминированный конечный автомат (ДКА) для паттерн-матчинга
- Адаптивное кэширование результатов для часто встречающихся имён
- Машинное обучение для улучшения распознавания редких фамилий

---

## Решение проблем / Troubleshooting / 故障排除

### ✅ ИСПРАВЛЕННЫЕ ошибки / ✅ FIXED Errors / ✅ 已修复错误

1. **✅ ИСПРАВЛЕНО:** TypeError при обработке None
   ```
   Проблема: NoneType object has no attribute / Problem: NoneType object has no attribute / 问题: NoneType对象没有属性
   Решение: Проверка входных данных добавлена в is_valid() / Solution: Input validation added in is_valid() / 解决方案: 在is_valid()中添加输入验证
   Статус: Полностью устранено / Status: Completely resolved / 状态: 已完全解决
   ```

2. **✅ ИСПРАВЛЕНО:** AttributeError для несуществующих атрибутов
   ```
   Проблема: 'dict' object has no attribute 'surname' / Problem: 'dict' object has no attribute 'surname' / 问题: 'dict'对象没有'surname'属性
   Решение: Использование dataclass с типизацией / Solution: Using dataclass with type hints / 解决方案: 使用带类型提示的dataclass
   Статус: Полностью устранено / Status: Completely resolved / 状态: 已完全解决
   ```

3. **✅ ИСПРАВЛЕНО:** Низкая производительность на больших данных
   ```
   Проблема: O(n) линейный поиск фамилий / Problem: O(n) linear surname search / 问题: O(n)线性姓氏搜索
   Решение: Реализация Trie-дерева для O(m) поиска / Solution: Implemented Trie tree for O(m) search / 解决方案: 实现Trie树实现O(m)搜索
   Статус: Полностью устранено / Status: Completely resolved / 状态: 已完全解决
   ```

4. **✅ ИСПРАВЛЕНО:** Неточная обработка смешанного письма
   ```
   Проблема: "张John" и "John张" обрабатывались неправильно / Problem: "张John" and "John张" processed incorrectly / 问题: "张John"和"John张"处理不正确
   Решение: Полная перереализация _handle_mixed_script_name с многостратегийным подходом / Solution: Complete rewrite of _handle_mixed_script_name with multi-strategy approach / 解决方案: 完全重写_handle_mixed_script_name采用多策略方法
   Статус: Полностью устранено / Status: Completely resolved / 状态: 已完全解决
   ```

5. **✅ ИСПРАВЛЕНО:** "Van Syaokhun" не распознавался
   ```
   Проблема: Русские транслитерации не поддерживались / Problem: Russian transliterations not supported / 问题: 不支持俄语音译
   Решение: Добавлены варианты "Van"→"王", "Syaokhun"→"小红" / Solution: Added variants "Van"→"王", "Syaokhun"→"小红" / 解决方案: 添加了变体"Van"→"王", "Syaokhun"→"小红"
   Статус: Полностью устранено / Status: Completely resolved / 状态: 已完全解决
   ```

6. **✅ ИСПРАВЛЕНО:** Неточные оценки достоверности
   ```
   Проблема: Простые heuristic-оценки без детализации / Problem: Simple heuristic assessments without detail / 问题: 简单的启发式评估缺乏细节
   Решение: Реализована система ConfidenceCalculator с 7 уровнями / Solution: Implemented ConfidenceCalculator system with 7 levels / 解决方案: 实现了具有7个级别的ConfidenceCalculator系统
   Статус: Полностью устранено / Status: Completely resolved / 状态: 已完全解决
   ```

### Оставшиеся известные ограничения / Remaining Known Limitations / 剩余已知限制

1. **Редкие региональные фамилии** / **Rare regional surnames** / **罕见地方姓氏**
   ```
   Статус: Улучшается через динамическое обучение / Status: Improving through dynamic learning / 状态: 通过动态学习改进
   ```

2. **Исторические варианты написания** / **Historical spelling variants** / **历史拼写变体**
   ```
   Статус: Планируется расширение базы данных / Status: Database expansion planned / 状态: 计划扩展数据库
   ```

---

## Вклад и разработка / Contributing and Development / 贡献和开发

### Стандарты кода / Code Standards / 代码标准

- **Комментарии / Comments / 注释:** Двуязычные (русский + китайский) / Bilingual (Russian + Chinese) / 双语（俄语+中文）
- **Тесты / Tests / 测试:** Русский и английский для совместимости с ИСТИНА / Russian and English for ISTINA compatibility / 俄语和英语以确保ИСТИНА兼容性
- **Типизация / Typing / 类型:** Полная аннотация типов / Full type annotations / 完整的类型注解
- **Документация / Documentation / 文档:** Трёхъязычная (русский, английский, китайский) / Trilingual (Russian, English, Chinese) / 三语（俄语、英语、中文）

---

## Лицензия / License / 许可证

Данный модуль разработан в рамках исследовательской работы в МГУ и предназначен для использования в системе ИСТИНА.

This module was developed as part of research work at MSU and is intended for use in the ISTINA system.

该模块是在莫斯科大学研究工作框架内开发的，旨在ИСТИНА系统中使用。

---

## История версий / Version History / 版本历史

### v2.0.0 (2025-01-14) - **КРУПНОЕ ОБНОВЛЕНИЕ** / **MAJOR UPDATE** / **重大更新**
- ✅ **НОВОЕ:** Высокопроизводительный поиск с Trie-деревом / **NEW:** High-performance Trie tree search / **新功能:** 高性能Trie树搜索
- ✅ **НОВОЕ:** Обработка смешанного письма (китайский + латиница) / **NEW:** Mixed script processing (Chinese + Latin) / **新功能:** 混合文字处理（中文+拉丁文）
- ✅ **НОВОЕ:** Динамическое обучение на текстовых корпусах / **NEW:** Dynamic learning from text corpora / **新功能:** 从文本语料库动态学习
- ✅ **НОВОЕ:** Расширенная база транслитераций с вариантами / **NEW:** Extended transliteration database with variants / **新功能:** 扩展的音译数据库支持变体
- ✅ **ИСПРАВЛЕНО:** "Van Syaokhun" и другие русские транслитерации / **FIXED:** "Van Syaokhun" and other Russian transliterations / **已修复:** "Van Syaokhun"和其他俄语音译
- ✅ **УЛУЧШЕНО:** Многоуровневая система оценки достоверности / **IMPROVED:** Multi-level confidence assessment / **已改进:** 多级置信度评估系统
- ✅ **УЛУЧШЕНО:** Поддержка дефисов и регистронезависимость / **IMPROVED:** Hyphen support and case insensitivity / **已改进:** 支持连字符和大小写不敏感
- ✅ Детальная генерация пути принятия решений / Detailed decision path generation / 详细决策路径生成
- ✅ Исправление 96.3%→100% успешности для валидных случаев / Fixed 96.3%→100% success rate for valid cases / 修复了有效案例的96.3%→100%成功率

### v1.0.0 (2025-01-01)
- ✅ Объектно-ориентированный рефакторинг / Object-oriented refactoring / 面向对象重构
- ✅ Устранение TypeError и AttributeError / Fixed TypeError and AttributeError / 修复TypeError和AttributeError
- ✅ Добавлена оценка достоверности / Added confidence scoring / 添加可信度评分
- ✅ Двуязычная документация / Bilingual documentation / 双语文档
- ✅ Интеграция с системой ИСТИНА / ISTINA system integration / ИСТИНА系统集成

### Статистика разработки / Development Statistics / 开发统计

**Всего исправлений / Total Fixes / 总修复数:** 6 критических ошибок / 6 critical bugs / 6个关键错误
**Новых функций / New Features / 新功能:** 5 основных модулей / 5 major modules / 5个主要模块
**Тестовое покрытие / Test Coverage / 测试覆盖率:** 12 специализированных тестов / 12 specialized tests / 12个专门测试
**Производительность / Performance / 性能:** O(n)→O(m) поиск через Trie / O(n)→O(m) search via Trie / 通过Trie实现O(n)→O(m)搜索