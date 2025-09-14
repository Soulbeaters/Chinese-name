# -*- coding: utf-8 -*-
"""
分析测试成功率问题 / Analyze test success rate issue

分析为什么测试中有50个案例失败，找到根本原因并修复
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import create_default_processor

def analyze_failed_cases():
    """分析失败的测试案例"""
    print("=== 测试成功率分析 / TEST SUCCESS RATE ANALYSIS ===")
    print()

    processor = create_default_processor()

    # 重建测试数据（与test_trie_integration.py相同）
    test_names = [
        # 单字姓氏
        '李明', '王小红', '张三丰', '刘德华', '陈独秀', '杨过',
        '黄药师', '赵云龙', '周星驰', '吴用',

        # 复合姓氏
        '欧阳修', '司马光', '诸葛亮', '上官婉儿', '司徒王朗',
        '东方不败', '慕容复', '令狐冲', '独孤求败',

        # 音译姓名
        'Li Ming', 'Wang Xiaohong', 'Zhang Sanfeng', 'Ma Jiaxing',

        # 边界情况
        '测试名', '未知姓', '单字', ''
    ] * 50  # 重复50次

    print(f"总测试案例: {len(test_names)}")

    # 统计各类失败
    failed_cases = []
    empty_names = []
    chinese_failures = []
    transliterated_failures = []
    mixed_failures = []

    success_count = 0

    for i, name in enumerate(test_names):
        try:
            result = processor.process_name(name)

            if result.is_successful():
                success_count += 1
            else:
                failed_cases.append((i, name, result))

                # 分类失败原因
                if not name or name.strip() == '':
                    empty_names.append(name)
                elif name.isascii():  # 音译姓名
                    transliterated_failures.append((name, result.error_message))
                elif any('\u4e00' <= char <= '\u9fff' for char in name):  # 包含中文
                    if any(char.isascii() and char.isalpha() for char in name):  # 混合
                        mixed_failures.append((name, result.error_message))
                    else:  # 纯中文
                        chinese_failures.append((name, result.error_message))

        except Exception as e:
            failed_cases.append((i, name, f"异常: {e}"))

    print(f"成功案例: {success_count}/{len(test_names)} ({success_count/len(test_names)*100:.1f}%)")
    print(f"失败案例: {len(failed_cases)}")
    print()

    # 详细分析失败类别
    print("=== 失败案例分类分析 ===")

    if empty_names:
        print(f"1. 空字符串: {len(empty_names)} 个")
        unique_empty = list(set(empty_names))
        for empty in unique_empty:
            print(f"   '{empty}' (出现 {empty_names.count(empty)} 次)")

    if chinese_failures:
        print(f"2. 中文姓名失败: {len(chinese_failures)} 个")
        unique_chinese_failures = {}
        for name, error in chinese_failures:
            if name not in unique_chinese_failures:
                unique_chinese_failures[name] = error

        for name, error in list(unique_chinese_failures.items())[:10]:  # 只显示前10个
            print(f"   '{name}': {error}")

    if transliterated_failures:
        print(f"3. 音译姓名失败: {len(transliterated_failures)} 个")
        unique_trans_failures = {}
        for name, error in transliterated_failures:
            if name not in unique_trans_failures:
                unique_trans_failures[name] = error

        for name, error in list(unique_trans_failures.items())[:10]:
            print(f"   '{name}': {error}")

    if mixed_failures:
        print(f"4. 混合文字失败: {len(mixed_failures)} 个")
        for name, error in mixed_failures[:5]:
            print(f"   '{name}': {error}")

    print()

    # 分析具体失败的唯一案例
    print("=== 唯一失败案例详细分析 ===")

    unique_failures = {}
    for i, name, result in failed_cases:
        if name not in unique_failures:
            unique_failures[name] = result

    print(f"唯一失败案例数量: {len(unique_failures)}")

    for name, result in unique_failures.items():
        print(f"\n案例: '{name}'")
        if hasattr(result, 'error_message'):
            print(f"  错误信息: {result.error_message}")
        if hasattr(result, 'decision_path'):
            print(f"  决策路径: {result.decision_path}")

        # 尝试理解为什么失败
        if not name or name.strip() == '':
            print(f"  失败原因: 空字符串输入")
        elif name in ['测试名', '未知姓', '单字']:
            print(f"  失败原因: 包含系统中未知的姓氏")
        else:
            print(f"  失败原因: 需要进一步分析")

if __name__ == "__main__":
    analyze_failed_cases()