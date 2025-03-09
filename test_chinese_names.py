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
    CHINESE_SURNAMES
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
        "Zhang San",
        "Ouyang Xiu",
        "Sima Guang"
    ]
    
    for name in pinyin_test_cases:
        result = identify_transliterated_chinese_name(name)
        if result:
            print_result(name, result)


def export_surnames_database():
    """Экспорт базы данных китайских фамилий в виде списка"""
    print(f"\n=== База данных китайских фамилий ===")
    print(f"Всего содержит {len(CHINESE_SURNAMES)} фамилий")
    
    # Вывод количества однословных и составных фамилий
    single_char_surnames = [s for s in CHINESE_SURNAMES.keys() if len(s) == 1]
    multiple_char_surnames = [s for s in CHINESE_SURNAMES.keys() if len(s) > 1]
    
    print(f"Однословные фамилии: {len(single_char_surnames)}")
    print(f"Составные фамилии: {len(multiple_char_surnames)}")
    
    # Вывод нескольких примеров
    print("\nПримеры однословных фамилий:")
    for i, surname in enumerate(single_char_surnames):
        if i >= 5:
            break
        info = CHINESE_SURNAMES[surname]
        print(f"  - {surname}: пиньинь = {info['pinyin']}, система Палладия = {info['palladius']}")
    
    print("\nПримеры составных фамилий:")
    for i, surname in enumerate(multiple_char_surnames):
        if i >= 5:
            break
        info = CHINESE_SURNAMES[surname]
        print(f"  - {surname}: пиньинь = {info['pinyin']}, система Палладия = {info['palladius']}")
    
    # Вывод количества транслитераций пиньинь и системы Палладия
    pinyin_count = len(set(info['pinyin'] for info in CHINESE_SURNAMES.values()))
    palladius_count = len(set(info['palladius'] for info in CHINESE_SURNAMES.values()))
    
    print(f"\nТранслитераций пиньинь: {pinyin_count}")
    print(f"Транслитераций системы Палладия: {palladius_count}")


def main():
    """Основная функция"""
    print("Тестирование обработки китайских имен")
    
    # Тестирование чистых китайских имен
    test_pure_chinese_names()
    
    # Тестирование транслитерированных китайских имен
    test_transliterated_chinese_names()
    
    # Отображение информации о базе данных фамилий
    export_surnames_database()


if __name__ == "__main__":
    main() 