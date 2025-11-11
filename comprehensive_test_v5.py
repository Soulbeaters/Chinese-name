# -*- coding: utf-8 -*-
"""
v5.0算法完整数据集综合测试
Comprehensive Test on Full Crossref Dataset for v5.0 Algorithm

测试内容 / Test Contents / Содержание тестирования:
1. v5.0算法在完整数据上的表现
2. 质量验证（抽样检查）
3. 生成详细性能报告

中文注释：v5.0算法综合测试
Русский комментарий: Комплексное тестирование алгоритма v5.0
"""

import json
import random
import argparse
from collections import Counter
from final_filter_v5_enhanced import filter_chinese_author_v5
from data.surname_pinyin_db import is_surname_pinyin
from data.variant_pinyin_map import get_all_possible_pinyins
from data.traditional_chinese_surnames import is_traditional_chinese_surname
from src.localization import get_localizer

# 命令行参数解析 / Парсинг аргументов командной строки
def parse_arguments():
    """
    解析命令行参数 / Парсинг аргументов командной строки
    Parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        description='Chinese Author Name Processing System - v5.0 Comprehensive Test\n'
                    'Система обработки китайских имен авторов - Комплексное тестирование v5.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法 / Примеры использования / Usage Examples:

  # 使用默认数据（导师数据，俄语输出）
  python comprehensive_test_v5.py

  # 使用自定义数据路径
  python comprehensive_test_v5.py --data-path "C:/custom/path/crossref_authors.json"

  # 英语输出
  python comprehensive_test_v5.py --language en

  # 中文输出
  python comprehensive_test_v5.py --language zh
        '''
    )

    parser.add_argument(
        '--data-path',
        type=str,
        default=r"C:\istina\materia 材料\测试表单\crossref_authors.json",
        help='Path to crossref_authors.json file / Путь к файлу crossref_authors.json'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=r"C:\program 1 in 2025\comprehensive_test_v5_results.json",
        help='Output file path / Путь к выходному файлу'
    )

    parser.add_argument(
        '--language',
        type=str,
        choices=['zh', 'ru', 'en'],
        default='ru',
        help='Output language (zh=Chinese, ru=Russian, en=English) / Язык вывода (по умолчанию: ru)'
    )

    return parser.parse_args()

# 解析命令行参数
args = parse_arguments()

# 初始化本地化器 / Инициализация локализатора / Initialize localizer
localizer = get_localizer(args.language)

print("=" * 80)
print(f"v5.0 Algorithm - {localizer.get_text('comprehensive_test')}")
print("=" * 80)

# 加载完整Crossref数据
CROSSREF_DATA = args.data_path
print(f"\n{localizer.get_text('loading_data')}:")
print(f"  {CROSSREF_DATA}")

with open(CROSSREF_DATA, 'r', encoding='utf-8') as f:
    all_authors = json.load(f)

print(f"\n{localizer.get_text('total_authors')}: {len(all_authors):,}")

# ========== 测试 v5.0 ==========
print("\n" + "=" * 80)
print(f"{localizer.get_text('testing_algorithm')} v5.0")
print("=" * 80)

v5_chinese = []
v5_non_chinese = []

print(f"\n{localizer.get_text('running_filter')} v5.0...")
for i, author in enumerate(all_authors):
    if i > 0 and i % 50000 == 0:
        print(localizer.get_progress_message(i, len(all_authors)), flush=True)

    is_chinese, conf, reason = filter_chinese_author_v5(
        author.get('original_name', ''),
        author.get('affiliation', '')
    )

    if is_chinese is True:
        v5_chinese.append(author)
    elif is_chinese is False:
        v5_non_chinese.append(author)

v5_total = len(v5_chinese) + len(v5_non_chinese)

print(f"\nv5.0 {localizer.get_text('result')}:")
print(f"  {localizer.get_text('total')}: {v5_total:,}")
print(f"  {localizer.get_text('chinese_authors')}: {len(v5_chinese):,} ({len(v5_chinese)*100/v5_total:.2f}%)")
print(f"  {localizer.get_text('non_chinese_authors')}: {len(v5_non_chinese):,} ({len(v5_non_chinese)*100/v5_total:.2f}%)")

# ========== 质量验证 ==========
print("\n" + "=" * 80)
print(f"{localizer.get_text('quality_check')} ({localizer.get_text('sample_size')}: 5,000)")
print("=" * 80)

def validate_false_positives(chinese_list, sample_size=5000):
    """检查筛选出的中文作者中的误判率"""
    sample = random.sample(chinese_list, min(sample_size, len(chinese_list)))

    false_positives = []
    for author in sample:
        lastname = author.get('lastname', '').strip().lower()
        if not lastname:
            continue

        is_chinese = False
        if is_traditional_chinese_surname(lastname):
            is_chinese = True
        if not is_chinese:
            all_forms = get_all_possible_pinyins(lastname)
            if any(is_surname_pinyin(form) for form in all_forms):
                is_chinese = True

        if not is_chinese:
            false_positives.append(author)

    return false_positives, len(false_positives)*100/len(sample) if sample else 0

# v5.0质量验证
print(f"\nv5.0 {localizer.get_text('quality_check')} (5,000 {localizer.get_text('sample_size')})...")
v5_fp, v5_fp_rate = validate_false_positives(v5_chinese)
print(f"  {localizer.get_text('false_positives')}: {len(v5_fp)} ({v5_fp_rate:.2f}%)")

# ========== 最终报告 ==========
print("\n" + "=" * 80)
print(localizer.get_text('final_report'))
print("=" * 80)

report = f"""
## v5.0 {localizer.get_text('comprehensive_test')} {localizer.get_text('result')}

### {localizer.get_text('dataset')}
- **{localizer.get_text('source')}**: {CROSSREF_DATA}
- **{localizer.get_text('total_authors')}**: {len(all_authors):,}

### v5.0 {localizer.get_text('performance')}
- **{localizer.get_text('chinese_authors')}**: {len(v5_chinese):,} ({len(v5_chinese)*100/v5_total:.2f}%)
- **{localizer.get_text('non_chinese_authors')}**: {len(v5_non_chinese):,} ({len(v5_non_chinese)*100/v5_total:.2f}%)
- **{localizer.get_text('false_positive_rate')}**: {v5_fp_rate:.2f}% (based on 5,000 samples)

### {localizer.get_text('key_findings')}

1. **Algorithm {localizer.get_text('performance')}**: v5.0
   - {localizer.get_text('false_positive_rate')}: {v5_fp_rate:.2f}%
   - {localizer.get_text('result')}: {'Excellent' if v5_fp_rate < 1.0 else 'Good' if v5_fp_rate < 2.0 else 'Needs improvement'}

2. **{localizer.get_text('recommendation')}**:
   - {'Deploy v5.0 - excellent quality' if v5_fp_rate < 1.0 else 'Review false positive cases' if v5_fp_rate < 2.0 else 'Further optimization needed'}

### Performance Metrics Summary / Сводка метрик производительности

| Metric / Метрика | v5.0 | Quality / Качество |
|------------------|------|-------------------|
| {localizer.get_text('chinese_authors')} | {len(v5_chinese):,} ({len(v5_chinese)*100/v5_total:.1f}%) | - |
| {localizer.get_text('false_positive_rate')} | {v5_fp_rate:.2f}% | {'Excellent / Отлично' if v5_fp_rate < 1.0 else 'Good / Хорошо'} |
"""

print(report)

# 保存结果
results = {
    'dataset': {
        'source': CROSSREF_DATA,
        'total_authors': len(all_authors)
    },
    'v5_performance': {
        'chinese_count': len(v5_chinese),
        'non_chinese_count': len(v5_non_chinese),
        'chinese_percentage': len(v5_chinese)*100/v5_total,
        'false_positive_rate': v5_fp_rate,
        'false_positive_samples': [{
            'name': fp.get('original_name', ''),
            'lastname': fp.get('lastname', ''),
            'firstname': fp.get('firstname', '')
        } for fp in v5_fp[:100]]
    }
}

output_file = args.output
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{localizer.get_text('results_saved_to')}: {output_file}")
print(localizer.get_text('test_complete'))
print("=" * 80)
