# -*- coding: utf-8 -*-
"""
对比两种Ground Truth推断方法
Compare two ground truth inference methods
"""

import json
from collections import Counter

def method_run_bench(lastname, firstname, original_name):
    """run_bench.py的方法"""
    if original_name.strip().startswith(lastname):
        return "family_first"
    else:
        return "given_first"

def method_evidence_chain(lastname, firstname, original_name):
    """run_bench_with_evidence.py的方法"""
    original_name_lower = original_name.lower()
    lastname_pos = original_name_lower.find(lastname.lower())
    firstname_pos = original_name_lower.find(firstname.lower())

    if lastname_pos >= 0 and firstname_pos >= 0:
        if lastname_pos < firstname_pos:
            return 'family_first'
        else:
            return 'given_first'
    else:
        return None  # 未找到

def main():
    # 加载数据
    with open('C:/program 1 in 2025/test_data/crossref_10k.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 对比两种方法
    method1_results = {}
    method2_results = {}
    differences = []
    method2_none_count = 0

    for i, item in enumerate(data):
        if 'lastname' not in item or 'firstname' not in item:
            continue

        lastname = item['lastname']
        firstname = item['firstname']
        original_name = item.get('original_name', '')

        if not original_name:
            continue

        # 方法1
        gt1 = method_run_bench(lastname, firstname, original_name)
        method1_results[str(i)] = gt1

        # 方法2
        gt2 = method_evidence_chain(lastname, firstname, original_name)
        if gt2 is not None:
            method2_results[str(i)] = gt2
        else:
            method2_none_count += 1

        # 记录差异
        if gt2 is not None and gt1 != gt2:
            differences.append({
                'index': i,
                'original_name': original_name,
                'lastname': lastname,
                'firstname': firstname,
                'method1_run_bench': gt1,
                'method2_evidence_chain': gt2
            })

    # 统计
    print(f"Total records with lastname/firstname: {len(method1_results)}")
    print(f"\nMethod 1 (run_bench.py):")
    print(f"  Total ground truth: {len(method1_results)}")
    counter1 = Counter(method1_results.values())
    print(f"  family_first: {counter1['family_first']}")
    print(f"  given_first: {counter1['given_first']}")

    print(f"\nMethod 2 (run_bench_with_evidence.py):")
    print(f"  Total ground truth: {len(method2_results)}")
    print(f"  Records with no match (None): {method2_none_count}")
    counter2 = Counter(method2_results.values())
    print(f"  family_first: {counter2['family_first']}")
    print(f"  given_first: {counter2['given_first']}")

    print(f"\nDifferences between methods: {len(differences)}")
    if differences:
        print("\nFirst 10 differences:")
        for diff in differences[:10]:
            print(f"  [{diff['index']}] {diff['original_name']}")
            print(f"    lastname: {diff['lastname']}, firstname: {diff['firstname']}")
            print(f"    Method1: {diff['method1_run_bench']}, Method2: {diff['method2_evidence_chain']}")

    # 关键差异：方法2中被排除的记录
    if method2_none_count > 0:
        print(f"\n⚠️ CRITICAL: Method 2 excludes {method2_none_count} records!")
        print("This could explain the accuracy difference!")

        # 找几个被排除的例子
        print("\nExamples of excluded records:")
        count = 0
        for i, item in enumerate(data):
            if str(i) not in method2_results and str(i) in method1_results:
                print(f"  [{i}] {item.get('original_name', '')}")
                print(f"    lastname: {item.get('lastname', '')}")
                print(f"    firstname: {item.get('firstname', '')}")
                count += 1
                if count >= 5:
                    break

if __name__ == '__main__':
    main()
