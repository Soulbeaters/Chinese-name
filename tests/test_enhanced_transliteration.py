# -*- coding: utf-8 -*-
"""
增强音译数据库测试 / Enhanced Transliteration Database Test

测试增强的音译数据库，特别关注"Van Syaokhun"解析和变体支持
Test enhanced transliteration database, focusing on "Van Syaokhun" parsing and variant support
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transliteration_db import ExtendedTransliterationDatabase

def test_enhanced_transliteration():
    """测试增强的音译功能"""
    print("=== Enhanced Transliteration Database Test ===")
    print("=== 增强音译数据库测试 ===")
    print()

    db = ExtendedTransliterationDatabase()

    # 特别关注的测试案例 / Special focus test cases
    critical_test_cases = [
        # Van Syaokhun 解析测试 / Van Syaokhun parsing test
        (["Van", "Syaokhun"], "关键测试：Van应该被识别为王的变体，Syaokhun应该被识别为小红"),
        (["van", "syaokhun"], "小写测试"),
        (["VAN", "SYAOKHUN"], "大写测试"),

        # 连字符支持测试 / Hyphen support test
        (["Jia-xing"], "连字符复合名字测试"),
        (["Ma-Jia", "Xing"], "连字符姓名测试"),
        (["Van-Wang", "Syao-khun"], "连字符变体测试"),

        # 变体支持测试 / Variant support test
        (["Wong", "Ming"], "Wang变体测试"),
        (["Lee", "Xiaohong"], "Li变体测试"),
        (["Chang", "Wei"], "Zhang变体测试"),
        (["Cheung", "Ping"], "Zhang变体测试"),
    ]

    # 标准测试案例 / Standard test cases
    standard_test_cases = [
        (["Li", "Ming"], "标准拼音"),
        (["Ma", "Jiaxing"], "作者姓名"),
        (["Wang", "Xiaohong"], "常见姓名"),
        (["Zhang", "Wei"], "普通姓名"),
        (["Ming", "Li"], "西方顺序"),
    ]

    print("=== 关键功能测试 / Critical Function Tests ===")
    critical_results = []

    for name_parts, description in critical_test_cases:
        print(f"测试 / Test: {' '.join(name_parts)} ({description})")

        try:
            result = db.identify_transliterated_name(name_parts)

            if result:
                surname, given_name, middle_name, confidence, source_type = result
                print(f"  姓氏 / Surname: '{surname}'")
                print(f"  名字 / Given Name: '{given_name}'")
                if middle_name:
                    print(f"  中间名 / Middle Name: '{middle_name}'")
                print(f"  置信度 / Confidence: {confidence:.3f}")
                print(f"  数据源类型 / Source Type: {source_type}")
                print(f"  识别状态 / Status: 成功 / Success")

                critical_results.append({
                    'input': name_parts,
                    'description': description,
                    'surname': surname,
                    'given_name': given_name,
                    'confidence': confidence,
                    'success': True
                })
            else:
                print(f"  识别状态 / Status: 失败 / Failed")
                critical_results.append({
                    'input': name_parts,
                    'description': description,
                    'success': False
                })

        except Exception as e:
            print(f"  错误 / Error: {e}")
            critical_results.append({
                'input': name_parts,
                'description': description,
                'success': False,
                'error': str(e)
            })

        print()

    print("=== 标准功能测试 / Standard Function Tests ===")
    standard_results = []

    for name_parts, description in standard_test_cases:
        print(f"测试 / Test: {' '.join(name_parts)} ({description})")

        try:
            result = db.identify_transliterated_name(name_parts)

            if result:
                surname, given_name, middle_name, confidence, source_type = result
                print(f"  结果 / Result: {surname} | {given_name}")
                print(f"  置信度 / Confidence: {confidence:.3f}")
                print(f"  类型 / Type: {source_type}")

                standard_results.append({
                    'input': name_parts,
                    'confidence': confidence,
                    'success': True
                })
            else:
                print(f"  状态 / Status: 无法识别 / Not recognized")
                standard_results.append({
                    'input': name_parts,
                    'success': False
                })

        except Exception as e:
            print(f"  错误 / Error: {e}")
            standard_results.append({
                'input': name_parts,
                'success': False,
                'error': str(e)
            })

        print()

    # 结果分析 / Results analysis
    print("=== 测试结果分析 / Test Results Analysis ===")

    # 关键功能分析 / Critical function analysis
    critical_success = sum(1 for r in critical_results if r['success'])
    critical_total = len(critical_results)
    critical_rate = (critical_success / critical_total) * 100

    print(f"关键功能测试 / Critical Function Tests:")
    print(f"  成功 / Success: {critical_success}/{critical_total}")
    print(f"  成功率 / Success Rate: {critical_rate:.1f}%")

    # 标准功能分析 / Standard function analysis
    standard_success = sum(1 for r in standard_results if r['success'])
    standard_total = len(standard_results)
    standard_rate = (standard_success / standard_total) * 100

    print(f"标准功能测试 / Standard Function Tests:")
    print(f"  成功 / Success: {standard_success}/{standard_total}")
    print(f"  成功率 / Success Rate: {standard_rate:.1f}%")

    # Van Syaokhun 特定验证 / Van Syaokhun specific validation
    print()
    print("=== Van Syaokhun 解析验证 / Van Syaokhun Parsing Validation ===")

    van_tests = [r for r in critical_results if 'Van' in str(r['input']) or 'van' in str(r['input'])]
    van_success = 0

    for test in van_tests:
        test_input = ' '.join(test['input'])
        if test['success']:
            # 验证是否正确识别为王姓和相关名字
            surname = test['surname']
            if '王' in surname or 'Wang' in surname or 'Van' in surname:
                van_success += 1
                print(f"[✓] {test_input}: 正确识别姓氏 '{surname}'")
            else:
                print(f"[✗] {test_input}: 姓氏识别不正确 '{surname}'")
        else:
            print(f"[✗] {test_input}: 识别失败")

    van_rate = (van_success / len(van_tests)) * 100 if van_tests else 0
    print(f"Van 解析成功率 / Van Parsing Success Rate: {van_rate:.1f}%")

    # 数据库统计 / Database statistics
    print()
    print("=== 数据库统计 / Database Statistics ===")
    stats = db.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 总体评估 / Overall assessment
    print()
    print("=== 总体评估 / Overall Assessment ===")

    overall_success_rate = (critical_success + standard_success) / (critical_total + standard_total) * 100

    print(f"整体成功率 / Overall Success Rate: {overall_success_rate:.1f}%")
    print(f"Van Syaokhun 解析: {'通过' if van_rate >= 60 else '需要改进'}")
    print(f"连字符支持: {'实现' if critical_rate >= 70 else '需要优化'}")
    print(f"变体支持: {'良好' if standard_rate >= 80 else '需要扩展'}")

    if overall_success_rate >= 80 and van_rate >= 60:
        print()
        print("[成功] 增强音译数据库功能实现良好!")
        print("[SUCCESS] Enhanced transliteration database functionality implemented well!")
    else:
        print()
        print("[需要改进] 部分功能需要进一步优化")
        print("[NEEDS IMPROVEMENT] Some functionality needs further optimization")

if __name__ == "__main__":
    test_enhanced_transliteration()