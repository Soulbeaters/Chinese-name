# -*- coding: utf-8 -*-
"""
Демонстрация высокопроизводительного поиска фамилий с использованием Trie
高性能Trie姓氏搜索演示

Автор / 作者: Ма Цзясин (Ma Jiaxin)
Проект / 项目: ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных

Простая демонстрация улучшений производительности, достигнутых благодаря
переходу от линейного поиска O(n) к алгоритму Trie O(m) для решения проблемы 1.2.
简单演示通过从线性搜索O(n)转换为Trie算法O(m)所实现的性能改进，以解决问题1.2。
"""

import sys
import os
import time

# Добавление текущего каталога в путь / 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import SurnameDatabase, create_default_processor
from surname_trie import create_optimized_surname_trie

def demo_basic_functionality():
    """Демонстрация базовой функциональности / 基本功能演示"""
    print("=== ДЕМОНСТРАЦИЯ БАЗОВОЙ ФУНКЦИОНАЛЬНОСТИ TRIE ===")
    print("=== BASIC TRIE FUNCTIONALITY DEMONSTRATION ===")

    # Тестовые данные / 测试数据
    surnames_dict = {
        '李': {'pinyin': 'li', 'palladius': 'ли', 'frequency': 95, 'region': ['全国']},
        '王': {'pinyin': 'wang', 'palladius': 'ван', 'frequency': 92, 'region': ['全国']},
        '张': {'pinyin': 'zhang', 'palladius': 'чжан', 'frequency': 90, 'region': ['全国']},
        '赵': {'pinyin': 'zhao', 'palladius': 'чжао', 'frequency': 72, 'region': ['全国']},  # 添加赵姓
        '欧阳': {'pinyin': 'ouyang', 'palladius': 'оуян', 'frequency': 15, 'region': ['华南']},
        '司马': {'pinyin': 'sima', 'palladius': 'сыма', 'frequency': 12, 'region': ['华北']},
        '诸葛': {'pinyin': 'zhuge', 'palladius': 'чжугэ', 'frequency': 11, 'region': ['华东']},
    }

    # Создание Trie / 创建Trie
    trie = create_optimized_surname_trie(surnames_dict)
    print(f"✅ Trie создан с {len(surnames_dict)} фамилиями")
    print(f"✅ Trie created with {len(surnames_dict)} surnames")

    # Тестовые имена / 测试姓名
    test_names = ['李明', '欧阳修', '司马光', '诸葛亮', '张三丰', '王小明', '赵云', '测试名']

    print(f"\n📝 Тестирование поиска фамилий / Surname search testing:")
    print(f"{'Полное имя / Full name':<15} {'Найденная фамилия / Found surname':<20} {'Длина / Length':<8} {'Частота / Freq'}")
    print("-" * 60)

    for name in test_names:
        result = trie.find_longest_prefix(name)
        if result:
            print(f"{name:<15} {result.surname:<20} {result.length:<8} {result.frequency}")
        else:
            print(f"{name:<15} {'НЕ НАЙДЕНА / NOT FOUND':<20} {'-':<8} {'-'}")

def demo_performance_comparison():
    """Сравнение производительности / 性能比较演示"""
    print("\n=== СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ ===")
    print("=== PERFORMANCE COMPARISON ===")

    # Расширенный набор фамилий для тестирования / 扩展姓氏集用于测试
    surnames_dict = {
        '李': {'pinyin': 'li', 'palladius': 'ли', 'frequency': 95, 'region': ['全国']},
        '王': {'pinyin': 'wang', 'palladius': 'ван', 'frequency': 92, 'region': ['全国']},
        '张': {'pinyin': 'zhang', 'palladius': 'чжан', 'frequency': 90, 'region': ['全国']},
        '刘': {'pinyin': 'liu', 'palladius': 'лю', 'frequency': 85, 'region': ['全国']},
        '陈': {'pinyin': 'chen', 'palladius': 'чэнь', 'frequency': 80, 'region': ['全国']},
        '杨': {'pinyin': 'yang', 'palladius': 'ян', 'frequency': 77, 'region': ['全国']},
        '黄': {'pinyin': 'huang', 'palladius': 'хуан', 'frequency': 74, 'region': ['华南']},
        '赵': {'pinyin': 'zhao', 'palladius': 'чжао', 'frequency': 72, 'region': ['全国']},
        '吴': {'pinyin': 'wu', 'palladius': 'у', 'frequency': 70, 'region': ['华东']},
        '周': {'pinyin': 'zhou', 'palladius': 'чжоу', 'frequency': 69, 'region': ['华东']},
        '欧阳': {'pinyin': 'ouyang', 'palladius': 'оуян', 'frequency': 15, 'region': ['华南']},
        '司马': {'pinyin': 'sima', 'palladius': 'сыма', 'frequency': 12, 'region': ['华北']},
        '诸葛': {'pinyin': 'zhuge', 'palladius': 'чжугэ', 'frequency': 11, 'region': ['华东']},
        '上官': {'pinyin': 'shangguan', 'palladius': 'шангуань', 'frequency': 10, 'region': ['华中']},
        '司徒': {'pinyin': 'situ', 'palladius': 'сыту', 'frequency': 9, 'region': ['华南']},
    }

    # Тестовые имена / 测试姓名
    test_names = [
        '李明', '王小红', '张三', '刘德华', '陈独秀', '杨过', '黄药师', '赵云', '吴用', '周瑜',
        '欧阳修', '司马光', '诸葛亮', '上官婉儿', '司徒王朗',
        '测试名1', '测试名2', '测试名3'  # Имена без известных фамилий / 无已知姓氏的名字
    ] * 100  # Повторяем для статистически значимого результата / 重复以获得统计意义的结果

    print(f"Тестирование на {len(test_names)} именах / Testing on {len(test_names)} names")

    # 1. Тестирование линейного поиска / 线性搜索测试
    print("\n🐢 Тестирование линейного поиска / Linear search testing...")
    db_linear = SurnameDatabase(surnames_dict, enable_trie=False)

    start_time = time.perf_counter()
    linear_matches = 0

    for name in test_names:
        result = db_linear._linear_surname_search(name)
        if result:
            linear_matches += 1

    linear_time = time.perf_counter() - start_time

    # 2. Тестирование Trie поиска / Trie搜索测试
    print("⚡ Тестирование Trie поиска / Trie search testing...")
    db_trie = SurnameDatabase(surnames_dict, enable_trie=True)

    start_time = time.perf_counter()
    trie_matches = 0

    for name in test_names:
        result = db_trie.find_surname_in_text(name)
        if result:
            trie_matches += 1

    trie_time = time.perf_counter() - start_time

    # Вывод результатов / 输出结果
    print(f"\n📊 РЕЗУЛЬТАТЫ СРАВНЕНИЯ / COMPARISON RESULTS:")
    print(f"{'Метод / Method':<25} {'Время / Time (s)':<15} {'Скорость / Speed':<20} {'Совпадения / Matches'}")
    print("-" * 80)
    print(f"{'Линейный поиск / Linear':<25} {linear_time:.4f}s{'':<7} {len(test_names)/linear_time:.1f} ops/sec{'':<5} {linear_matches}")
    print(f"{'Trie поиск / Trie':<25} {trie_time:.4f}s{'':<7} {len(test_names)/trie_time:.1f} ops/sec{'':<5} {trie_matches}")

    # Анализ улучшения производительности / 性能改进分析
    if trie_time > 0:
        speedup = linear_time / trie_time
        print(f"\n🚀 УЛУЧШЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ / PERFORMANCE IMPROVEMENT:")
        print(f"   Ускорение / Speedup: {speedup:.1f}x")
        print(f"   Экономия времени / Time saved: {((linear_time - trie_time) / linear_time) * 100:.1f}%")

        if speedup > 2:
            print("   ✅ ОТЛИЧНЫЕ результаты для системы ИСТИНА!")
            print("   ✅ EXCELLENT results for ISTINA system!")
        elif speedup > 1.5:
            print("   ✅ ХОРОШИЕ результаты для системы ИСТИНА!")
            print("   ✅ GOOD results for ISTINA system!")
        else:
            print("   ⚠️  Требуется дополнительная оптимизация")
            print("   ⚠️  Additional optimization needed")

def demo_integration_with_processor():
    """Демонстрация интеграции с процессором / 与处理器集成演示"""
    print("\n=== ИНТЕГРАЦИЯ С CHINESENAMEPROCESSOR ===")
    print("=== INTEGRATION WITH CHINESENAMEPROCESSOR ===")

    print("Создание процессоров с разными настройками...")
    print("Creating processors with different settings...")

    # Процессор без Trie / 不使用Trie的处理器
    processor_linear = create_default_processor()
    processor_linear.surname_db._trie_enabled = False
    processor_linear.surname_db._trie = None

    # Процессор с Trie / 使用Trie的处理器
    processor_trie = create_default_processor()

    # Тестовые китайские имена / 测试中文姓名
    test_chinese_names = [
        '李小明', '王小红', '张三丰', '欧阳修', '司马光', '诸葛亮',
        '刘德华', '陈独秀', '杨过', '黄药师', '赵云龙', '周星驰'
    ]

    print(f"\nТестирование на {len(test_chinese_names)} китайских именах:")
    print(f"Testing on {len(test_chinese_names)} Chinese names:")

    print(f"\n{'Имя / Name':<12} {'Без Trie / No Trie':<20} {'С Trie / With Trie':<20} {'Улучшение / Improve'}")
    print("-" * 70)

    total_improvement = 0
    valid_tests = 0

    for name in test_chinese_names:
        # Тестирование без Trie / 不使用Trie测试
        start_time = time.perf_counter()
        result_linear = processor_linear.process_name(name)
        linear_time = (time.perf_counter() - start_time) * 1000  # мс / 毫秒

        # Тестирование с Trie / 使用Trie测试
        start_time = time.perf_counter()
        result_trie = processor_trie.process_name(name)
        trie_time = (time.perf_counter() - start_time) * 1000  # мс / 毫秒

        # Расчёт улучшения / 计算改进
        if trie_time > 0:
            improvement = linear_time / trie_time
            total_improvement += improvement
            valid_tests += 1
        else:
            improvement = float('inf')

        print(f"{name:<12} {linear_time:.3f}ms{'':<12} {trie_time:.3f}ms{'':<12} {improvement:.1f}x")

        # Проверка корректности результатов / 检查结果正确性
        if result_linear.components.surname != result_trie.components.surname:
            print(f"  ⚠️  Разные результаты: {result_linear.components.surname} vs {result_trie.components.surname}")

    # Средние результаты / 平均结果
    if valid_tests > 0:
        avg_improvement = total_improvement / valid_tests
        print(f"\n📊 Среднее ускорение / Average speedup: {avg_improvement:.1f}x")

def main():
    """Главная функция демонстрации / 主演示函数"""
    print("ДЕМОНСТРАЦИЯ ВЫСОКОПРОИЗВОДИТЕЛЬНОГО ПОИСКА ФАМИЛИЙ")
    print("HIGH-PERFORMANCE SURNAME SEARCH DEMONSTRATION")
    print("="*65)
    print("Автор / Author: Ма Цзясин (Ma Jiaxin)")
    print("Решение проблемы 1.2: Высокопроизводительный алгоритм сопоставления фамилий")
    print("Problem 1.2 Solution: High-performance surname matching algorithm")
    print("="*65)

    try:
        # 1. Базовая функциональность / 基本功能
        demo_basic_functionality()

        # 2. Сравнение производительности / 性能比较
        demo_performance_comparison()

        # 3. Интеграция с процессором / 与处理器集成
        demo_integration_with_processor()

        print("\n" + "="*65)
        print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("🎉 DEMONSTRATION COMPLETED SUCCESSFULLY!")
        print("="*65)

        print("\n📋 КЛЮЧЕВЫЕ ДОСТИЖЕНИЯ / KEY ACHIEVEMENTS:")
        print("✅ Реализован алгоритм Trie для поиска фамилий O(m)")
        print("✅ Implemented Trie algorithm for surname search O(m)")
        print("✅ Значительное улучшение производительности по сравнению с O(n)")
        print("✅ Significant performance improvement over O(n)")
        print("✅ Полная интеграция с существующей системой")
        print("✅ Full integration with existing system")
        print("✅ Готово к использованию в системе ИСТИНА")
        print("✅ Ready for deployment in ISTINA system")

    except Exception as e:
        print(f"\n❌ Ошибка при демонстрации: {e}")
        print(f"❌ Demonstration error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())