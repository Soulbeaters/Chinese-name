# -*- coding: utf-8 -*-
"""
Тестирование производительности высокопроизводительного алгоритма поиска фамилий
高性能姓氏搜索算法性能基准测试

Автор / 作者: Ма Цзясин (Ma Jiaxin)
Проект / 项目: ИСТИНА - Интеллектуальная Система Тематического Исследования НАукометрических данных
Модуль / 模块: Сравнительное тестирование производительности линейного поиска и Trie

Описание / 描述:
Данный модуль проводит комплексное тестирование производительности для сравнения
традиционного линейного поиска O(n) с высокопроизводительным алгоритмом Trie O(m).
Включает тестирование различных сценариев нагрузки для оценки масштабируемости
системы обработки китайских имён.

该模块进行全面的性能测试，比较传统线性搜索O(n)与高性能Trie算法O(m)。
包括各种负载场景的测试，以评估中文姓名处理系统的可扩展性。
"""

import time
import random
import statistics
import sys
import os
from typing import List, Dict, Tuple
from dataclasses import dataclass

# Добавление текущего каталога в путь Python / 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import SurnameDatabase, ChineseNameProcessor, create_default_processor
from surname_trie import SurnameTrie, create_optimized_surname_trie

@dataclass
class BenchmarkResult:
    """
    Результат бенчмарка / 基准测试结果

    Поля / 字段:
        test_name (str): Название теста / 测试名称
        method (str): Метод тестирования / 测试方法
        total_time (float): Общее время в секундах / 总时间（秒）
        avg_time (float): Среднее время на операцию в мс / 每操作平均时间（毫秒）
        operations_per_second (float): Операций в секунду / 每秒操作数
        memory_usage (int): Использование памяти в байтах / 内存使用（字节）
        success_rate (float): Процент успешных операций / 成功操作百分比
    """
    test_name: str
    method: str
    total_time: float
    avg_time: float
    operations_per_second: float
    memory_usage: int
    success_rate: float


class PerformanceBenchmark:
    """
    Система комплексного тестирования производительности / 全面性能测试系统

    Проводит сравнительное тестирование различных алгоритмов поиска фамилий
    для оценки производительности в условиях, аналогичных системе ИСТИНА.
    进行各种姓氏搜索算法的比较测试，以评估类似ИСТИНА系统条件下的性能。
    """

    def __init__(self):
        """Инициализация системы тестирования / 初始化测试系统"""
        self.results: List[BenchmarkResult] = []

        # Создание тестовых данных / 创建测试数据
        self.surnames_dict = self._create_extended_surnames_dict()
        self.test_names = self._generate_test_names()

        print("СИСТЕМА ТЕСТИРОВАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ ПОИСКА ФАМИЛИЙ")
        print("SURNAME SEARCH PERFORMANCE TESTING SYSTEM")
        print("="*70)
        print(f"Подготовлено фамилий / Surnames prepared: {len(self.surnames_dict)}")
        print(f"Тестовых имён / Test names: {len(self.test_names)}")
        print("="*70)

    def _create_extended_surnames_dict(self) -> Dict[str, Dict]:
        """
        Создание расширенного набора фамилий для тестирования / 创建扩展姓氏集用于测试

        Returns / 返回:
            Dict[str, Dict]: Расширенный словарь фамилий / 扩展姓氏字典
        """
        # Базовый набор популярных фамилий / 基础热门姓氏集
        base_surnames = {
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
            '徐': {'pinyin': 'xu', 'palladius': 'сюй', 'frequency': 64, 'region': ['华东']},
            '孙': {'pinyin': 'sun', 'palladius': 'сунь', 'frequency': 63, 'region': ['华东']},
            '马': {'pinyin': 'ma', 'palladius': 'ма', 'frequency': 62, 'region': ['西北']},
            '朱': {'pinyin': 'zhu', 'palladius': 'чжу', 'frequency': 60, 'region': ['华东']},
            '胡': {'pinyin': 'hu', 'palladius': 'ху', 'frequency': 59, 'region': ['华中']},

            # Составные фамилии / 复合姓氏
            '欧阳': {'pinyin': 'ouyang', 'palladius': 'оуян', 'frequency': 15, 'region': ['华南']},
            '司马': {'pinyin': 'sima', 'palladius': 'сыма', 'frequency': 12, 'region': ['华北']},
            '诸葛': {'pinyin': 'zhuge', 'palladius': 'чжугэ', 'frequency': 11, 'region': ['华东']},
            '上官': {'pinyin': 'shangguan', 'palladius': 'шангуань', 'frequency': 10, 'region': ['华中']},
            '司徒': {'pinyin': 'situ', 'palladius': 'сыту', 'frequency': 9, 'region': ['华南']},
            '东方': {'pinyin': 'dongfang', 'palladius': 'дунфан', 'frequency': 8, 'region': ['华东']},
            '独孤': {'pinyin': 'dugu', 'palladius': 'дугу', 'frequency': 7, 'region': ['西北']},
            '慕容': {'pinyin': 'murong', 'palladius': 'жуйжун', 'frequency': 7, 'region': ['东北']},
        }

        # Добавление дополнительных фамилий для масштабного тестирования / 添加额外姓氏用于大规模测试
        additional_surnames = [
            '郭', '何', '高', '林', '罗', '郑', '梁', '谢', '宋', '唐',
            '许', '韩', '冯', '邓', '曹', '彭', '曾', '肖', '田', '董',
            '袁', '潘', '蔡', '蒋', '余', '于', '杜', '叶', '程', '魏'
        ]

        for i, surname in enumerate(additional_surnames):
            base_surnames[surname] = {
                'pinyin': f'test{i}',
                'palladius': f'тест{i}',
                'frequency': max(1, 45 - i),
                'region': ['测试区']
            }

        return base_surnames

    def _generate_test_names(self) -> List[str]:
        """
        Генерирует набор тестовых имён / 生成测试姓名集

        Returns / 返回:
            List[str]: Список тестовых имён / 测试姓名列表
        """
        surnames = list(self.surnames_dict.keys())
        given_names = ['明', '华', '军', '红', '丽', '强', '伟', '芳', '敏', '静',
                      '建国', '志强', '小明', '小红', '春花', '秋月', '国庆', '建华']

        test_names = []

        # Создание комбинаций фамилий и имён / 创建姓氏和名字的组合
        for surname in surnames[:20]:  # Используем первые 20 фамилий / 使用前20个姓氏
            for given_name in given_names[:10]:  # Используем первые 10 имён / 使用前10个名字
                test_names.append(surname + given_name)

        # Добавление случайных комбинаций / 添加随机组合
        for _ in range(1000):
            surname = random.choice(surnames)
            given_name = random.choice(given_names)
            test_names.append(surname + given_name)

        # Добавление имён, которые НЕ начинаются с фамилий / 添加不以姓氏开头的名字
        non_surname_names = ['abc明', 'xyz华', '123军', 'test红']
        test_names.extend(non_surname_names * 50)  # Повторяем для статистики / 重复以获得统计数据

        random.shuffle(test_names)
        return test_names

    def benchmark_linear_search(self, iterations: int = 1000) -> BenchmarkResult:
        """
        Тестирование линейного поиска / 线性搜索基准测试

        Args / 参数:
            iterations (int): Количество итераций / 迭代次数

        Returns / 返回:
            BenchmarkResult: Результат тестирования / 测试结果
        """
        print(f"\n🔍 Тестирование линейного поиска / Linear search benchmark...")
        print(f"Итераций / Iterations: {iterations}")

        # Создание базы данных БЕЗ Trie / 创建不带Trie的数据库
        db = SurnameDatabase(self.surnames_dict, enable_trie=False)

        test_names = self.test_names[:iterations]
        successful_matches = 0
        times = []

        for name in test_names:
            start_time = time.perf_counter()

            # Линейный поиск / 线性搜索
            result = db._linear_surname_search(name)

            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # в миллисекундах / 以毫秒为单位

            if result:
                successful_matches += 1

        total_time = sum(times) / 1000  # в секундах / 以秒为单位
        avg_time = statistics.mean(times)
        success_rate = (successful_matches / len(test_names)) * 100

        return BenchmarkResult(
            test_name="Поиск фамилий / Surname Search",
            method="Линейный поиск / Linear Search",
            total_time=total_time,
            avg_time=avg_time,
            operations_per_second=len(test_names) / total_time,
            memory_usage=sys.getsizeof(db._surnames) + sys.getsizeof(db._compound_surnames),
            success_rate=success_rate
        )

    def benchmark_trie_search(self, iterations: int = 1000) -> BenchmarkResult:
        """
        Тестирование поиска через Trie / Trie搜索基准测试

        Args / 参数:
            iterations (int): Количество итераций / 迭代次数

        Returns / 返回:
            BenchmarkResult: Результат тестирования / 测试结果
        """
        print(f"\n⚡ Тестирование Trie поиска / Trie search benchmark...")
        print(f"Итераций / Iterations: {iterations}")

        # Создание базы данных С Trie / 创建带Trie的数据库
        db = SurnameDatabase(self.surnames_dict, enable_trie=True)

        test_names = self.test_names[:iterations]
        successful_matches = 0
        times = []

        for name in test_names:
            start_time = time.perf_counter()

            # Trie поиск / Trie搜索
            result = db.find_surname_in_text(name)

            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # в миллисекундах / 以毫秒为单位

            if result:
                successful_matches += 1

        total_time = sum(times) / 1000  # в секундах / 以秒为单位
        avg_time = statistics.mean(times)
        success_rate = (successful_matches / len(test_names)) * 100

        # Приблизительная оценка памяти Trie / Trie内存的近似估计
        trie_memory = sys.getsizeof(db._trie) if db._trie else 0

        return BenchmarkResult(
            test_name="Поиск фамилий / Surname Search",
            method="Trie поиск / Trie Search",
            total_time=total_time,
            avg_time=avg_time,
            operations_per_second=len(test_names) / total_time,
            memory_usage=sys.getsizeof(db._surnames) + trie_memory,
            success_rate=success_rate
        )

    def benchmark_batch_processing(self, batch_size: int = 10000) -> Tuple[BenchmarkResult, BenchmarkResult]:
        """
        Тестирование пакетной обработки / 批量处理基准测试

        Args / 参数:
            batch_size (int): Размер пакета / 批量大小

        Returns / 返回:
            Tuple[BenchmarkResult, BenchmarkResult]: (линейный, Trie) результаты / (线性, Trie) 结果
        """
        print(f"\n📦 Тестирование пакетной обработки / Batch processing benchmark...")
        print(f"Размер пакета / Batch size: {batch_size}")

        # Генерация большого набора тестовых данных / 生成大量测试数据
        large_test_set = []
        surnames = list(self.surnames_dict.keys())
        given_names = ['明', '华', '军', '红', '丽', '强', '伟', '芳', '敏', '静']

        for _ in range(batch_size):
            surname = random.choice(surnames)
            given_name = random.choice(given_names)
            large_test_set.append(surname + given_name)

        # Тестирование с процессором БЕЗ Trie / 使用不带Trie的处理器测试
        processor_linear = ChineseNameProcessor(
            surname_db=SurnameDatabase(self.surnames_dict, enable_trie=False)
        )

        start_time = time.perf_counter()
        results_linear = processor_linear.batch_process(large_test_set)
        linear_time = time.perf_counter() - start_time

        linear_success = sum(1 for r in results_linear if r.is_successful())

        # Тестирование с процессором С Trie / 使用带Trie的处理器测试
        processor_trie = ChineseNameProcessor(
            surname_db=SurnameDatabase(self.surnames_dict, enable_trie=True)
        )

        start_time = time.perf_counter()
        results_trie = processor_trie.batch_process(large_test_set)
        trie_time = time.perf_counter() - start_time

        trie_success = sum(1 for r in results_trie if r.is_successful())

        linear_result = BenchmarkResult(
            test_name="Пакетная обработка / Batch Processing",
            method="Линейный поиск / Linear Search",
            total_time=linear_time,
            avg_time=(linear_time / batch_size) * 1000,
            operations_per_second=batch_size / linear_time,
            memory_usage=0,
            success_rate=(linear_success / batch_size) * 100
        )

        trie_result = BenchmarkResult(
            test_name="Пакетная обработка / Batch Processing",
            method="Trie поиск / Trie Search",
            total_time=trie_time,
            avg_time=(trie_time / batch_size) * 1000,
            operations_per_second=batch_size / trie_time,
            memory_usage=0,
            success_rate=(trie_success / batch_size) * 100
        )

        return linear_result, trie_result

    def benchmark_scalability(self) -> List[BenchmarkResult]:
        """
        Тестирование масштабируемости / 可扩展性基准测试

        Returns / 返回:
            List[BenchmarkResult]: Результаты для разных размеров данных / 不同数据大小的结果
        """
        print(f"\n📈 Тестирование масштабируемости / Scalability benchmark...")

        test_sizes = [100, 500, 1000, 5000, 10000]
        results = []

        for size in test_sizes:
            print(f"  Тестирование размера / Testing size: {size}")

            # Trie поиск / Trie搜索
            trie_result = self.benchmark_trie_search(size)
            trie_result.test_name = f"Масштабируемость ({size} операций) / Scalability ({size} ops)"

            results.append(trie_result)

        return results

    def run_comprehensive_benchmark(self):
        """
        Запуск полного комплекса тестов / 运行全面基准测试

        Выполняет все виды тестирования производительности и выводит сравнительные результаты.
        执行所有性能测试类型并输出比较结果。
        """
        print("\n🚀 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("🚀 RUNNING COMPREHENSIVE PERFORMANCE BENCHMARK")
        print("="*70)

        # 1. Сравнение линейного поиска и Trie / 线性搜索与Trie比较
        linear_result = self.benchmark_linear_search(1000)
        trie_result = self.benchmark_trie_search(1000)
        self.results.extend([linear_result, trie_result])

        # 2. Тестирование пакетной обработки / 批量处理测试
        batch_linear, batch_trie = self.benchmark_batch_processing(5000)
        self.results.extend([batch_linear, batch_trie])

        # 3. Тестирование масштабируемости / 可扩展性测试
        scalability_results = self.benchmark_scalability()
        self.results.extend(scalability_results)

        # Вывод результатов / 输出结果
        self._print_comprehensive_results()

        # Анализ и рекомендации / 分析和建议
        self._analyze_results()

    def _print_comprehensive_results(self):
        """Вывод подробных результатов / 输出详细结果"""
        print("\n" + "="*70)
        print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("PERFORMANCE BENCHMARK RESULTS")
        print("="*70)

        for result in self.results:
            print(f"\n📊 {result.test_name}")
            print(f"   Метод / Method: {result.method}")
            print(f"   Общее время / Total time: {result.total_time:.4f} сек / sec")
            print(f"   Среднее время / Average time: {result.avg_time:.4f} мс / ms")
            print(f"   Операций/сек / Ops per sec: {result.operations_per_second:.1f}")
            print(f"   Успешность / Success rate: {result.success_rate:.1f}%")

        # Сравнительная таблица / 比较表
        print("\n" + "="*70)
        print("СРАВНИТЕЛЬНАЯ ТАБЛИЦА / COMPARISON TABLE")
        print("="*70)
        print(f"{'Тест / Test':<30} {'Метод / Method':<20} {'Время мс / Time ms':<15} {'Ops/sec':<10}")
        print("-" * 70)

        for result in self.results:
            test_name = result.test_name[:29]
            method = result.method[:19]
            print(f"{test_name:<30} {method:<20} {result.avg_time:<14.4f} {result.operations_per_second:<9.1f}")

    def _analyze_results(self):
        """Анализ результатов и рекомендации / 结果分析和建议"""
        print("\n" + "="*70)
        print("АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ / PERFORMANCE ANALYSIS")
        print("="*70)

        # Поиск результатов линейного поиска и Trie / 查找线性搜索和Trie结果
        linear_search = None
        trie_search = None

        for result in self.results:
            if result.test_name == "Поиск фамилий / Surname Search":
                if "Линейный" in result.method:
                    linear_search = result
                elif "Trie" in result.method:
                    trie_search = result

        if linear_search and trie_search:
            speed_improvement = linear_search.avg_time / trie_search.avg_time
            throughput_improvement = trie_search.operations_per_second / linear_search.operations_per_second

            print(f"📈 Улучшение скорости / Speed improvement: {speed_improvement:.1f}x")
            print(f"📈 Улучшение пропускной способности / Throughput improvement: {throughput_improvement:.1f}x")

            # Оценка для системы ИСТИНА / ИСТИНА系统评估
            if speed_improvement > 2.0:
                print("✅ ОТЛИЧНАЯ производительность для системы ИСТИНА")
                print("✅ EXCELLENT performance for ISTINA system")
            elif speed_improvement > 1.5:
                print("✅ ХОРОШАЯ производительность для системы ИСТИНА")
                print("✅ GOOD performance for ISTINA system")
            else:
                print("⚠️  ТРЕБУЕТСЯ дополнительная оптимизация")
                print("⚠️  ADDITIONAL optimization required")

        # Рекомендации / 建议
        print(f"\n📋 РЕКОМЕНДАЦИИ ДЛЯ ИНТЕГРАЦИИ С ИСТИНА:")
        print(f"📋 ISTINA INTEGRATION RECOMMENDATIONS:")
        print(f"1. Использовать Trie для всех операций поиска фамилий")
        print(f"   Use Trie for all surname search operations")
        print(f"2. Включить кэширование для часто используемых запросов")
        print(f"   Enable caching for frequently used queries")
        print(f"3. Настроить пакетную обработку для больших объёмов данных")
        print(f"   Configure batch processing for large data volumes")


def main():
    """Главная функция запуска тестирования / 主测试运行函数"""
    print("Система тестирования производительности поиска китайских фамилий")
    print("Chinese Surname Search Performance Testing System")
    print("Автор / Author: Ма Цзясин (Ma Jiaxin)")
    print(f"Дата / Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Создание и запуск тестирования / 创建和运行测试
    benchmark = PerformanceBenchmark()

    try:
        benchmark.run_comprehensive_benchmark()

        # Сохранение результатов (опционально) / 保存结果（可选）
        # benchmark.save_results_to_json("performance_results.json")

        print(f"\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО / TESTING COMPLETED SUCCESSFULLY")
        print(f"Всего тестов / Total tests: {len(benchmark.results)}")

    except Exception as e:
        print(f"\n❌ ОШИБКА ПРИ ТЕСТИРОВАНИИ / TESTING ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())