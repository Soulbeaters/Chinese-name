# -*- coding: utf-8 -*-
"""
全面人工验证 v5.0
Comprehensive Manual Validation v5.0

验证内容 / Validation Contents / Содержание валидации:
1. 随机抽样检查被排除的作者（是否有中文作者被误排除）
2. 随机抽样检查筛选出的中文作者（是否有非中文作者混入）
3. 测试姓氏识别算法在v5筛选结果上的准确率
4. 生成详细验证报告

中文注释：全面人工验证，确保算法质量
Русский комментарий：Комплексная проверка качества алгоритма
"""

import json
import random
import argparse
from collections import Counter
from final_filter_v5_enhanced import filter_chinese_author_v5
from src.surname_identifier import identify_surname_position
from data.surname_pinyin_db import is_surname_pinyin
from data.variant_pinyin_map import get_all_possible_pinyins
from data.traditional_chinese_surnames import is_traditional_chinese_surname
from src.localization import get_localizer

# 命令行参数解析
def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='v5.0 Comprehensive Manual Validation\n'
                    'Комплексная валидация v5.0',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--data-path',
        type=str,
        default=r"C:\istina\materia 材料\测试表单\crossref_authors.json",
        help='Path to crossref_authors.json / Путь к файлу'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=r"C:\program 1 in 2025\comprehensive_validation_v5_results.json",
        help='Output file path / Путь к выходному файлу'
    )

    parser.add_argument(
        '--language',
        type=str,
        choices=['zh', 'ru', 'en'],
        default='ru',
        help='Output language (default: ru) / Язык вывода'
    )

    return parser.parse_args()

# 解析参数
args = parse_arguments()
localizer = get_localizer(args.language)

print("=" * 80)
print(f"v5.0 {localizer.get_text('validation')}")
print("=" * 80)

# 加载完整数据集
print(f"\n{localizer.get_text('loading_data')}...")
with open(args.data_path, 'r', encoding='utf-8') as f:
    all_authors = json.load(f)

print(f"{localizer.get_text('total_authors')}: {len(all_authors):,}")

# ========== 步骤1: 运行v5筛选 ==========
print("\n" + "=" * 80)
print("步骤1: 运行v5.0筛选算法")
print("=" * 80)

print("\n正在筛选...")
chinese_authors = []
non_chinese_authors = []

for i, author in enumerate(all_authors):
    if i > 0 and i % 50000 == 0:
        print(f"  进度: {i:,}/{len(all_authors):,}...", flush=True)

    is_chinese, conf, reason = filter_chinese_author_v5(
        author.get('original_name', ''),
        author.get('affiliation', '')
    )

    author_with_info = author.copy()
    author_with_info['filter_reason'] = reason
    author_with_info['filter_confidence'] = conf

    if is_chinese is True:
        chinese_authors.append(author_with_info)
    else:
        non_chinese_authors.append(author_with_info)

print(f"\n筛选结果:")
print(f"  中文作者: {len(chinese_authors):,} ({len(chinese_authors)*100/len(all_authors):.2f}%)")
print(f"  非中文作者: {len(non_chinese_authors):,} ({len(non_chinese_authors)*100/len(all_authors):.2f}%)")

# ========== 步骤2: 检查被排除的作者（是否误排除中文作者）==========
print("\n" + "=" * 80)
print("步骤2: 检查被排除的作者中是否有中文作者被误排除")
print("=" * 80)

print(f"\n从 {len(non_chinese_authors):,} 个被排除的作者中随机抽样 5,000 个...")
sample_excluded = random.sample(non_chinese_authors, min(5000, len(non_chinese_authors)))

wrongly_excluded = []

for author in sample_excluded:
    lastname = author.get('lastname', '').strip().lower()
    if not lastname:
        continue

    # 检查lastname是否为中文姓氏（简体+繁体）
    is_chinese_surname = False

    # 1. 检查繁体中文姓氏
    if is_traditional_chinese_surname(lastname):
        is_chinese_surname = True

    # 2. 检查简体中文姓氏
    if not is_chinese_surname:
        all_forms = get_all_possible_pinyins(lastname)
        if any(is_surname_pinyin(form) for form in all_forms):
            is_chinese_surname = True

    if is_chinese_surname:
        wrongly_excluded.append({
            'name': author.get('original_name', ''),
            'lastname': author.get('lastname', ''),
            'firstname': author.get('firstname', ''),
            'filter_reason': author.get('filter_reason', ''),
            'affiliation': (author.get('affiliation', '') or '')[:50]
        })

print(f"\n发现可能被误排除的中文作者: {len(wrongly_excluded)} 个 ({len(wrongly_excluded)*100/len(sample_excluded):.2f}%)")

if wrongly_excluded:
    print("\n分析前50个案例:")
    print("-" * 80)
    print(f"{'No.':<4} {'Name':<30} {'Lastname':<10} {'排除原因':<45}")
    print("-" * 80)

    # 统计排除原因
    exclusion_reasons = Counter()
    for case in wrongly_excluded:
        reason = case['filter_reason']
        if '外文专有名词' in reason:
            exclusion_reasons['外文专有名词'] += 1
        elif '外国姓氏' in reason:
            exclusion_reasons['外国姓氏'] += 1
        elif '无中文姓氏' in reason:
            exclusion_reasons['无中文姓氏'] += 1
        elif '复合名' in reason:
            exclusion_reasons['复合名含外文'] += 1
        else:
            exclusion_reasons['其他'] += 1

    for i, case in enumerate(wrongly_excluded[:50], 1):
        print(f"{i:<4} {case['name']:<30} {case['lastname']:<10} {case['filter_reason'][:45]}")

    print(f"\n排除原因统计:")
    for reason, count in exclusion_reasons.most_common():
        print(f"  {reason}: {count} ({count*100/len(wrongly_excluded):.1f}%)")

# ========== 步骤3: 检查筛选出的中文作者（是否混入非中文作者）==========
print("\n" + "=" * 80)
print("步骤3: 检查筛选出的中文作者中是否有非中文作者混入")
print("=" * 80)

print(f"\n从 {len(chinese_authors):,} 个中文作者中随机抽样 5,000 个...")
sample_chinese = random.sample(chinese_authors, min(5000, len(chinese_authors)))

false_positives = []

for author in sample_chinese:
    name = author.get('original_name', '')
    lastname = author.get('lastname', '').strip().lower()

    # 检查lastname是否确实是中文姓氏
    is_really_chinese = False

    # 1. 检查繁体中文姓氏
    if is_traditional_chinese_surname(lastname):
        is_really_chinese = True

    # 2. 检查简体中文姓氏
    if not is_really_chinese and lastname:
        all_forms = get_all_possible_pinyins(lastname)
        if any(is_surname_pinyin(form) for form in all_forms):
            is_really_chinese = True

    # 如果lastname不是中文姓氏，可能是误判
    if not is_really_chinese:
        false_positives.append({
            'name': name,
            'lastname': author.get('lastname', ''),
            'firstname': author.get('firstname', ''),
            'filter_reason': author.get('filter_reason', ''),
            'affiliation': (author.get('affiliation', '') or '')[:50]
        })

print(f"\n发现可能的误判（lastname不是中文姓氏）: {len(false_positives)} 个 ({len(false_positives)*100/len(sample_chinese):.2f}%)")

if false_positives:
    print("\n前50个案例:")
    print("-" * 80)
    print(f"{'No.':<4} {'Name':<30} {'Lastname':<12} {'筛选原因':<40}")
    print("-" * 80)

    for i, case in enumerate(false_positives[:50], 1):
        print(f"{i:<4} {case['name']:<30} {case['lastname']:<12} {case['filter_reason'][:40]}")

# ========== 步骤4: 姓氏识别算法验证 ==========
print("\n" + "=" * 80)
print("步骤4: 验证姓氏识别算法在v5筛选结果上的准确率")
print("=" * 80)

print(f"\n从 {len(chinese_authors):,} 个中文作者中随机抽样 10,000 个测试姓氏识别...")
surname_test_sample = random.sample(chinese_authors, min(10000, len(chinese_authors)))

correct_surname = 0
incorrect_surname = 0
undetermined_surname = 0
surname_errors = []

for author in surname_test_sample:
    original_name = author.get('original_name', '')
    crossref_lastname = author.get('lastname', '').strip()

    if not original_name or not crossref_lastname:
        undetermined_surname += 1
        continue

    # 使用姓氏识别算法
    position, conf, reason = identify_surname_position(
        original_name,
        author.get('affiliation', '')
    )

    parts = original_name.split()
    if len(parts) < 2:
        undetermined_surname += 1
        continue

    # 提取我们识别的姓氏
    if position == 'family_first':
        our_surname = parts[-1].strip()
    elif position == 'given_first':
        our_surname = parts[0].strip()
    else:
        undetermined_surname += 1
        continue

    # 对比
    if our_surname.lower() == crossref_lastname.lower():
        correct_surname += 1
    else:
        incorrect_surname += 1
        if len(surname_errors) < 100:
            surname_errors.append({
                'name': original_name,
                'our': our_surname,
                'crossref': crossref_lastname,
                'position': position,
                'conf': conf
            })

surname_total = correct_surname + incorrect_surname + undetermined_surname
surname_accuracy = correct_surname * 100 / surname_total if surname_total > 0 else 0

print(f"\n姓氏识别结果:")
print(f"  总测试: {surname_total:,}")
print(f"  正确: {correct_surname:,} ({correct_surname*100/surname_total:.2f}%)")
print(f"  错误: {incorrect_surname:,} ({incorrect_surname*100/surname_total:.2f}%)")
print(f"  无法判断: {undetermined_surname:,} ({undetermined_surname*100/surname_total:.2f}%)")
print(f"\n*** 姓氏识别准确率: {surname_accuracy:.2f}% ***")

if surname_errors:
    print("\n姓氏识别错误案例（前30个）:")
    print("-" * 80)
    print(f"{'No.':<4} {'Name':<30} {'Our':<10} {'Crossref':<10} {'Position':<15}")
    print("-" * 80)
    for i, case in enumerate(surname_errors[:30], 1):
        print(f"{i:<4} {case['name']:<30} {case['our']:<10} {case['crossref']:<10} {case['position']:<15}")

# ========== 最终报告 ==========
print("\n" + "=" * 80)
print("最终验证报告")
print("=" * 80)

report = f"""
## v5.0 全面验证结果

### 1. 初筛性能
- **总作者数**: {len(all_authors):,}
- **筛选出中文作者**: {len(chinese_authors):,} ({len(chinese_authors)*100/len(all_authors):.2f}%)
- **排除非中文作者**: {len(non_chinese_authors):,} ({len(non_chinese_authors)*100/len(all_authors):.2f}%)

### 2. 质量验证（抽样5,000）

#### 2.1 被排除作者检查
- **抽样数**: {len(sample_excluded):,}
- **可能误排除**: {len(wrongly_excluded)} ({len(wrongly_excluded)*100/len(sample_excluded):.2f}%)
- **主要原因**: {exclusion_reasons.most_common(1)[0][0] if wrongly_excluded else 'N/A'}

#### 2.2 筛选出作者检查
- **抽样数**: {len(sample_chinese):,}
- **可能误判（lastname非中文）**: {len(false_positives)} ({len(false_positives)*100/len(sample_chinese):.2f}%)

### 3. 姓氏识别性能（抽样10,000）
- **准确率**: {surname_accuracy:.2f}%
- **错误率**: {incorrect_surname*100/surname_total:.2f}%
- **无法判断**: {undetermined_surname*100/surname_total:.2f}%

### 4. 整体评估

**初筛质量**: {'优秀' if len(wrongly_excluded)*100/len(sample_excluded) < 2 else '良好' if len(wrongly_excluded)*100/len(sample_excluded) < 5 else '需改进'}
  - 误排除率: {len(wrongly_excluded)*100/len(sample_excluded):.2f}%
  - 误判率: {len(false_positives)*100/len(sample_chinese):.2f}%

**姓氏识别质量**: {'优秀' if surname_accuracy > 98 else '良好' if surname_accuracy > 95 else '需改进'}
  - 准确率: {surname_accuracy:.2f}%

**系统总体性能**: {'优秀 - 可部署' if surname_accuracy > 98 and len(wrongly_excluded)*100/len(sample_excluded) < 2 else '良好 - 建议优化' if surname_accuracy > 95 else '需改进'}

### 5. 发现的问题

#### 5.1 误排除案例分析
{f"主要原因: {', '.join(f'{k}({v})' for k, v in exclusion_reasons.most_common(3))}" if wrongly_excluded else "未发现误排除"}

#### 5.2 误判案例分析
{"需要检查具体案例" if len(false_positives) > 20 else "误判率很低，无需特别关注" if len(false_positives) > 0 else "未发现误判"}

### 6. 建议

{'1. 检查并修正误排除案例的原因' if len(wrongly_excluded) > 50 else ''}
{'2. 分析误判案例，优化筛选规则' if len(false_positives) > 50 else ''}
{'3. 系统性能优秀，建议进入部署阶段' if surname_accuracy > 98 and len(wrongly_excluded)*100/len(sample_excluded) < 2 else ''}
"""

print(report)

# 保存验证结果
validation_results = {
    'summary': {
        'total_authors': len(all_authors),
        'chinese_count': len(chinese_authors),
        'non_chinese_count': len(non_chinese_authors),
        'wrongly_excluded_count': len(wrongly_excluded),
        'false_positive_count': len(false_positives),
        'surname_accuracy': surname_accuracy,
        'surname_error_rate': incorrect_surname*100/surname_total if surname_total > 0 else 0
    },
    'wrongly_excluded_cases': wrongly_excluded[:200],
    'false_positive_cases': false_positives[:200],
    'surname_errors': surname_errors[:200],
    'exclusion_reasons': dict(exclusion_reasons)
}

with open(args.output, 'w', encoding='utf-8') as f:
    json.dump(validation_results, f, ensure_ascii=False, indent=2)

print(f"\n{localizer.get_text('results_saved_to')}: {args.output}")
print(localizer.get_text('test_complete'))
print("=" * 80)
