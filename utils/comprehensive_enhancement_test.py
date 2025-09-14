# -*- coding: utf-8 -*-
"""
综合增强功能测试 / Comprehensive Enhancement Test

测试所有transliteration_db.py增强功能的综合测试
Comprehensive test for all transliteration_db.py enhancements
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transliteration_db import ExtendedTransliterationDatabase

def test_comprehensive_enhancements():
    """综合测试所有增强功能"""
    print("=== Comprehensive Transliteration Database Enhancement Test ===")
    print()

    db = ExtendedTransliterationDatabase()

    # 测试分类 / Test categories
    test_categories = {
        "Van Syaokhun Fix": [
            (["Van", "Syaokhun"], "Original problematic case"),
            (["van", "syaokhun"], "Lowercase version"),
            (["VAN", "SYAOKHUN"], "Uppercase version"),
        ],

        "Case Insensitive": [
            (["li", "ming"], "All lowercase"),
            (["LI", "MING"], "All uppercase"),
            (["Li", "MING"], "Mixed case"),
            (["wang", "XIAOHONG"], "Mixed case surname"),
        ],

        "Hyphen Support": [
            (["jia-xing"], "Single hyphenated compound"),
            (["Ma-Jia", "Xing"], "Hyphenated first + last"),
            (["Li-Wei"], "Single hyphenated name"),
        ],

        "Variant Support": [
            (["Wong", "Ming"], "Wong -> Wang"),
            (["Lee", "Xiaohong"], "Lee -> Li"),
            (["Chang", "Wei"], "Chang -> Zhang"),
            (["Cheung", "Ping"], "Cheung -> Zhang"),
            (["Lau", "David"], "Lau -> Liu"),
        ],

        "Russian Transliteration": [
            (["Ван", "Сяохун"], "Russian Van Syaokhun"),
            (["Ма", "Цзясин"], "Russian Ma Jiaxing"),
            (["Ли", "Мин"], "Russian Li Ming"),
        ],

        "Standard Cases": [
            (["Li", "Ming"], "Standard pinyin"),
            (["Ma", "Jiaxing"], "Author name"),
            (["Wang", "Xiaohong"], "Common name"),
            (["Ming", "Li"], "Western order"),
        ],
    }

    all_results = []
    category_stats = {}

    for category, test_cases in test_categories.items():
        print(f"=== {category} ===")
        category_results = []

        for name_parts, description in test_cases:
            input_str = ' '.join(name_parts)
            print(f"Test: {input_str} ({description})")

            try:
                result = db.identify_transliterated_name(name_parts)

                if result:
                    surname, given_name, middle_name, confidence, source_type = result
                    print(f"  Result: {surname} | {given_name}")
                    print(f"  Confidence: {confidence:.3f}")
                    print(f"  Type: {source_type}")
                    print(f"  Status: SUCCESS")

                    category_results.append({
                        'input': input_str,
                        'category': category,
                        'success': True,
                        'confidence': confidence,
                        'surname': surname,
                        'given_name': given_name
                    })
                else:
                    print(f"  Status: FAILED")
                    category_results.append({
                        'input': input_str,
                        'category': category,
                        'success': False
                    })

            except Exception as e:
                print(f"  Error: {e}")
                category_results.append({
                    'input': input_str,
                    'category': category,
                    'success': False,
                    'error': str(e)
                })

            print()

        # 计算类别统计
        successful = sum(1 for r in category_results if r['success'])
        total = len(category_results)
        success_rate = (successful / total) * 100

        category_stats[category] = {
            'successful': successful,
            'total': total,
            'rate': success_rate
        }

        print(f"Category Result: {successful}/{total} ({success_rate:.1f}%)")
        print("-" * 50)
        print()

        all_results.extend(category_results)

    # 总体统计分析
    print("=== Overall Statistics ===")
    total_tests = len(all_results)
    total_successful = sum(1 for r in all_results if r['success'])
    overall_success_rate = (total_successful / total_tests) * 100

    print(f"Total tests: {total_tests}")
    print(f"Total successful: {total_successful}")
    print(f"Overall success rate: {overall_success_rate:.1f}%")
    print()

    # 按类别显示结果
    print("=== Category Breakdown ===")
    for category, stats in category_stats.items():
        status = "PASS" if stats['rate'] >= 75 else "NEEDS WORK"
        print(f"{category}: {stats['successful']}/{stats['total']} ({stats['rate']:.1f}%) - {status}")

    # 置信度分析
    successful_results = [r for r in all_results if r['success'] and 'confidence' in r]
    if successful_results:
        confidences = [r['confidence'] for r in successful_results]
        avg_confidence = sum(confidences) / len(confidences)
        max_confidence = max(confidences)
        min_confidence = min(confidences)

        print()
        print("=== Confidence Analysis ===")
        print(f"Average confidence: {avg_confidence:.3f}")
        print(f"Confidence range: {min_confidence:.3f} - {max_confidence:.3f}")

        # 置信度分层
        high_conf = sum(1 for c in confidences if c >= 0.9)
        medium_conf = sum(1 for c in confidences if 0.7 <= c < 0.9)
        low_conf = sum(1 for c in confidences if c < 0.7)

        print(f"High confidence (>=0.9): {high_conf}")
        print(f"Medium confidence (0.7-0.89): {medium_conf}")
        print(f"Low confidence (<0.7): {low_conf}")

    # 数据库统计
    print()
    print("=== Database Statistics ===")
    stats = db.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 最终评估
    print()
    print("=== Final Enhancement Assessment ===")

    # 检查关键功能
    van_category = category_stats.get("Van Syaokhun Fix", {})
    case_category = category_stats.get("Case Insensitive", {})
    variant_category = category_stats.get("Variant Support", {})
    russian_category = category_stats.get("Russian Transliteration", {})

    checks = [
        ("Van Syaokhun Fix", van_category.get('rate', 0) >= 80),
        ("Case Insensitive Processing", case_category.get('rate', 0) >= 80),
        ("Variant Support", variant_category.get('rate', 0) >= 80),
        ("Russian Transliteration", russian_category.get('rate', 0) >= 60),
        ("Overall Success Rate", overall_success_rate >= 75),
    ]

    all_passed = True
    for check_name, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("SUCCESS: All transliteration database enhancements implemented successfully!")
        print("- Van Syaokhun parsing issue resolved")
        print("- Case-insensitive processing working")
        print("- Hyphen handling implemented")
        print("- Extensive variant support added")
        print("- Russian transliteration coverage enhanced")
    else:
        print("PARTIAL SUCCESS: Most enhancements working, some optimizations needed")

    return all_results, category_stats

if __name__ == "__main__":
    test_comprehensive_enhancements()