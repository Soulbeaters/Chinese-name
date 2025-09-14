# -*- coding: utf-8 -*-
"""
Тестовый модуль для ChineseNameProcessor / ChineseNameProcessor Test Module
Test script for ChineseNameProcessor core functionality

Автор / Author: Ма Цзясин (Ma Jiaxin)
Проект / Project: ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных
                   ISTINA - Intelligent System for Thematic Investigation of Scientometric data
Модуль / Module: Тестирование модуля обработки китайских имён
                Testing module for Chinese name processing

Описание / Description:
Данный модуль содержит тестовые сценарии для проверки функциональности
системы обработки китайских имён в контексте интеграции с системой ИСТИНА.
Все тестовые результаты выводятся на русском и английском языках для
обеспечения совместимости с международными стандартами.

This module contains test scenarios for verifying the functionality of
the Chinese name processing system in the context of integration with ISTINA system.
All test outputs are provided in Russian and English to ensure compatibility
with international standards.
"""

import sys
import os
import json
import time
from pathlib import Path

# Добавление текущего каталога в путь Python / Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import ChineseNameProcessor, SurnameDatabase, create_default_processor

class TestResults:
    """
    Класс для сбора результатов тестирования / Test results collection class
    """
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_details = []

    def add_test(self, test_name: str, passed: bool, details: str = ""):
        """Добавить результат теста / Add test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "PASSED / ПРОЙДЕН"
        else:
            self.failed_tests += 1
            status = "FAILED / НЕ ПРОЙДЕН"

        self.test_details.append({
            'name': test_name,
            'status': status,
            'passed': passed,
            'details': details
        })

    def print_summary(self):
        """Вывести сводку результатов / Print results summary"""
        print("\n" + "="*80)
        print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ / TEST RESULTS")
        print("="*80)
        print(f"Всего тестов / Total tests: {self.total_tests}")
        print(f"Пройдено / Passed: {self.passed_tests}")
        print(f"Не пройдено / Failed: {self.failed_tests}")
        print(f"Успешность / Success rate: {(self.passed_tests/self.total_tests)*100:.1f}%")

        if self.failed_tests == 0:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! / ALL TESTS PASSED!")
        else:
            print("⚠️  ОБНАРУЖЕНЫ НЕУДАЧНЫЕ ТЕСТЫ / FAILED TESTS DETECTED")

def test_basic_name_parsing():
    """
    Тест базового парсинга китайских имён / Basic Chinese name parsing test
    """
    print("\n=== ТЕСТ БАЗОВОГО ПАРСИНГА / BASIC PARSING TEST ===")

    processor = create_default_processor()
    results = TestResults()

    # Тестовые случаи: (входные данные, ожидаемая фамилия, ожидаемое имя)
    # Test cases: (input, expected surname, expected given name)
    test_cases = [
        ("李小明", "李", "小明"),      # Li Xiaoming - простая фамилия / simple surname
        ("王", "王", ""),             # Wang - только фамилия / surname only
        ("欧阳修", "欧阳", "修"),      # Ouyang Xiu - составная фамилия / compound surname
        ("司马光", "司马", "光"),      # Sima Guang - составная фамилия / compound surname
        ("张三丰", "张", "三丰"),      # Zhang Sanfeng - длинное имя / long given name
        ("陈独秀", "陈", "独秀")       # Chen Duxiu - длинное имя / long given name
    ]

    for i, (name, expected_surname, expected_firstname) in enumerate(test_cases, 1):
        result = processor.process_name(name)

        # Проверка успешности / Check success
        success = (result.components.surname == expected_surname and
                  result.components.first_name == expected_firstname)

        # Вывод результатов / Output results
        print(f"\n{i}. Тест / Test: '{name}'")
        print(f"   Результат / Result: {result.components.surname} | {result.components.first_name}")
        print(f"   Ожидается / Expected: {expected_surname} | {expected_firstname}")
        print(f"   Достоверность / Confidence: {result.confidence_score:.3f}")
        print(f"   Время обработки / Processing time: {result.processing_time*1000:.2f}ms")
        print(f"   Статус / Status: {'✓ ПРОЙДЕН / PASSED' if success else '✗ НЕ ПРОЙДЕН / FAILED'}")

        if result.errors:
            print(f"   Ошибки / Errors: {result.errors}")

        details = f"Input: {name}, Output: {result.components.surname}|{result.components.first_name}"
        results.add_test(f"Basic parsing: {name}", success, details)

    return results

def test_error_handling():
    """
    Тест обработки ошибок / Error handling test
    """
    print("\n=== ТЕСТ ОБРАБОТКИ ОШИБОК / ERROR HANDLING TEST ===")

    processor = create_default_processor()
    results = TestResults()

    # Тестовые случаи с ошибками / Error test cases
    error_cases = [
        ("", "пустая строка / empty string"),
        (None, "значение None / None value"),
        ("   ", "только пробелы / whitespace only"),
        ("123", "только цифры / numbers only"),
        ("abc", "латинские буквы / latin letters"),
        ("李小明王五", "слишком длинное имя / too long name"),
    ]

    for i, (case, description) in enumerate(error_cases, 1):
        print(f"\n{i}. Тест ошибки / Error test: {description}")
        print(f"   Входные данные / Input: {repr(case)}")

        result = processor.process_name(case)

        # Для тестов ошибок ожидаем неуспешный результат / For error tests we expect unsuccessful result
        expected_failure = not result.is_successful()

        print(f"   Успешность парсинга / Parsing success: {result.is_successful()}")
        print(f"   Количество ошибок / Error count: {len(result.errors)}")
        print(f"   Статус / Status: {'✓ КОРРЕКТНО ОБРАБОТАНО / CORRECTLY HANDLED' if expected_failure else '✗ ОШИБКА НЕ ОБНАРУЖЕНА / ERROR NOT DETECTED'}")

        if result.errors:
            print(f"   Сообщение об ошибке / Error message: {result.errors[0]}")

        results.add_test(f"Error handling: {description}", expected_failure, f"Input: {repr(case)}")

    return results

def test_batch_processing():
    """
    Тест пакетной обработки / Batch processing test
    """
    print("\n=== ТЕСТ ПАКЕТНОЙ ОБРАБОТКИ / BATCH PROCESSING TEST ===")

    processor = create_default_processor()
    results = TestResults()

    # Список имён для пакетной обработки / List of names for batch processing
    names = ["李明", "王小红", "张三", "欧阳修", "司马光", "陈独秀"]

    print(f"Обработка {len(names)} имён пакетно / Processing {len(names)} names in batch")

    # Замер времени / Time measurement
    start_time = time.time()
    batch_results = processor.batch_process(names)
    end_time = time.time()

    total_time = end_time - start_time
    avg_time = total_time / len(names) * 1000  # в миллисекундах / in milliseconds

    successful = 0
    for i, (name, result) in enumerate(zip(names, batch_results), 1):
        success = result.is_successful()
        if success:
            successful += 1

        print(f"  {i}. {name} -> {result.components.surname} | {result.components.first_name}")
        print(f"     Достоверность / Confidence: {result.confidence_score:.3f}")

        if result.errors:
            print(f"     Ошибки / Errors: {result.errors}")

    print(f"\nСтатистика пакетной обработки / Batch processing statistics:")
    print(f"  Успешно обработано / Successfully processed: {successful}/{len(names)}")
    print(f"  Общее время / Total time: {total_time:.3f}s")
    print(f"  Среднее время на имя / Average time per name: {avg_time:.2f}ms")

    # Тест считается пройденным, если обработаны все имена / Test passes if all names processed
    batch_success = successful == len(names)
    results.add_test("Batch processing", batch_success, f"Processed: {successful}/{len(names)}")

    return results

def test_surname_database():
    """
    Тест базы данных фамилий / Surname database test
    """
    print("\n=== ТЕСТ БАЗЫ ДАННЫХ ФАМИЛИЙ / SURNAME DATABASE TEST ===")

    results = TestResults()

    # Создание тестовой базы данных / Creating test database
    test_surnames = {
        '测试': {'pinyin': 'ceshi', 'palladius': 'цеши', 'frequency': 1, 'region': ['测试区']},
        '复合测': {'pinyin': 'fuheceshi', 'palladius': 'фухэцеши', 'frequency': 1, 'region': ['测试区']}
    }

    try:
        db = SurnameDatabase(test_surnames)
        print("✓ База данных создана успешно / Database created successfully")

        # Тест базовых запросов / Basic query test
        info = db.lookup_surname('测试')
        lookup_success = info is not None and info.pinyin == 'ceshi'
        print(f"Поиск '测试' / Lookup '测试': {'✓ Найдено / Found' if lookup_success else '✗ Не найдено / Not found'}")
        results.add_test("Basic surname lookup", lookup_success)

        # Тест составных фамилий / Compound surname test
        is_compound = db.is_compound_surname('复合测')
        compound_success = is_compound
        print(f"'复合测' составная фамилия / '复合测' is compound: {'✓ Да / Yes' if compound_success else '✗ Нет / No'}")
        results.add_test("Compound surname detection", compound_success)

        # Тест поиска по пиньинь / Pinyin search test
        surnames = db.find_by_pinyin('ceshi')
        pinyin_success = '测试' in surnames
        print(f"Поиск по пиньинь 'ceshi' / Pinyin search 'ceshi': {'✓ Найдено / Found' if pinyin_success else '✗ Не найдено / Not found'}")
        results.add_test("Pinyin-based search", pinyin_success)

        # Тест динамического добавления / Dynamic addition test
        add_success = db.add_surname('新姓', {
            'pinyin': 'xinxing',
            'palladius': 'синсин',
            'frequency': 1,
            'region': ['测试区']
        })
        print(f"Динамическое добавление фамилии / Dynamic surname addition: {'✓ Успешно / Success' if add_success else '✗ Неудача / Failed'}")
        results.add_test("Dynamic surname addition", add_success)

        # Тест экспорта / Export test
        try:
            test_file = "test_surnames_export.json"
            db.export_to_json(test_file)
            export_success = os.path.exists(test_file)
            print(f"Экспорт в JSON / JSON export: {'✓ Успешно / Success' if export_success else '✗ Неудача / Failed'}")

            # Очистка тестового файла / Clean up test file
            if export_success and os.path.exists(test_file):
                os.remove(test_file)

            results.add_test("JSON export", export_success)

        except Exception as e:
            print(f"Экспорт в JSON / JSON export: ✗ Ошибка / Error - {e}")
            results.add_test("JSON export", False, str(e))

    except Exception as e:
        print(f"✗ Ошибка создания базы данных / Database creation error: {e}")
        results.add_test("Database creation", False, str(e))

    return results

def test_performance_benchmark():
    """
    Тест производительности / Performance benchmark test
    """
    print("\n=== ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ / PERFORMANCE BENCHMARK TEST ===")

    processor = create_default_processor()
    results = TestResults()

    # Создание большего набора данных для теста производительности
    # Creating larger dataset for performance test
    base_names = ["李明", "王小红", "张三", "欧阳修", "司马光"]
    test_names = base_names * 200  # 1000 имён / 1000 names

    print(f"Тестирование производительности на {len(test_names)} именах")
    print(f"Performance testing on {len(test_names)} names")

    # Замер времени пакетной обработки / Batch processing time measurement
    start_time = time.time()
    batch_results = processor.batch_process(test_names)
    end_time = time.time()

    total_time = end_time - start_time
    avg_time = total_time / len(test_names) * 1000  # миллисекунды / milliseconds
    names_per_second = len(test_names) / total_time

    successful = sum(1 for r in batch_results if r.is_successful())
    success_rate = (successful / len(test_names)) * 100

    print(f"\nРезультаты производительности / Performance results:")
    print(f"  Общее время / Total time: {total_time:.3f} секунд / seconds")
    print(f"  Среднее время на имя / Average time per name: {avg_time:.3f} мс / ms")
    print(f"  Имён в секунду / Names per second: {names_per_second:.1f}")
    print(f"  Успешность / Success rate: {success_rate:.1f}%")

    # Критерии производительности / Performance criteria
    acceptable_avg_time = 10.0  # мс / ms
    acceptable_success_rate = 95.0  # %

    performance_ok = avg_time <= acceptable_avg_time and success_rate >= acceptable_success_rate

    print(f"\nОценка производительности / Performance evaluation:")
    print(f"  Критерий времени / Time criterion: {'✓ Пройден / Passed' if avg_time <= acceptable_avg_time else '✗ Не пройден / Failed'}")
    print(f"  Критерий успешности / Success criterion: {'✓ Пройден / Passed' if success_rate >= acceptable_success_rate else '✗ Не пройден / Failed'}")

    results.add_test("Performance benchmark", performance_ok,
                    f"Avg time: {avg_time:.3f}ms, Success: {success_rate:.1f}%")

    return results

def test_istina_integration_compatibility():
    """
    Тест совместимости с системой ИСТИНА / ISTINA system integration compatibility test
    """
    print("\n=== ТЕСТ СОВМЕСТИМОСТИ С СИСТЕМОЙ ИСТИНА / ISTINA COMPATIBILITY TEST ===")

    processor = create_default_processor()
    results = TestResults()

    # Тестовые случаи, типичные для системы ИСТИНА
    # Test cases typical for ISTINA system
    istina_test_cases = [
        "李明",           # Простое китайское имя / Simple Chinese name
        "Li Ming",        # Транслитерация пиньинь / Pinyin transliteration
        "Ли Мин",         # Русская транслитерация / Russian transliteration
        "Zhang, Wei",     # Западный формат / Western format
        "欧阳修",         # Составная фамилия / Compound surname
        "Sima Guang",     # Транслитерированная составная фамилия / Transliterated compound surname
    ]

    print("Тестирование форматов имён, типичных для ИСТИНА:")
    print("Testing name formats typical for ISTINA:")

    total_processed = 0
    successful_parses = 0

    for i, name in enumerate(istina_test_cases, 1):
        result = processor.process_name(name)
        total_processed += 1

        if result.is_successful():
            successful_parses += 1
            status = "✓ УСПЕШНО / SUCCESS"
        else:
            status = "⚠️  ПРОБЛЕМА / ISSUE"

        print(f"  {i}. '{name}' -> {result.components.surname} | {result.components.first_name}")
        print(f"     Тип / Type: {result.components.source_type}")
        print(f"     Достоверность / Confidence: {result.confidence_score:.3f}")
        print(f"     Статус / Status: {status}")

        if result.errors:
            print(f"     Ошибки / Errors: {result.errors}")

        # Проверка совместимости с форматом ИСТИНА / ISTINA format compatibility check
        istina_compatible = result.is_successful() and result.confidence_score >= 0.7
        results.add_test(f"ISTINA compatibility: {name}", istina_compatible)

    compatibility_rate = (successful_parses / total_processed) * 100
    print(f"\nОбщая совместимость с ИСТИНА / Overall ISTINA compatibility: {compatibility_rate:.1f}%")

    # Тест JSON-сериализации для ИСТИНА / JSON serialization test for ISTINA
    try:
        result = processor.process_name("李明")
        json_data = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        json_success = len(json_data) > 0 and '"surname"' in json_data
        print(f"JSON-сериализация / JSON serialization: {'✓ Поддерживается / Supported' if json_success else '✗ Проблема / Issue'}")
        results.add_test("JSON serialization", json_success)
    except Exception as e:
        print(f"JSON-сериализация / JSON serialization: ✗ Ошибка / Error - {e}")
        results.add_test("JSON serialization", False, str(e))

    return results

def run_complete_test_suite():
    """
    Запуск полного набора тестов / Run complete test suite
    """
    print("СИСТЕМА ТЕСТИРОВАНИЯ ОБРАБОТКИ КИТАЙСКИХ ИМЁН ДЛЯ ИСТИНА")
    print("CHINESE NAME PROCESSING TEST SYSTEM FOR ISTINA")
    print("="*80)
    print("Автор / Author: Ма Цзясин (Ma Jiaxin)")
    print("Дата / Date:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)

    # Список всех тестов / List of all tests
    test_functions = [
        ("Базовый парсинг / Basic parsing", test_basic_name_parsing),
        ("Обработка ошибок / Error handling", test_error_handling),
        ("Пакетная обработка / Batch processing", test_batch_processing),
        ("База данных фамилий / Surname database", test_surname_database),
        ("Производительность / Performance", test_performance_benchmark),
        ("Совместимость ИСТИНА / ISTINA compatibility", test_istina_integration_compatibility)
    ]

    # Общие результаты / Overall results
    overall_results = TestResults()

    # Выполнение всех тестов / Execute all tests
    for test_name, test_func in test_functions:
        print(f"\n🔍 Запуск теста / Running test: {test_name}")
        try:
            test_result = test_func()

            # Объединение результатов / Merge results
            overall_results.total_tests += test_result.total_tests
            overall_results.passed_tests += test_result.passed_tests
            overall_results.failed_tests += test_result.failed_tests
            overall_results.test_details.extend(test_result.test_details)

        except Exception as e:
            print(f"❌ Критическая ошибка в тесте / Critical error in test {test_name}: {e}")
            overall_results.add_test(f"CRITICAL: {test_name}", False, str(e))

    # Вывод итоговой сводки / Print final summary
    overall_results.print_summary()

    # Рекомендации для интеграции с ИСТИНА / Recommendations for ISTINA integration
    print("\n" + "="*80)
    print("РЕКОМЕНДАЦИИ ДЛЯ ИНТЕГРАЦИИ С ИСТИНА / ISTINA INTEGRATION RECOMMENDATIONS")
    print("="*80)

    if overall_results.failed_tests == 0:
        print("✅ Модуль готов к интеграции с системой ИСТИНА")
        print("✅ Module is ready for ISTINA system integration")
    elif overall_results.failed_tests <= overall_results.total_tests * 0.1:  # Менее 10% неудач / Less than 10% failures
        print("⚠️  Модуль готов к интеграции с небольшими доработками")
        print("⚠️  Module is ready for integration with minor improvements")
    else:
        print("❌ Требуются дополнительные доработки перед интеграцией")
        print("❌ Additional improvements required before integration")

    return overall_results

if __name__ == "__main__":
    # Запуск полного набора тестов / Run complete test suite
    results = run_complete_test_suite()

    # Завершение / Completion
    print(f"\nТестирование завершено / Testing completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Код выхода для автоматизации / Exit code for automation
    exit_code = 0 if results.failed_tests == 0 else 1
    print(f"Код выхода / Exit code: {exit_code}")
    sys.exit(exit_code)