# -*- coding: utf-8 -*-
"""
混合文字姓名处理测试 / Mixed Script Name Processing Test

测试新的 _handle_mixed_script_name 函数，验证中文和拉丁字母混合姓名的处理能力
Test the new _handle_mixed_script_name function for Chinese and Latin mixed names
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import create_default_processor

def test_mixed_script_names():
    """测试混合文字姓名处理功能"""
    print("=== 混合文字姓名处理测试 / Mixed Script Name Processing Test ===")
    print()

    processor = create_default_processor()

    # 分类测试案例
    test_categories = {
        "姓氏在前 (Surname First)": [
            ('张John', '中文姓氏+拉丁名字'),
            ('李Mary', '中文姓氏+拉丁名字'),
            ('王David', '中文姓氏+拉丁名字'),
            ('欧阳Peter', '复合中文姓氏+拉丁名字'),
            ('司马Anna', '复合中文姓氏+拉丁名字'),
            ('赵Johnson', '中文姓氏+拉丁姓氏'),
        ],

        "姓氏在后 (Surname Last)": [
            ('John张', '拉丁名字+中文姓氏'),
            ('Mary李', '拉丁名字+中文姓氏'),
            ('David王', '拉丁名字+中文姓氏'),
            ('Peter欧阳', '拉丁名字+复合中文姓氏'),
            ('Anna司马', '拉丁名字+复合中文姓氏'),
            ('Johnson赵', '拉丁姓氏+中文姓氏'),
        ],

        "复杂混合 (Complex Mixed)": [
            ('张三John', '中文姓名+拉丁名字'),
            ('李小Mary', '中文姓名+拉丁名字'),
            ('John王五', '拉丁名字+中文姓名'),
            ('David李明', '拉丁名字+中文姓名'),
            ('张John Smith', '中文姓氏+拉丁全名'),
            ('李Mary Johnson', '中文姓氏+拉丁全名'),
        ],

        "多字符组合 (Multi-character Mix)": [
            ('张JohnPeter', '中文姓氏+组合拉丁名'),
            ('李MaryAnna', '中文姓氏+组合拉丁名'),
            ('JohnPeter张', '组合拉丁名+中文姓氏'),
            ('MaryAnna李', '组合拉丁名+中文姓氏'),
        ],

        "边界情况 (Edge Cases)": [
            ('王A', '中文姓氏+单字母'),
            ('A王', '单字母+中文姓氏'),
            ('张 John', '带空格分隔'),
            ('John 张', '带空格分隔'),
            ('测试John', '未知中文字符+拉丁名字'),
            ('John测试', '拉丁名字+未知中文字符'),
        ],
    }

    all_results = []

    for category, test_cases in test_categories.items():
        print(f"=== {category} ===")
        print()

        category_results = []

        for name, description in test_cases:
            print(f"测试: '{name}' ({description})")

            try:
                result = processor.process_name(name)

                if result and result.is_successful():
                    print(f"  识别结果: 成功")
                    print(f"  姓氏: '{result.components.surname}'")
                    print(f"  名字: '{result.components.first_name}'")
                    print(f"  置信度: {result.confidence_score:.3f}")
                    print(f"  数据源类型: {result.components.source_type}")

                    # 决策路径
                    if result.decision_path:
                        print("  决策路径:")
                        for i, step in enumerate(result.decision_path, 1):
                            print(f"    {i}. {step}")

                    # 决策说明
                    if hasattr(result.components, 'decision_reason') and result.components.decision_reason:
                        print(f"  决策说明: {result.components.decision_reason}")

                    category_results.append({
                        'name': name,
                        'description': description,
                        'surname': result.components.surname,
                        'given_name': result.components.first_name,
                        'confidence': result.confidence_score,
                        'source_type': result.components.source_type,
                        'success': True
                    })

                else:
                    print(f"  识别结果: 失败")
                    if result and result.errors:
                        print(f"  错误信息: {result.errors}")

                    category_results.append({
                        'name': name,
                        'description': description,
                        'success': False
                    })

            except Exception as e:
                print(f"  处理异常: {e}")
                category_results.append({
                    'name': name,
                    'description': description,
                    'success': False,
                    'error': str(e)
                })

            print()

        all_results.extend(category_results)
        print("-" * 60)
        print()

    # 统计分析
    print("=== 混合文字处理统计分析 ===")

    total_tests = len(all_results)
    successful_tests = sum(1 for r in all_results if r['success'])
    success_rate = (successful_tests / total_tests) * 100

    print(f"总测试案例: {total_tests}")
    print(f"成功识别: {successful_tests}")
    print(f"成功率: {success_rate:.1f}%")
    print()

    # 按类别分析成功率
    for category in test_categories.keys():
        category_results = [r for r in all_results
                          if any(name == r['name'] for name, _ in test_categories[category])]
        if category_results:
            category_success = sum(1 for r in category_results if r['success'])
            category_total = len(category_results)
            category_rate = (category_success / category_total) * 100
            print(f"{category}: {category_success}/{category_total} ({category_rate:.1f}%)")

    print()

    # 置信度分析
    successful_results = [r for r in all_results if r['success'] and 'confidence' in r]
    if successful_results:
        confidences = [r['confidence'] for r in successful_results]
        avg_confidence = sum(confidences) / len(confidences)
        max_confidence = max(confidences)
        min_confidence = min(confidences)

        print("=== 置信度分析 ===")
        print(f"平均置信度: {avg_confidence:.3f}")
        print(f"置信度范围: {min_confidence:.3f} - {max_confidence:.3f}")

        # 按置信度分层
        high_conf = sum(1 for c in confidences if c >= 0.75)
        medium_conf = sum(1 for c in confidences if 0.65 <= c < 0.75)
        low_conf = sum(1 for c in confidences if c < 0.65)

        print(f"高置信度 (≥0.75): {high_conf} 个")
        print(f"中置信度 (0.65-0.74): {medium_conf} 个")
        print(f"低置信度 (<0.65): {low_conf} 个")

    print()

    # 验证核心功能
    print("=== 核心功能验证 ===")

    # 测试具体要求
    core_tests = [
        ('张John', {'expected_surname': '张', 'expected_given': 'John'}),
        ('David张', {'expected_surname': '张', 'expected_given': 'David'}),
        ('欧阳Peter', {'expected_surname': '欧阳', 'expected_given': 'Peter'}),
        ('Anna司马', {'expected_surname': '司马', 'expected_given': 'Anna'}),
    ]

    core_success = 0
    for test_name, expected in core_tests:
        result = processor.process_name(test_name)
        if (result and result.is_successful() and
            result.components.surname == expected['expected_surname'] and
            result.components.first_name == expected['expected_given']):
            core_success += 1
            print(f"[✓] {test_name}: 正确识别为 {result.components.surname} | {result.components.first_name}")
        else:
            print(f"[✗] {test_name}: 识别失败或结果不符合预期")

    core_success_rate = (core_success / len(core_tests)) * 100

    print()
    print("=== 测试总结 ===")
    print(f"整体成功率: {success_rate:.1f}%")
    print(f"核心功能验证: {core_success_rate:.1f}%")

    if success_rate >= 80 and core_success_rate >= 75:
        print("✓ 混合文字处理功能实现良好!")
        print("✓ Mixed script processing functionality implemented well!")
    elif success_rate >= 60:
        print("⚠ 混合文字处理功能基本可用，但需要进一步优化")
        print("⚠ Mixed script processing is functional but needs optimization")
    else:
        print("✗ 混合文字处理功能需要重大改进")
        print("✗ Mixed script processing needs major improvements")

if __name__ == "__main__":
    test_mixed_script_names()