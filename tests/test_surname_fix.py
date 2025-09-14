# -*- coding: utf-8 -*-
"""
快速验证姓氏数据修复 / Quick surname data fix verification
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import create_default_processor
from surname_trie import create_optimized_surname_trie

def test_surname_fix():
    """测试姓氏修复 / Test surname fix"""
    print("=== 姓氏数据修复验证 / SURNAME DATA FIX VERIFICATION ===\n")

    # 创建默认处理器 / Create default processor
    processor = create_default_processor()

    # 测试有问题的姓名 / Test problematic names
    test_names = [
        '赵云',      # 之前找不到的 / Previously not found
        '李明',      # 应该找到的 / Should be found
        '欧阳修',    # 复合姓氏 / Compound surname
        '司马光',    # 复合姓氏 / Compound surname
        '黄药师',    # 新增的姓氏 / Newly added surname
        '周星驰',    # 新增的姓氏 / Newly added surname
        '郭靖',      # 新增的姓氏 / Newly added surname
        '测试名'     # 不存在的姓氏 / Non-existent surname
    ]

    print("使用ChineseNameProcessor测试 / Testing with ChineseNameProcessor:")
    print(f"{'姓名 / Name':<10} {'姓氏 / Surname':<8} {'名字 / Given':<8} {'置信度 / Conf':<6} {'状态 / Status'}")
    print("-" * 50)

    for name in test_names:
        result = processor.process_name(name)
        if result.is_successful():
            status = "✅ 找到 / Found"
        else:
            status = "❌ 未找到 / Not found"

        print(f"{name:<10} {result.components.surname:<8} {result.components.first_name:<8} {result.confidence_score:<6.2f} {status}")

    # 直接测试姓氏数据库 / Direct test of surname database
    print(f"\n直接测试SurnameDatabase / Direct SurnameDatabase test:")
    surname_db = processor.surname_db

    test_surnames = ['赵', '李', '欧阳', '司马', '黄', '周', '郭', '测试']

    print(f"{'姓氏 / Surname':<8} {'数据库中 / In DB':<12} {'Trie搜索 / Trie Search'}")
    print("-" * 35)

    for surname in test_surnames:
        in_db = surname_db.is_known_surname(surname)
        trie_result = surname_db.find_surname_in_text(surname + "明")  # 测试"明"作为名字

        if trie_result:
            trie_found = f"找到 {trie_result[0]} / Found {trie_result[0]}"
        else:
            trie_found = "未找到 / Not found"

        print(f"{surname:<8} {'是 / Yes' if in_db else '否 / No':<12} {trie_found}")

if __name__ == "__main__":
    test_surname_fix()