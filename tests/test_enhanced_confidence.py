# -*- coding: utf-8 -*-
"""
增强置信度系统测试 / Enhanced Confidence System Test

测试新的精细化置信度评分系统和决策路径生成逻辑
Test new refined confidence scoring system and decision path generation logic
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import create_default_processor

def test_enhanced_confidence_system():
    """测试增强的置信度系统"""
    print("=== Enhanced Confidence System Test ===")
    print("=== 增强置信度系统测试 ===")
    print()

    processor = create_default_processor()

    # 分类测试案例
    test_categories = {
        "完整姓名匹配 (Perfect Match)": [
            ('欧阳修', '应该达到0.98置信度'),
            ('司马光', '应该达到0.98置信度'),
            ('李明', '应该达到0.98置信度'),
            ('马嘉星', '作者姓名，应该达到0.98置信度'),
        ],

        "复合姓氏 (Compound Surnames)": [
            ('欧阳锋', '复合姓氏，高置信度'),
            ('司马懿', '复合姓氏，高置信度'),
            ('诸葛青', '复合姓氏，高置信度'),
        ],

        "常见单字姓氏 (Common Single Surnames)": [
            ('王五', '常见姓氏，中高置信度'),
            ('李四', '常见姓氏，中高置信度'),
            ('张三', '常见姓氏，中高置信度'),
        ],

        "Trie匹配测试 (Trie Matching)": [
            ('赵六', 'Trie搜索匹配'),
            ('刘七', 'Trie搜索匹配'),
            ('陈八', 'Trie搜索匹配'),
        ],

        "音译姓名 (Transliterated Names)": [
            ('Li Ming', '拼音系统'),
            ('Wang Xiaohong', '拼音系统'),
            ('Ma Jiaxing', '拼音系统'),
        ],

        "后备策略 (Fallback Strategy)": [
            ('单字', '未知姓氏，后备策略'),
            ('测试名', '未知姓氏，后备策略'),
            ('实验者', '未知姓氏，后备策略'),
        ],
    }

    all_results = []

    for category, test_cases in test_categories.items():
        print(f"=== {category} ===")
        print()

        category_results = []

        for name, expected_desc in test_cases:
            print(f"测试: '{name}' ({expected_desc})")

            try:
                result = processor.process_name(name)

                print(f"  姓氏: '{result.components.surname}'")
                print(f"  名字: '{result.components.first_name}'")
                print(f"  置信度: {result.confidence_score:.3f}")
                print(f"  数据源: {result.components.source_type}")

                # 决策路径
                if result.decision_path:
                    print("  决策路径:")
                    for i, step in enumerate(result.decision_path, 1):
                        print(f"    {i}. {step}")

                # 详细决策说明
                if hasattr(result.components, 'decision_reason') and result.components.decision_reason:
                    print(f"  决策说明: {result.components.decision_reason}")

                # 成功状态
                success_status = "成功" if result.is_successful() else "失败"
                print(f"  处理状态: {success_status}")

                category_results.append({
                    'name': name,
                    'confidence': result.confidence_score,
                    'success': result.is_successful(),
                    'category': category
                })

            except Exception as e:
                print(f"  错误: {e}")
                category_results.append({
                    'name': name,
                    'confidence': 0.0,
                    'success': False,
                    'category': category,
                    'error': str(e)
                })

            print()

        all_results.extend(category_results)
        print("-" * 60)
        print()

    # 统计分析
    print("=== 置信度评分系统分析 / Confidence Scoring Analysis ===")

    # 按类别分析
    for category in test_categories.keys():
        category_data = [r for r in all_results if r['category'] == category]
        if category_data:
            confidences = [r['confidence'] for r in category_data if 'error' not in r]
            success_rate = sum(1 for r in category_data if r['success']) / len(category_data)

            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                max_confidence = max(confidences)
                min_confidence = min(confidences)

                print(f"{category}:")
                print(f"  平均置信度: {avg_confidence:.3f}")
                print(f"  置信度范围: {min_confidence:.3f} - {max_confidence:.3f}")
                print(f"  成功率: {success_rate*100:.1f}%")
                print()

    # 验证置信度分层
    print("=== 置信度分层验证 ===")
    perfect_matches = [r for r in all_results if r['confidence'] >= 0.95]
    high_confidence = [r for r in all_results if 0.85 <= r['confidence'] < 0.95]
    medium_confidence = [r for r in all_results if 0.70 <= r['confidence'] < 0.85]
    low_confidence = [r for r in all_results if r['confidence'] < 0.70]

    print(f"完美匹配 (≥0.95): {len(perfect_matches)} 个")
    print(f"高置信度 (0.85-0.94): {len(high_confidence)} 个")
    print(f"中等置信度 (0.70-0.84): {len(medium_confidence)} 个")
    print(f"低置信度 (<0.70): {len(low_confidence)} 个")

    # 验证预期结果
    print("\n=== 预期结果验证 ===")

    expected_perfect = ['欧阳修', '司马光', '李明', '马嘉星']
    actual_perfect = [r['name'] for r in perfect_matches]

    print("预期完美匹配:", expected_perfect)
    print("实际完美匹配:", actual_perfect)

    match_rate = len(set(expected_perfect) & set(actual_perfect)) / len(expected_perfect)
    print(f"预期匹配率: {match_rate*100:.1f}%")

    print("\n=== 系统验证总结 ===")
    total_success = sum(1 for r in all_results if r['success'])
    overall_success_rate = total_success / len(all_results)

    print(f"总体成功率: {overall_success_rate*100:.1f}%")
    print(f"置信度评分系统: {'正常工作' if match_rate >= 0.8 else '需要调整'}")
    print(f"决策路径生成: {'已实现' if any('decision_path' in str(r) for r in all_results) else '未实现'}")

    if overall_success_rate >= 0.9 and match_rate >= 0.8:
        print("\n[成功] 增强置信度系统工作正常!")
        print("[SUCCESS] Enhanced confidence system working properly!")
    else:
        print("\n[警告] 增强置信度系统需要进一步优化")
        print("[WARNING] Enhanced confidence system needs further optimization")

if __name__ == "__main__":
    test_enhanced_confidence_system()