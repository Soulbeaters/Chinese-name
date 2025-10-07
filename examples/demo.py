# -*- coding: utf-8 -*-
"""
完整功能演示 / Демонстрация полной функциональности

展示使用新数据库的中文姓名处理：
- 中文姓名识别
- 拼音转写（英文）
- 俄语转写（帕拉迪）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data import (
    is_surname,
    get_surname_from_text,
    to_pinyin_string,
    to_russian,
    ALL_SURNAMES,
    CHAR_COUNT,
)

def demo_surname_detection():
    """姓氏识别演示"""
    print("=" * 60)
    print("姓氏识别演示 / Демонстрация распознавания фамилий")
    print("=" * 60)

    test_names = ['马嘉星', '李明', '王芳', '欧阳锋', '司马懿', '张三']

    for name in test_names:
        surname = get_surname_from_text(name)
        given_name = name[len(surname):]
        print(f"{name} → 姓: {surname}, 名: {given_name}")

    print(f"\n姓氏库统计: {len(ALL_SURNAMES)}个姓氏")


def demo_pinyin_transliteration():
    """拼音转写演示"""
    print("\n" + "=" * 60)
    print("拼音转写演示 / Демонстрация транслитерации пиньинь")
    print("=" * 60)

    test_names = ['马嘉星', '李明', '王芳', '欧阳锋', '司马懿', '诸葛亮']

    for name in test_names:
        pinyin = to_pinyin_string(name)
        print(f"{name} → {pinyin}")


def demo_russian_transliteration():
    """俄语转写演示"""
    print("\n" + "=" * 60)
    print("俄语帕拉迪转写演示 / Демонстрация русской транслитерации")
    print("=" * 60)

    test_names = ['马嘉星', '李明', '王芳', '欧阳锋', '司马懿', '诸葛亮']

    for name in test_names:
        russian = to_russian(name)
        print(f"{name} → {russian}")


def demo_author_processing():
    """作者信息处理演示"""
    print("\n" + "=" * 60)
    print("作者信息处理演示 / Обработка информации об авторах")
    print("=" * 60)

    authors = [
        "马嘉星",
        "李明华",
        "王晓芳",
        "欧阳明月",
    ]

    print(f"{'中文':<10} {'拼音':<20} {'俄语':<20}")
    print("-" * 60)

    for author in authors:
        surname = get_surname_from_text(author)
        pinyin = to_pinyin_string(author)
        russian = to_russian(author)
        print(f"{author:<10} {pinyin:<20} {russian:<20}")


def main():
    print("\n")
    print("█" * 60)
    print("  中文姓名处理系统 - 完整演示")
    print("  Система обработки китайских имен - Полная демонстрация")
    print("█" * 60)
    print(f"\n汉字库: {CHAR_COUNT}个字符")
    print(f"姓氏库: {len(ALL_SURNAMES)}个姓氏\n")

    demo_surname_detection()
    demo_pinyin_transliteration()
    demo_russian_transliteration()
    demo_author_processing()

    print("\n" + "=" * 60)
    print("演示完成 / Демонстрация завершена")
    print("=" * 60)


if __name__ == '__main__':
    main()
