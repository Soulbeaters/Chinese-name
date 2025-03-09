#!/usr/bin/env python
# -*- coding: utf-8 -*-

from split_authors import (
    is_chinese_char,
    is_chinese_name,
    split_chinese_name,
    CHINESE_SURNAMES
)

def test_chinese_char():
    """Тестирование распознавания китайских иероглифов"""
    print("Тестирование распознавания китайских иероглифов:")
    for char in ['李', 'A', '1', '王', 'Ж']:
        result = is_chinese_char(char)
        print(f"  '{char}' является китайским иероглифом: {result}")

def test_chinese_name():
    """Тестирование распознавания китайских имен"""
    print("\nТестирование распознавания китайских имен:")
    for name in ['李明', 'John', '王小红', 'Li Ming', '诸葛亮']:
        result = is_chinese_name(name)
        print(f"  '{name}' является китайским именем: {result}")

def test_split_name():
    """Тестирование разделения китайских имен"""
    print("\nТестирование разделения китайских имен:")
    for name in ['李明', '王小红', '张三', '欧阳修', '司马光']:
        if is_chinese_name(name):
            result = split_chinese_name(name)
            print(f"  '{name}' результат разделения: фамилия='{result[0]}', имя='{result[1]}', отчество='{result[2]}'")

def test_surnames_db():
    """Тестирование базы данных фамилий"""
    print("\nТестирование базы данных фамилий:")
    print(f"  В базе данных всего {len(CHINESE_SURNAMES)} фамилий")
    
    # Показать несколько примеров
    examples = ['李', '王', '欧阳', '司马']
    for surname in examples:
        if surname in CHINESE_SURNAMES:
            info = CHINESE_SURNAMES[surname]
            print(f"  '{surname}': пиньинь='{info['pinyin']}', система Палладия='{info['palladius']}'")

def main():
    """Основная функция"""
    print("Простое тестирование обработки китайских имен\n")
    
    test_chinese_char()
    test_chinese_name()
    test_split_name()
    test_surnames_db()

if __name__ == "__main__":
    main() 