# -*- coding: utf-8 -*-
"""
简化版音译姓名测试 / Simplified transliterated name test
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import create_default_processor

def test_transliterated_names():
    """测试音译姓名处理 / Test transliterated name processing"""
    print("音译姓名处理测试 / Transliterated Name Processing Test")
    print("=" * 60)

    processor = create_default_processor()

    # 测试案例 / Test cases
    test_cases = [
        # 原始中文 / Original Chinese
        ('马嘉星', 'Chinese'),
        ('李明', 'Chinese'),
        ('王小红', 'Chinese'),

        # 拼音 / Pinyin
        ('Ma Jiaxing', 'Pinyin'),
        ('Li Ming', 'Pinyin'),
        ('Wang Xiaohong', 'Pinyin'),

        # 帕拉第系统 / Palladius system
        ('Ma Tszyasin', 'Palladius'),
        ('Li Min', 'Palladius'),
        ('Van Syaokhun', 'Palladius'),

        # 变体 / Variants
        ('Ma Jia-xing', 'Pinyin variant'),
        ('Li, Ming', 'Comma format'),
        ('WANG Xiaohong', 'Mixed case'),
    ]

    print(f"{'姓名 / Name':<15} {'类型 / Type':<15} {'识别结果 / Result':<20} {'置信度 / Conf'}")
    print("-" * 70)

    success_count = 0
    total_count = len(test_cases)

    for name, name_type in test_cases:
        try:
            result = processor.process_name(name)

            if result.is_successful():
                surname = result.components.surname or "未知"
                given_name = result.components.first_name or "未知"
                confidence = result.confidence_score

                result_str = f"{surname}|{given_name}"
                status = "成功" if confidence > 0.3 else "低置信"

                if confidence > 0.3:
                    success_count += 1

            else:
                result_str = "识别失败 / Failed"
                confidence = 0.0
                status = "失败"

            print(f"{name:<15} {name_type:<15} {result_str:<20} {confidence:.2f}")

        except Exception as e:
            print(f"{name:<15} {name_type:<15} 错误: {str(e):<12} 0.00")

    print("-" * 70)
    print(f"成功率 / Success Rate: {success_count}/{total_count} ({100*success_count/total_count:.1f}%)")

    # 重点测试Li Ming问题 / Focus on Li Ming issue
    print(f"\n重点测试Li Ming / Li Ming Focus Test:")
    test_li_ming = processor.process_name("Li Ming")

    if test_li_ming.is_successful():
        print("Li Ming 识别成功 / Li Ming recognized successfully")
        print(f"姓氏 / Surname: {test_li_ming.components.surname}")
        print(f"名字 / Given name: {test_li_ming.components.first_name}")
        print(f"置信度 / Confidence: {test_li_ming.confidence_score:.2f}")
        print(f"决策路径 / Decision path: {test_li_ming.decision_path}")
    else:
        print("Li Ming 识别失败 / Li Ming recognition failed")
        print(f"错误信息 / Error: {test_li_ming.error_message}")


if __name__ == "__main__":
    test_transliterated_names()