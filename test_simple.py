#!/usr/bin/env python
# -*- coding: utf-8 -*-

from split_authors import (
    is_chinese_char,
    is_chinese_name,
    split_chinese_name,
    CHINESE_SURNAMES,
    simplified_to_traditional,
    traditional_to_simplified,
    process_ethnic_name,
    fuzzy_match_chinese_name,
    detect_japanese_kanji,
    handle_mixed_script_name
)

def test_chinese_char():
    """Тестирование распознавания китайских иероглифов"""
    print("="*50)
    print("Тестирование распознавания китайских иероглифов:")
    print("="*50)
    for char in ['李', 'A', '1', '王', 'Ж']:
        result = is_chinese_char(char)
        print(f"  '{char}' является китайским иероглифом: {result}")

def test_chinese_name():
    """Тестирование распознавания китайских имен"""
    print("\n"+"="*50)
    print("Тестирование распознавания китайских имен:")
    print("="*50)
    for name in ['李明', 'John', '王小红', 'Li Ming', '诸葛亮']:
        result = is_chinese_name(name)
        print(f"  '{name}' является китайским именем: {result}")

def test_split_name():
    """Тестирование разделения китайских имен"""
    print("\n"+"="*50)
    print("Тестирование разделения китайских имен:")
    print("="*50)
    for name in ['李明', '王小红', '张三', '欧阳修', '司马光']:
        if is_chinese_name(name):
            result = split_chinese_name(name)
            print(f"  '{name}' результат разделения: фамилия='{result[0]}', имя='{result[1]}', отчество='{result[2]}'")

def test_surnames_db():
    """Тестирование базы данных фамилий"""
    print("\n"+"="*50)
    print("Тестирование базы данных фамилий:")
    print("="*50)
    print(f"  В базе данных всего {len(CHINESE_SURNAMES)} фамилий")
    
    # Показать несколько примеров
    examples = ['李', '王', '欧阳', '司马']
    for surname in examples:
        if surname in CHINESE_SURNAMES:
            info = CHINESE_SURNAMES[surname]
            print(f"  '{surname}': пиньинь='{info['pinyin']}', система Палладия='{info['palladius']}'")
            if 'frequency' in info:
                print(f"    Частота: {info['frequency']}")
            if 'region' in info:
                print(f"    Регионы: {', '.join(info['region'])}")

def test_simplified_traditional():
    """Тестирование конвертации между упрощенными и традиционными иероглифами"""
    print("\n"+"="*50)
    print("Тестирование конвертации иероглифов:")
    print("="*50)
    
    test_cases = [
        ('张三', '張三'),  # Упрощенный -> Традиционный
        ('李明', '李明'),  # Без изменений (одинаковые в обеих системах)
        ('马云', '馬雲')   # Оба иероглифа меняются
    ]
    
    for simplified, traditional in test_cases:
        conv_to_trad = simplified_to_traditional(simplified)
        conv_to_simp = traditional_to_simplified(traditional)
        
        print(f"  Упрощенный -> Традиционный: '{simplified}' -> '{conv_to_trad}'")
        print(f"  Традиционный -> Упрощенный: '{traditional}' -> '{conv_to_simp}'")
        print(f"  Правильно: {conv_to_trad == traditional and conv_to_simp == simplified}")

def test_ethnic_names():
    """Тестирование обработки имен этнических меньшинств"""
    print("\n"+"="*50)
    print("Тестирование обработки имен этнических меньшинств:")
    print("="*50)
    
    ethnic_names = [
        ('拉木次仁', 'Тибетское'),
        ('艾买提·买买提', 'Уйгурское'),
        ('钢巴特尔', 'Монгольское')
    ]
    
    for name, ethnic_type in ethnic_names:
        result = process_ethnic_name(name)
        print(f"  {ethnic_type} имя '{name}':")
        if result:
            print(f"    Фамилия: '{result[0]}'")
            print(f"    Имя: '{result[1]}'")
            print(f"    Отчество: '{result[2]}'")
        else:
            print("    Не распознано как этническое имя")

def test_mixed_script():
    """Тестирование обработки имен со смешанным письмом"""
    print("\n"+"="*50)
    print("Тестирование обработки имен со смешанным письмом:")
    print("="*50)
    
    mixed_names = [
        '李Ming',
        'Wang小红',
        '张San'
    ]
    
    for name in mixed_names:
        result = handle_mixed_script_name(name)
        if result:
            print(f"  '{name}' -> Фамилия='{result[0]}', Имя='{result[1]}', Отчество='{result[2]}'")
        else:
            print(f"  '{name}' не удалось обработать")

def test_fuzzy_match():
    """Тестирование нечеткого поиска имен"""
    print("\n"+"="*50)
    print("Тестирование нечеткого поиска имен:")
    print("="*50)
    
    query = "Li Min"
    candidates = ["Li Ming", "Wang Li", "Zhang Min", "Lee Min"]
    
    print(f"  Запрос: '{query}'")
    print(f"  Кандидаты: {candidates}")
    
    match, score = fuzzy_match_chinese_name(query, candidates)
    print(f"  Лучшее совпадение: '{match}' (оценка: {score:.2f})")
    
    # Тест с русской транслитерацией
    query_ru = "Ли Мин"
    candidates_ru = ["李明", "李敏", "李民"]
    
    print(f"\n  Запрос (рус.): '{query_ru}'")
    print(f"  Кандидаты: {candidates_ru}")
    
    match_ru, score_ru = fuzzy_match_chinese_name(query_ru, candidates_ru, threshold=0.6)
    if match_ru:
        print(f"  Лучшее совпадение: '{match_ru}' (оценка: {score_ru:.2f})")
    else:
        print("  Совпадений не найдено")

def test_japanese_kanji():
    """Тестирование распознавания японских кандзи"""
    print("\n"+"="*50)
    print("Тестирование распознавания японских кандзи:")
    print("="*50)
    
    test_cases = [
        '李明',  # Только китайские иероглифы
        '山田太郎',  # Японское имя с кандзи
        '橋本環奈',  # Японское имя с особыми японскими иероглифами
        'ナカムラ',  # Японское имя катаканой
        'たなか'     # Японское имя хираганой
    ]
    
    for text in test_cases:
        is_japanese = detect_japanese_kanji(text)
        print(f"  '{text}' содержит японские кандзи: {is_japanese}")

def main():
    """Основная функция"""
    print("="*50)
    print("Простое тестирование обработки китайских имен")
    print("="*50)
    
    # Базовые тесты
    test_chinese_char()
    test_chinese_name()
    test_split_name()
    test_surnames_db()
    
    # Новые тесты для расширенных функций
    test_simplified_traditional()
    test_ethnic_names()
    test_mixed_script()
    test_fuzzy_match()
    test_japanese_kanji()
    
    print("\n"+"="*50)
    print("Тестирование завершено!")
    print("="*50)

if __name__ == "__main__":
    main() 