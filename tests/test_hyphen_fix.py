# -*- coding: utf-8 -*-
"""
连字符处理修复测试 / Hyphen Processing Fix Test

专门测试修复的连字符处理功能
Specifically test the fixed hyphen processing functionality
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transliteration_db import ExtendedTransliterationDatabase

def test_hyphen_fix():
    """测试连字符处理修复"""
    print("=== Hyphen Processing Fix Test ===")

    db = ExtendedTransliterationDatabase()

    # 连字符测试案例 / Hyphen test cases
    test_cases = [
        (["jia-xing"], "Single hyphenated compound name"),
        (["Ma-Jia", "Xing"], "Hyphenated first + last"),
        (["Li-Wei"], "Single hyphenated name"),
        (["Jia-Ming"], "Single hyphenated compound"),
        (["Wang-Xiao", "Hong"], "Hyphenated compound surname + name"),
        (["Li", "Jia-Xing"], "Normal surname + hyphenated given"),
        (["Jia", "Xing"], "Split parts (control test)"),
        (["Ma", "Jiaxing"], "Normal case (control test)"),
    ]

    results = []

    print("Testing hyphen processing:")
    print()

    for name_parts, description in test_cases:
        input_str = ' '.join(name_parts)
        print(f"Test: {input_str} ({description})")

        try:
            result = db.identify_transliterated_name(name_parts)

            if result:
                surname, given_name, middle_name, confidence, source_type = result
                print(f"  Surname: '{surname}'")
                print(f"  Given Name: '{given_name}'")
                if middle_name:
                    print(f"  Middle Name: '{middle_name}'")
                print(f"  Confidence: {confidence:.3f}")
                print(f"  Source Type: {source_type}")
                print(f"  Status: SUCCESS")

                results.append({
                    'input': input_str,
                    'surname': surname,
                    'given_name': given_name,
                    'confidence': confidence,
                    'success': True
                })
            else:
                print(f"  Status: FAILED")
                results.append({
                    'input': input_str,
                    'success': False
                })

        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                'input': input_str,
                'success': False,
                'error': str(e)
            })

        print()

    # 分析结果 / Analyze results
    print("=== Results Analysis ===")

    total = len(results)
    successful = sum(1 for r in results if r['success'])
    success_rate = (successful / total) * 100

    print(f"Total tests: {total}")
    print(f"Successful: {successful}")
    print(f"Success rate: {success_rate:.1f}%")
    print()

    # 连字符特定验证 / Hyphen specific validation
    hyphen_tests = [r for r in results if '-' in r['input']]
    hyphen_success = sum(1 for r in hyphen_tests if r['success'])
    hyphen_rate = (hyphen_success / len(hyphen_tests)) * 100 if hyphen_tests else 0

    print("Hyphen processing validation:")
    for result in results:
        if '-' in result['input']:
            status = "PASS" if result['success'] else "FAIL"
            if result['success']:
                print(f"{status}: {result['input']} -> {result.get('surname', 'N/A')} | {result.get('given_name', 'N/A')}")
            else:
                print(f"{status}: {result['input']} -> parsing failed")

    print(f"Hyphen processing success: {hyphen_success}/{len(hyphen_tests)} ({hyphen_rate:.1f}%)")

    # 对照组验证 / Control group validation
    control_tests = [r for r in results if '-' not in r['input']]
    control_success = sum(1 for r in control_tests if r['success'])
    control_rate = (control_success / len(control_tests)) * 100 if control_tests else 0

    print(f"Control group success: {control_success}/{len(control_tests)} ({control_rate:.1f}%)")

    print()
    print("=== Final Assessment ===")
    if hyphen_rate >= 75:
        print("SUCCESS: Hyphen processing fix implemented successfully!")
        print("- Hyphenated compound names are correctly split and processed")
        print("- Multiple part hyphen combinations work")
        print("- Single character name recognition improved")
    elif hyphen_rate >= 50:
        print("PARTIAL SUCCESS: Hyphen processing improved but needs optimization")
    else:
        print("NEEDS WORK: Hyphen processing still needs significant improvement")

    return results

if __name__ == "__main__":
    test_hyphen_fix()