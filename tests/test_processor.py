# -*- coding: utf-8 -*-
"""
ChineseNameProcessor 测试脚本

作者: Ма Цзясин
项目: ИСТИНА - 智能科学计量数据专题研究系统
"""

import sys
import os
import json
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chinese_name_processor import ChineseNameProcessor, SurnameDatabase, create_default_processor

def test_basic_functionality():
    """测试基本功能"""
    print("=== 基本功能测试 ===")

    processor = create_default_processor()

    test_cases = [
        # (输入, 期望的姓氏, 期望的名字)
        ("李小明", "李", "小明"),
        ("王", "王", ""),
        ("欧阳修", "欧阳", "修"),
        ("司马光", "司马", "光"),
        ("张三丰", "张", "三丰"),
        ("陈独秀", "陈", "独秀")
    ]

    success_count = 0
    for name, expected_surname, expected_firstname in test_cases:
        result = processor.process_name(name)

        print(f"\n测试: {name}")
        print(f"  结果: {result.components.surname} | {result.components.first_name}")
        print(f"  期望: {expected_surname} | {expected_firstname}")
        print(f"  置信度: {result.confidence_score:.2f}")
        print(f"  成功: {result.is_successful()}")

        if result.components.surname == expected_surname and result.components.first_name == expected_firstname:
            success_count += 1
            print("  ✓ 通过")
        else:
            print("  ✗ 失败")

        if result.errors:
            print(f"  错误: {result.errors}")

    print(f"\n基本功能测试结果: {success_count}/{len(test_cases)} 通过")
    return success_count == len(test_cases)

def test_error_handling():
    """测试错误处理"""
    print("\n=== 错误处理测试 ===")

    processor = create_default_processor()

    error_cases = [
        "",           # 空字符串
        None,         # None值
        "   ",        # 只有空格
        "123",        # 数字
        "abc",        # 纯英文
        "李小明王五", # 太长的名字
    ]

    for case in error_cases:
        print(f"\n测试错误输入: {repr(case)}")
        result = processor.process_name(case)
        print(f"  成功: {result.is_successful()}")
        print(f"  错误数量: {len(result.errors)}")
        if result.errors:
            print(f"  错误信息: {result.errors[0]}")

def test_batch_processing():
    """测试批量处理"""
    print("\n=== 批量处理测试 ===")

    processor = create_default_processor()

    names = ["李明", "王小红", "张三", "欧阳修", "司马光"]

    results = processor.batch_process(names)

    print(f"批量处理 {len(names)} 个姓名:")
    successful = 0

    for i, (name, result) in enumerate(zip(names, results)):
        print(f"  {i+1}. {name} -> {result.components.surname} | {result.components.first_name}")
        if result.is_successful():
            successful += 1

    print(f"成功处理: {successful}/{len(names)}")
    return successful == len(names)

def test_surname_database():
    """测试姓氏数据库"""
    print("\n=== 姓氏数据库测试 ===")

    # 创建测试数据
    test_surnames = {
        '测试': {'pinyin': 'ceshi', 'palladius': 'цеши', 'frequency': 1, 'region': ['测试']},
        '复合测': {'pinyin': 'fuheceshi', 'palladius': 'фухэцеши', 'frequency': 1, 'region': ['测试']}
    }

    db = SurnameDatabase(test_surnames)

    # 测试基本查询
    info = db.lookup_surname('测试')
    print(f"查询'测试': {info.pinyin if info else 'Not found'}")

    # 测试复合姓氏
    is_compound = db.is_compound_surname('复合测')
    print(f"'复合测'是复合姓氏: {is_compound}")

    # 测试拼音查询
    surnames = db.find_by_pinyin('ceshi')
    print(f"拼音'ceshi'对应姓氏: {surnames}")

    # 测试动态添加
    success = db.add_surname('新姓', {
        'pinyin': 'xinxing',
        'palladius': 'синсин',
        'frequency': 1,
        'region': ['测试']
    })
    print(f"动态添加姓氏: {success}")

    # 测试导出
    try:
        db.export_to_json('test_surnames.json')
        print("导出姓氏数据库: 成功")

        # 清理测试文件
        if os.path.exists('test_surnames.json'):
            os.remove('test_surnames.json')

    except Exception as e:
        print(f"导出姓氏数据库: 失败 - {e}")

def test_configuration():
    """测试配置功能"""
    print("\n=== 配置测试 ===")

    config = {
        'confidence_threshold': 0.8,
        'enable_fuzzy_matching': False,
        'max_alternatives': 5
    }

    processor = ChineseNameProcessor(config=config)

    # 验证配置
    errors = processor.validate_configuration()
    print(f"配置验证错误: {len(errors)}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    # 获取统计信息
    stats = processor.get_statistics()
    print(f"处理器统计:")
    print(f"  姓氏数据库大小: {stats['surname_db_size']}")
    print(f"  复合姓氏数量: {stats['compound_surnames_count']}")

def test_performance():
    """性能测试"""
    print("\n=== 性能测试 ===")

    import time

    processor = create_default_processor()

    # 生成测试数据
    test_names = ["李明", "王小红", "张三", "欧阳修", "司马光"] * 100

    start_time = time.time()
    results = processor.batch_process(test_names)
    end_time = time.time()

    total_time = end_time - start_time
    avg_time = total_time / len(test_names) * 1000  # 毫秒

    successful = sum(1 for r in results if r.is_successful())

    print(f"性能测试结果:")
    print(f"  处理姓名数量: {len(test_names)}")
    print(f"  总时间: {total_time:.3f}秒")
    print(f"  平均时间: {avg_time:.2f}毫秒/姓名")
    print(f"  成功率: {successful/len(test_names)*100:.1f}%")

def main():
    """主测试函数"""
    print("ChineseNameProcessor 测试套件")
    print("=" * 50)

    tests = [
        ("基本功能", test_basic_functionality),
        ("错误处理", test_error_handling),
        ("批量处理", test_batch_processing),
        ("姓氏数据库", test_surname_database),
        ("配置功能", test_configuration),
        ("性能测试", test_performance)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n开始测试: {test_name}")
            result = test_func()
            if result is None or result:  # None表示无明确结果，True表示通过
                print(f"✓ {test_name} 通过")
                passed += 1
            else:
                print(f"✗ {test_name} 失败")
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} 异常: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"测试完成: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("🎉 所有测试通过!")
    else:
        print("⚠️  存在失败的测试，请检查代码")

if __name__ == "__main__":
    main()