#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# Добавляем текущий каталог в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from split_authors import (
    is_chinese_name, 
    split_chinese_name, 
    identify_transliterated_chinese_name,
    CHINESE_SURNAMES,
    hanzi_to_pinyin,
    hanzi_to_palladius,
    hanzi_to_wade_giles,
    hanzi_to_yale,
    transliterate_chinese_name,
    compare_transliterations,
    is_simplified_chinese,
    is_traditional_chinese,
    simplified_to_traditional,
    traditional_to_simplified,
    identify_ethnic_name,
    process_ethnic_name,
    handle_rare_surname,
    handle_mixed_script_name,
    fuzzy_match_chinese_name,
    batch_process_chinese_names,
    TRANSLITERATION_PINYIN,
    TRANSLITERATION_PALLADIUS,
    TRANSLITERATION_WADE_GILES,
    TRANSLITERATION_YALE
)

def print_result(name, result):
    """Выводит результаты тестирования"""
    print(f"\nТест: '{name}'")
    print("Результат:")
    print(f"  - Фамилия: '{result[0]}', Имя: '{result[1]}', Отчество: '{result[2]}'")


def test_pure_chinese_names():
    """Тестирование чистых китайских имен"""
    print("\n=== Тестирование чистых китайских имен ===")
    
    # Тестирование отдельных китайских имен
    test_cases = [
        "李明",
        "王小红",
        "张三",
        "欧阳修",
        "司马光",
        "诸葛亮",
        "上官婉儿"
    ]
    
    for name in test_cases:
        if is_chinese_name(name):
            result = split_chinese_name(name)
            print_result(name, result)


def test_transliterated_chinese_names():
    """Тестирование транслитерированных китайских имен"""
    print("\n=== Тестирование транслитерированных китайских имен ===")
    
    # Тестирование транслитерации пиньинь (китайский порядок: фамилия + имя)
    pinyin_test_cases = [
        "Li Ming",
        "Wang Xiaohong",
        "Zhang San"
    ]
    
    for name in pinyin_test_cases:
        result = identify_transliterated_chinese_name(name)
        if result:
            print_result(name, result)
    
    # Тестирование транслитерации по системе Палладия (русская транслитерация)
    palladius_test_cases = [
        "Ли Мин",
        "Ван Сяохун",
        "Чжан Сань"
    ]
    
    for name in palladius_test_cases:
        result = identify_transliterated_chinese_name(name)
        if result:
            print_result(name, result)


def test_transliteration_systems():
    """Тестирование систем транслитерации"""
    print("\n=== Тестирование систем транслитерации ===")
    
    # Тестовые имена
    test_cases = [
        "李明",
        "王小红",
        "张三",
        "欧阳修"
    ]
    
    for name in test_cases:
        if is_chinese_name(name):
            print(f"\nИмя: {name}")
            print(f"Пиньинь: {transliterate_chinese_name(name, TRANSLITERATION_PINYIN)}")
            print(f"Система Палладия: {transliterate_chinese_name(name, TRANSLITERATION_PALLADIUS)}")
            print(f"Система Уэйда-Джайлза: {transliterate_chinese_name(name, TRANSLITERATION_WADE_GILES)}")
            print(f"Йельская система: {transliterate_chinese_name(name, TRANSLITERATION_YALE)}")
            
            # Сравнение транслитераций
            comparisons = compare_transliterations(name)
            print("Сравнение транслитераций:")
            for system, trans in comparisons.items():
                if system != 'original' and system != 'detected_system':
                    print(f"  - {system}: {trans}")


def test_simplified_traditional():
    """Тестирование преобразования между упрощенными и традиционными иероглифами"""
    print("\n=== Тестирование преобразования между упрощенными и традиционными иероглифами ===")
    
    # Пары (упрощенный, традиционный)
    test_pairs = [
        ("李明", "李明"),  # Нет изменений
        ("张三", "張三"),  # Есть изменение в первом иероглифе
        ("刘洋", "劉洋")   # Есть изменение в первом иероглифе
    ]
    
    for simplified, traditional in test_pairs:
        print(f"\nУпрощенное: {simplified}")
        print(f"Традиционное: {traditional}")
        
        # Проверка определения типа
        print(f"Является ли '{simplified}' упрощенным: {is_simplified_chinese(simplified)}")
        print(f"Является ли '{traditional}' традиционным: {is_traditional_chinese(traditional)}")
        
        # Проверка преобразования
        converted_to_traditional = simplified_to_traditional(simplified)
        converted_to_simplified = traditional_to_simplified(traditional)
        
        print(f"Преобразование '{simplified}' в традиционное: {converted_to_traditional}")
        print(f"Преобразование '{traditional}' в упрощенное: {converted_to_simplified}")


def test_ethnic_names():
    """Тестирование имен этнических меньшинств"""
    print("\n=== Тестирование имен этнических меньшинств ===")
    
    # Тестовые имена этнических меньшинств
    test_cases = [
        "拉木次仁",  # Тибетское имя
        "艾买提江",  # Уйгурское имя
        "乌力吉图",  # Монгольское имя
        "白玛央金",  # Тибетское имя
        "吐尔逊娜依"  # Уйгурское имя
    ]
    
    for name in test_cases:
        result = identify_ethnic_name(name)
        if result:
            ethnic, surname, firstname, middlename = result
            print(f"\nИмя: {name}")
            print(f"Этническая группа: {ethnic}")
            print(f"Фамилия: {surname}, Имя: {firstname}, Отчество: {middlename}")
            
            # Проверка обработки этнического имени
            processed = process_ethnic_name(name)
            if processed:
                print_result(name, processed)


def test_edge_cases():
    """Тестирование обработки краевых случаев"""
    print("\n=== Тестирование обработки краевых случаев ===")
    
    # Тестирование редких фамилий
    rare_surnames = [
        "万俟宗",  # Редкая фамилия Мо Чжи
        "百里守",  # Редкая фамилия Бай Ли
        "东郭明",  # Редкая фамилия Дун Го
        "慕容华"   # Редкая фамилия Му Жонг
    ]
    
    print("\nТестирование редких фамилий:")
    for name in rare_surnames:
        result = handle_rare_surname(name)
        print_result(name, result)
    
    # Тестирование смешанных имен
    mixed_names = [
        "李Ming",  # Китайская фамилия + латинское имя
        "Wang小红",  # Латинская фамилия + китайское имя
        "李明 Li Ming",  # Китайское имя + его транслитерация
        "张Zhang Wei伟"  # Смешанный формат
    ]
    
    print("\nТестирование смешанных имен:")
    for name in mixed_names:
        result = handle_mixed_script_name(name)
        print_result(name, result)
    
    # Тестирование нечеткого поиска
    print("\nТестирование нечеткого поиска:")
    query = "Li Min"
    candidates = ["Li Ming", "Wang Li", "Zhang Min", "Li Mei"]
    best_match, score = fuzzy_match_chinese_name(query, candidates)
    print(f"Запрос: '{query}'")
    print(f"Лучшее совпадение: '{best_match}' (счет: {score:.2f})")


def test_batch_processing():
    """Тестирование пакетной обработки имен"""
    print("\n=== Тестирование пакетной обработки имен ===")
    
    # Смешанный список имен для тестирования
    names_list = [
        "李明",  # Чистое китайское имя
        "Li Ming",  # Пиньинь (китайский порядок)
        "Ming Li",  # Пиньинь (западный порядок)
        "Ли Мин",  # Система Палладия
        "欧阳修",  # Двусложная фамилия
        "拉木次仁",  # Тибетское имя
        "Wang Xiaohong",  # Еще один пример пиньиня
        "Li M."  # Имя с инициалом
    ]
    
    # Обработка в формате кортежей
    print("\nРезультаты в формате кортежей:")
    results_tuples = batch_process_chinese_names(names_list, output_format='tuple')
    for i, result in enumerate(results_tuples):
        print(f"{i+1}. {names_list[i]} -> {result}")
    
    # Обработка в формате словарей с дополнительной информацией
    print("\nРезультаты в формате словарей:")
    results_dicts = batch_process_chinese_names(names_list, output_format='dict')
    for i, result in enumerate(results_dicts):
        print(f"\n{i+1}. {names_list[i]}:")
        print(f"  - Оригинал: {result['original']}")
        print(f"  - Фамилия: {result['surname']}")
        print(f"  - Имя: {result['firstname']}")
        print(f"  - Отчество: {result['middlename']}")
        print(f"  - Система: {result.get('system', 'неизвестно')}")
        
        # Вывод транслитераций, если доступны
        if 'transliterations' in result:
            print("  - Транслитерации:")
            for system, trans in result['transliterations'].items():
                print(f"    * {system}: {trans}")


def export_surnames_database():
    """Экспорт базы данных фамилий в JSON"""
    print("\n=== Экспорт базы данных фамилий ===")
    
    # Экспорт базы данных фамилий в JSON
    from split_authors import export_chinese_surnames_to_json
    
    export_chinese_surnames_to_json("chinese_surnames.json")
    print("База данных фамилий экспортирована в chinese_surnames.json")
    
    # Показать некоторые записи из базы данных
    print("\nПримеры записей из базы данных фамилий:")
    count = 0
    for surname, data in CHINESE_SURNAMES.items():
        if count >= 5:  # Показать только первые 5 записей
            break
        print(f"\n{surname}:")
        for key, value in data.items():
            print(f"  - {key}: {value}")
        count += 1


def main():
    """Основная функция для запуска всех тестов"""
    # Тестирование чистых китайских имен
    test_pure_chinese_names()
    
    # Тестирование транслитерированных китайских имен
    test_transliterated_chinese_names()
    
    # Тестирование систем транслитерации
    test_transliteration_systems()
    
    # Тестирование преобразования между упрощенными и традиционными иероглифами
    test_simplified_traditional()
    
    # Тестирование имен этнических меньшинств
    test_ethnic_names()
    
    # Тестирование обработки краевых случаев
    test_edge_cases()
    
    # Тестирование пакетной обработки имен
    test_batch_processing()
    
    # Экспорт базы данных фамилий
    export_surnames_database()


if __name__ == "__main__":
    main() 