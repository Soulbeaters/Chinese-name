#!/usr/bin/env python
# -*- coding: utf-8 -*-

print("Test 1")
print("Test 2")
print("Test 3")

print("=== Тестирование функций обработки китайских имен ===")

from split_authors import is_chinese_char, is_chinese_name, split_chinese_name

print("\n=== Тестирование функции is_chinese_char ===")
print(f"is_chinese_char('李') = {is_chinese_char('李')}")
print(f"is_chinese_char('A') = {is_chinese_char('A')}")

print("\n=== Тестирование функции is_chinese_name ===")
print(f"is_chinese_name('李明') = {is_chinese_name('李明')}")
print(f"is_chinese_name('John') = {is_chinese_name('John')}")

print("\n=== Тестирование функции split_chinese_name ===")
result = split_chinese_name('李明')
print(f"split_chinese_name('李明') = {result}")

print("\n=== Тестирование завершено ===") 