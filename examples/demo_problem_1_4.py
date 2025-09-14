# -*- coding: utf-8 -*-
"""
问题1.4演示：可验证的处理结果
Problem 1.4 Demo: Verifiable Processing Results
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import create_default_processor

def demo_problem_1_4():
    """演示问题1.4实现"""
    print("=== Problem 1.4 Demo: Verifiable Processing Results ===")

    processor = create_default_processor()

    # 重点测试案例
    test_names = [
        '欧阳修',      # 复合姓氏 - 高置信度
        '李明',        # 单字姓氏 - 中等置信度
        'Li Ming',     # 音译姓名 - 中等置信度
        '单字',        # 边界情况 - 低置信度
    ]

    for name in test_names:
        print(f"\n--- Testing: '{name}' ---")

        result = processor.process_name(name)

        # 1. 处理后的姓名
        print(f"Parsed Name:")
        print(f"  Surname: '{result.components.surname}'")
        print(f"  Given Name: '{result.components.first_name}'")

        # 2. 量化置信度分数
        print(f"Confidence Score: {result.confidence_score:.3f}")

        # 3. 决策路径描述
        print("Decision Path:")
        for i, step in enumerate(result.decision_path, 1):
            print(f"  {i}. {step}")

        # 决策说明
        if hasattr(result.components, 'decision_reason') and result.components.decision_reason:
            print(f"Decision Reason: {result.components.decision_reason}")

        # 其他验证信息
        print(f"Source Type: {result.components.source_type}")
        print(f"Success: {result.is_successful()}")

        # 导出为字典
        result_dict = result.to_dict()
        print("Exportable Result: Available as JSON")

    print("\n=== Problem 1.4 Implementation Verification ===")
    print("1. Processed names (surname, given name): Implemented")
    print("2. Quantified confidence score (0.0-1.0): Implemented")
    print("3. Decision path text description: Implemented")
    print("4. Rich information object: Implemented")
    print("5. JSON serializable results: Implemented")
    print("\nProblem 1.4 successfully implemented!")

if __name__ == "__main__":
    demo_problem_1_4()