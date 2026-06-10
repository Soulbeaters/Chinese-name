# -*- coding: utf-8 -*-
"""
对比两个实验的预测结果
Compare predictions from two experiments
"""

import json
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.surname_identifier_v8 import NameRecord, batch_identify_surname_position_v8
from src.config_v8 import set_ablation_config, reset_ablation_config, AblationConfig

def load_dataset(path):
    """加载数据集"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    for i, item in enumerate(data):
        records.append(NameRecord(
            record_id=str(i),
            name_raw=item.get('original_name', ''),
            affiliation_raw=item.get('affiliation'),
            source=item.get('source', 'CROSSREF'),
            person_id=item.get('person_id'),
            publication_id=item.get('doi')
        ))
    return records, data

def main():
    # 加载数据集
    dataset_path = 'C:/program 1 in 2025/test_data/crossref_10k.json'
    records, raw_data = load_dataset(dataset_path)

    print(f"Loaded {len(records)} records")

    # 使用 baseline 配置运行 v8 算法
    baseline_config = AblationConfig(
        disable_source_prior=False,
        disable_western_exclusion=False,
        disable_batch_consistency=False,
        enable_person_consistency=True,
        enable_pub_consistency=True
    )
    set_ablation_config(baseline_config)

    # 运行v8算法（这是paper实验使用的方式）
    decisions = batch_identify_surname_position_v8(records)

    reset_ablation_config()

    # 统计预测结果
    family_first_count = sum(1 for d in decisions.values() if d.order == 'family_first')
    given_first_count = sum(1 for d in decisions.values() if d.order == 'given_first')
    unknown_count = sum(1 for d in decisions.values() if d.order == 'unknown')

    print(f"\nV8 Algorithm Predictions:")
    print(f"  family_first: {family_first_count}")
    print(f"  given_first: {given_first_count}")
    print(f"  unknown: {unknown_count}")

    # 计算准确率（使用startswith方法作为ground truth）
    correct = 0
    total = 0
    error_samples = []

    for i, item in enumerate(raw_data):
        if 'lastname' not in item or 'firstname' not in item:
            continue

        total += 1
        decision = decisions[str(i)]

        # Paper实验的ground truth推断方法
        lastname = item['lastname']
        original_name = item.get('original_name', '')

        if original_name.strip().startswith(lastname):
            gt_order = "family_first"
        else:
            gt_order = "given_first"

        if decision.order == gt_order:
            correct += 1
        elif decision.order != "unknown":
            error_samples.append({
                'index': i,
                'original_name': original_name,
                'lastname': lastname,
                'firstname': item['firstname'],
                'predicted': decision.order,
                'ground_truth': gt_order,
                'confidence': decision.confidence,
                'reasons': decision.reason_codes
            })

    accuracy = correct / total if total > 0 else 0.0
    unknown_rate = unknown_count / total if total > 0 else 0.0
    error_rate = 1.0 - accuracy - unknown_rate

    print(f"\nAccuracy (using paper GT method):")
    print(f"  Total evaluated: {total}")
    print(f"  Correct: {correct}")
    print(f"  Accuracy: {accuracy*100:.2f}%")
    print(f"  Unknown rate: {unknown_rate*100:.2f}%")
    print(f"  Error rate: {error_rate*100:.2f}%")

    print(f"\n❗ Expected accuracy from paper experiment: 96.77%")

    if abs(accuracy - 0.9677) < 0.001:
        print("✅ Accuracy matches! V8 algorithm is working correctly.")
    else:
        print(f"❌ Accuracy mismatch! Difference: {abs(accuracy - 0.9677)*100:.2f}%")

        if error_samples:
            print(f"\nFirst 10 error samples:")
            for sample in error_samples[:10]:
                print(f"  [{sample['index']}] {sample['original_name']}")
                print(f"    GT: {sample['ground_truth']}, Pred: {sample['predicted']} (conf: {sample['confidence']:.2f})")
                print(f"    Reasons: {', '.join(sample['reasons'][:3])}")

if __name__ == '__main__':
    main()
