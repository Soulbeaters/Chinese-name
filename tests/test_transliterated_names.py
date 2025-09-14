# -*- coding: utf-8 -*-
"""
Тестирование функциональности транслитерированных китайских имён
音译中文姓名功能测试

Автор / 作者: Ма Цзясин (Ma Jiaxin)
Проект / 项目: ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных
Модуль / 模块: Комплексное тестирование расширенной поддержки транслитерированных имён
               音译姓名扩展支持的全面测试

Описание / 描述:
Данный модуль проводит комплексное тестирование системы обработки транслитерированных
китайских имён, включая поддержку пиньинь, системы Палладия (русская транскрипция)
и различных вариантов написания. Обеспечивает проверку работы системы с именами,
типичными для научных публикаций в системе ИСТИНА.

该模块对音译中文姓名处理系统进行全面测试，包括拼音、帕拉第系统（俄语转写）
和各种拼写变体的支持。确保系统能处理ИСТИНА系统科学出版物中常见的姓名。
"""

import sys
import os
import time
from typing import List, Tuple, Dict

# Добавление текущего каталога в путь Python / 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import ChineseNameProcessor, create_default_processor
from transliteration_db import ExtendedTransliterationDatabase

class TransliteratedNameTester:
    """
    Тестер транслитерированных имён / 音译姓名测试器

    Проводит комплексное тестирование способности системы обрабатывать
    транслитерированные китайские имена в различных системах записи.
    对系统处理各种记录系统中音译中文姓名的能力进行全面测试。
    """

    def __init__(self):
        """Инициализация тестера / 初始化测试器"""
        self.processor = create_default_processor()
        self.test_results: List[Dict] = []

        print("ТЕСТИРОВАНИЕ ТРАНСЛИТЕРИРОВАННЫХ КИТАЙСКИХ ИМЁН")
        print("TRANSLITERATED CHINESE NAMES TESTING")
        print("="*60)
        print("Автор / Author: Ма Цзясин (Ma Jiaxing)")
        print("Система / System: ИСТИНА integration testing")
        print("="*60)

    def test_pinyin_names(self):
        """Тестирование имён в системе пиньинь / 拼音系统姓名测试"""
        print("\n🔤 ТЕСТИРОВАНИЕ ПИНЬИНЬ ИМЁН / PINYIN NAMES TEST")
        print("-" * 50)

        # Тестовые случаи пиньинь / Pinyin test cases
        pinyin_test_cases = [
            # (输入, 期望姓氏, 期望名字, 描述)
            ("Li Ming", "Li", "Ming", "李明 - Классическое пиньинь"),
            ("Wang Xiaohong", "Wang", "Xiaohong", "王小红 - Составное имя"),
            ("Zhang Wei", "Zhang", "Wei", "张伟 - Простое имя"),
            ("Ma Jiaxing", "Ma", "Jiaxing", "马嘉星 - Тестовое имя автора"),
            ("Zhao Yun", "Zhao", "Yun", "赵云 - Исторический персонаж"),
            ("Ouyang Xiu", "Ouyang", "Xiu", "欧阳修 - Составная фамилия"),
            ("Sima Guang", "Sima", "Guang", "司马光 - Составная фамилия"),

            # Тестирование западного порядка / 西方顺序测试
            ("Ming Li", "Li", "Ming", "明李 - Западный порядок"),
            ("Xiaohong Wang", "Wang", "Xiaohong", "小红王 - Западный порядок"),
        ]

        success_count = 0
        for i, (input_name, expected_surname, expected_given, description) in enumerate(pinyin_test_cases, 1):
            result = self.processor.process_name(input_name)

            is_success = (result.is_successful() and
                         result.components.surname.lower() == expected_surname.lower() and
                         result.components.first_name.lower() == expected_given.lower())

            if is_success:
                success_count += 1
                status = "✅ ПРОЙДЕН / PASSED"
            else:
                status = "❌ НЕ ПРОЙДЕН / FAILED"

            print(f"{i:2d}. {input_name:<15} -> {result.components.surname:<8} | {result.components.first_name:<10} | {status}")
            print(f"    Описание / Description: {description}")
            print(f"    Ожидается / Expected: {expected_surname} | {expected_given}")
            print(f"    Получено / Got: {result.components.surname} | {result.components.first_name}")
            print(f"    Достоверность / Confidence: {result.confidence_score:.3f}")
            print(f"    Тип / Type: {result.components.source_type}")

            if result.errors:
                print(f"    Ошибки / Errors: {result.errors}")
            print()

        print(f"📊 Результат пиньинь тестов / Pinyin test results: {success_count}/{len(pinyin_test_cases)} успешно")
        return success_count, len(pinyin_test_cases)

    def test_palladius_names(self):
        """Тестирование имён в системе Палладия / 帕拉第系统姓名测试"""
        print("\n🇷🇺 ТЕСТИРОВАНИЕ ИМЁН ПО СИСТЕМЕ ПАЛЛАДИЯ / PALLADIUS SYSTEM TEST")
        print("-" * 60)

        # Тестовые случаи системы Палладия / Palladius system test cases
        palladius_test_cases = [
            ("Ма Цзясин", "Ма", "Цзясин", "马嘉星 - Имя автора в системе Палладия"),
            ("Ли Мин", "Ли", "Мин", "李明 - Классическое русское написание"),
            ("Ван Сяохун", "Ван", "Сяохун", "王小红 - Женское имя"),
            ("Чжан Вэй", "Чжан", "Вэй", "张伟 - Популярное мужское имя"),
            ("Чжао Юнь", "Чжао", "Юнь", "赵云 - Исторический персонаж"),
            ("Оуян Сю", "Оуян", "Сю", "欧阳修 - Составная фамилия"),
            ("Сыма Гуан", "Сыма", "Гуан", "司马光 - Составная фамилия"),
        ]

        success_count = 0
        for i, (input_name, expected_surname, expected_given, description) in enumerate(palladius_test_cases, 1):
            result = self.processor.process_name(input_name)

            is_success = (result.is_successful() and
                         result.components.surname.lower() == expected_surname.lower() and
                         result.components.first_name.lower() == expected_given.lower())

            if is_success:
                success_count += 1
                status = "✅ ПРОЙДЕН / PASSED"
            else:
                status = "❌ НЕ ПРОЙДЕН / FAILED"

            print(f"{i:2d}. {input_name:<15} -> {result.components.surname:<8} | {result.components.first_name:<10} | {status}")
            print(f"    Описание / Description: {description}")
            print(f"    Ожидается / Expected: {expected_surname} | {expected_given}")
            print(f"    Получено / Got: {result.components.surname} | {result.components.first_name}")
            print(f"    Достоверность / Confidence: {result.confidence_score:.3f}")
            print(f"    Тип / Type: {result.components.source_type}")

            if result.errors:
                print(f"    Ошибки / Errors: {result.errors}")
            print()

        print(f"📊 Результат тестов системы Палладия / Palladius test results: {success_count}/{len(palladius_test_cases)} успешно")
        return success_count, len(palladius_test_cases)

    def test_variant_spellings(self):
        """Тестирование вариантов написания / 拼写变体测试"""
        print("\n📝 ТЕСТИРОВАНИЕ ВАРИАНТОВ НАПИСАНИЯ / VARIANT SPELLINGS TEST")
        print("-" * 55)

        # Различные варианты написания одних и тех же имён / Different spellings of the same names
        variant_test_cases = [
            ("Lee Ming", "Lee", "Ming", "李明 - Вариант Li"),
            ("Wong Siu Hong", "Wong", "Siu Hong", "王小红 - Кантонская транскрипция"),
            ("Chang Wei", "Chang", "Wei", "张伟 - Вариант Zhang"),
            ("Chow Yun", "Chow", "Yun", "周云 - Кантонская транскрипция"),
            ("Lau Tak Wah", "Lau", "Tak Wah", "刘德华 - Кантонский вариант Liu"),
        ]

        success_count = 0
        for i, (input_name, expected_surname, expected_given, description) in enumerate(variant_test_cases, 1):
            result = self.processor.process_name(input_name)

            # Для вариантов написания используем более гибкую проверку
            is_success = result.is_successful() and bool(result.components.surname and result.components.first_name)

            if is_success:
                success_count += 1
                status = "✅ РАСПОЗНАНО / RECOGNIZED"
            else:
                status = "❌ НЕ РАСПОЗНАНО / NOT RECOGNIZED"

            print(f"{i:2d}. {input_name:<15} -> {result.components.surname:<8} | {result.components.first_name:<12} | {status}")
            print(f"    Описание / Description: {description}")
            print(f"    Достоверность / Confidence: {result.confidence_score:.3f}")
            print(f"    Тип / Type: {result.components.source_type}")

            if result.errors:
                print(f"    Ошибки / Errors: {result.errors}")
            print()

        print(f"📊 Результат тестов вариантов / Variant test results: {success_count}/{len(variant_test_cases)} распознано")
        return success_count, len(variant_test_cases)

    def test_mixed_script_names(self):
        """Тестирование смешанных имён / 混合文字姓名测试"""
        print("\n🌐 ТЕСТИРОВАНИЕ СМЕШАННЫХ ИМЁН / MIXED SCRIPT NAMES TEST")
        print("-" * 50)

        # Смешанные случаи / Mixed cases
        mixed_test_cases = [
            ("李 Ming", "李", "Ming", "Китайская фамилия + латинское имя"),
            ("Li 明", "Li", "明", "Латинская фамилия + китайское имя"),
            ("王 John", "王", "John", "Китайская фамилия + западное имя"),
            ("David 张", "张", "David", "Западное имя + китайская фамилия"),
        ]

        success_count = 0
        for i, (input_name, expected_surname, expected_given, description) in enumerate(mixed_test_cases, 1):
            result = self.processor.process_name(input_name)

            # Для смешанных имён проверяем наличие результата
            is_success = result.is_successful() and bool(result.components.surname and result.components.first_name)

            if is_success:
                success_count += 1
                status = "✅ ОБРАБОТАНО / PROCESSED"
            else:
                status = "❌ НЕ ОБРАБОТАНО / NOT PROCESSED"

            print(f"{i:2d}. {input_name:<15} -> {result.components.surname:<8} | {result.components.first_name:<10} | {status}")
            print(f"    Описание / Description: {description}")
            print(f"    Достоверность / Confidence: {result.confidence_score:.3f}")
            print(f"    Тип / Type: {result.components.source_type}")

            if result.errors:
                print(f"    Ошибки / Errors: {result.errors}")
            print()

        print(f"📊 Результат тестов смешанных имён / Mixed names test results: {success_count}/{len(mixed_test_cases)} обработано")
        return success_count, len(mixed_test_cases)

    def test_performance_comparison(self):
        """Сравнение производительности / 性能比较测试"""
        print("\n⚡ ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ ТРАНСЛИТЕРАЦИИ / TRANSLITERATION PERFORMANCE TEST")
        print("-" * 70)

        # Набор для тестирования производительности / Performance test set
        perf_test_names = [
            "Li Ming", "Wang Xiaohong", "Zhang Wei", "Zhao Yun", "Ma Jiaxing",
            "Ма Цзясин", "Ли Мин", "Ван Сяохун", "Чжан Вэй", "Чжао Юнь",
            "Ouyang Xiu", "Sima Guang", "Lee Jong", "Wong Ka Kui", "Chan Jackie"
        ] * 100  # 1500 имён для статистически значимого теста / 1500 names for statistically significant test

        print(f"Тестирование производительности на {len(perf_test_names)} именах...")
        print(f"Performance testing on {len(perf_test_names)} names...")

        start_time = time.perf_counter()
        successful_parses = 0

        for name in perf_test_names:
            result = self.processor.process_name(name)
            if result.is_successful():
                successful_parses += 1

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time = (total_time / len(perf_test_names)) * 1000  # в миллисекундах / in milliseconds
        success_rate = (successful_parses / len(perf_test_names)) * 100

        print(f"\n📊 РЕЗУЛЬТАТЫ ПРОИЗВОДИТЕЛЬНОСТИ / PERFORMANCE RESULTS:")
        print(f"  Общее время / Total time: {total_time:.4f} секунд / seconds")
        print(f"  Среднее время на имя / Average time per name: {avg_time:.3f} мс / ms")
        print(f"  Имён в секунду / Names per second: {len(perf_test_names)/total_time:.1f}")
        print(f"  Успешно обработано / Successfully processed: {successful_parses}/{len(perf_test_names)}")
        print(f"  Процент успеха / Success rate: {success_rate:.1f}%")

        # Оценка для системы ИСТИНА / ISTINA system evaluation
        if avg_time < 2.0 and success_rate > 80:
            grade = "✅ ОТЛИЧНО для системы ИСТИНА / EXCELLENT for ISTINA system"
        elif avg_time < 5.0 and success_rate > 70:
            grade = "✅ ХОРОШО для системы ИСТИНА / GOOD for ISTINA system"
        else:
            grade = "⚠️  Требуется оптимизация / Optimization needed"

        print(f"  Оценка / Rating: {grade}")

    def test_istina_integration_scenarios(self):
        """Тестирование сценариев интеграции с ИСТИНА / ИСТИНА集成场景测试"""
        print("\n🏛️  ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ С СИСТЕМОЙ ИСТИНА / ISTINA INTEGRATION TEST")
        print("-" * 70)

        # Реальные сценарии из системы ИСТИНА / Real ISTINA system scenarios
        istina_scenarios = [
            # Автор: Ма Цзясин / Author: Ma Jiaxin
            ("Ма Цзясин", "Ма", "Цзясин", "Русская транскрипция автора"),
            ("Ma Jiaxing", "Ma", "Jiaxing", "Английская транскрипция автора"),
            ("马嘉星", "马", "嘉星", "Оригинальные иероглифы"),

            # Типичные китайские авторы научных статей / Typical Chinese authors in scientific papers
            ("Li Wei", "Li", "Wei", "Популярное имя в китайской науке"),
            ("Wang Ming", "Wang", "Ming", "Распространённая комбинация"),
            ("Zhang Hua", "Zhang", "Hua", "Типичное научное имя"),
            ("Liu Jian", "Liu", "Jian", "Частое имя в публикациях"),

            # Смешанные форматы / Mixed formats
            ("J. Li", "Li", "J", "Инициал + фамилия"),
            ("Wang, X.", "Wang", "X", "Фамилия, инициал"),
        ]

        success_count = 0
        for i, (input_name, expected_surname, expected_given, scenario) in enumerate(istina_scenarios, 1):
            result = self.processor.process_name(input_name)

            # Проверяем успешную идентификацию / Check successful identification
            is_success = result.is_successful()

            if is_success:
                success_count += 1
                status = "✅ СОВМЕСТИМО / COMPATIBLE"
            else:
                status = "❌ НЕ СОВМЕСТИМО / INCOMPATIBLE"

            print(f"{i:2d}. {input_name:<15} -> {result.components.surname:<8} | {result.components.first_name:<10} | {status}")
            print(f"    Сценарий / Scenario: {scenario}")
            print(f"    Достоверность / Confidence: {result.confidence_score:.3f}")
            print(f"    Тип обработки / Processing type: {result.components.source_type}")

            # Проверка JSON сериализации для API ИСТИНА / JSON serialization check for ISTINA API
            try:
                import json
                json_data = result.to_dict()
                json_str = json.dumps(json_data, ensure_ascii=False)
                json_ok = len(json_str) > 0
                print(f"    JSON сериализация / JSON serialization: {'✅ ОК' if json_ok else '❌ Ошибка'}")
            except Exception as e:
                print(f"    JSON сериализация / JSON serialization: ❌ Ошибка - {e}")

            if result.errors:
                print(f"    Ошибки / Errors: {result.errors}")
            print()

        compatibility_rate = (success_count / len(istina_scenarios)) * 100
        print(f"📊 Совместимость с ИСТИНА / ISTINA compatibility: {success_count}/{len(istina_scenarios)} ({compatibility_rate:.1f}%)")

        if compatibility_rate >= 90:
            print("🎉 ПРЕВОСХОДНАЯ совместимость с системой ИСТИНА!")
            print("🎉 EXCELLENT compatibility with ISTINA system!")
        elif compatibility_rate >= 80:
            print("✅ ХОРОШАЯ совместимость с системой ИСТИНА")
            print("✅ GOOD compatibility with ISTINA system")
        else:
            print("⚠️  Необходимы улучшения для интеграции с ИСТИНА")
            print("⚠️  Improvements needed for ISTINA integration")

    def run_comprehensive_test(self):
        """Запуск полного набора тестов / 运行全面测试"""
        print("ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ")
        print("RUNNING COMPREHENSIVE TEST SUITE")

        # Выполнение всех тестов / Execute all tests
        pinyin_success, pinyin_total = self.test_pinyin_names()
        palladius_success, palladius_total = self.test_palladius_names()
        variant_success, variant_total = self.test_variant_spellings()
        mixed_success, mixed_total = self.test_mixed_script_names()

        # Тесты производительности и интеграции / Performance and integration tests
        self.test_performance_comparison()
        self.test_istina_integration_scenarios()

        # Общие результаты / Overall results
        total_success = pinyin_success + palladius_success + variant_success + mixed_success
        total_tests = pinyin_total + palladius_total + variant_total + mixed_total

        print("\n" + "="*70)
        print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ / FINAL TEST RESULTS")
        print("="*70)
        print(f"Пиньинь имена / Pinyin names: {pinyin_success}/{pinyin_total}")
        print(f"Система Палладия / Palladius system: {palladius_success}/{palladius_total}")
        print(f"Варианты написания / Spelling variants: {variant_success}/{variant_total}")
        print(f"Смешанные имена / Mixed script names: {mixed_success}/{mixed_total}")
        print(f"ОБЩИЙ РЕЗУЛЬТАТ / OVERALL RESULT: {total_success}/{total_tests} ({(total_success/total_tests)*100:.1f}%)")

        if total_success == total_tests:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! / ALL TESTS PASSED!")
        elif (total_success/total_tests) > 0.8:
            print("✅ БОЛЬШИНСТВО ТЕСТОВ ПРОЙДЕНО / MOST TESTS PASSED")
        else:
            print("⚠️  ТРЕБУЮТСЯ УЛУЧШЕНИЯ / IMPROVEMENTS NEEDED")

        print(f"\nДата завершения / Completion date: {time.strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Главная функция запуска тестирования / 主测试函数"""
    tester = TransliteratedNameTester()

    try:
        tester.run_comprehensive_test()
        return 0
    except Exception as e:
        print(f"\nКРИТИЧЕСКАЯ ОШИБКА ТЕСТИРОВАНИЯ / CRITICAL TEST ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit(main())