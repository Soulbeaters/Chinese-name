# -*- coding: utf-8 -*-
"""
修复所有测试文件的Unicode编码问题
Fix Unicode encoding issues in all test files
"""

import os
import re
import sys

def fix_unicode_in_file(filepath):
    """修复单个文件的Unicode问题"""
    if not os.path.exists(filepath):
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 替换常见的有问题的Unicode字符
        replacements = {
            '✓': '✓',    # 使用ASCII替代
            '✗': '✗',    # 使用ASCII替代
            '❌': '[X]',  # 替换为ASCII
            '✅': '[✓]',  # 替换为ASCII
            '🚀': '[START]',  # 替换为ASCII
            '🐢': '[SLOW]',   # 替换为ASCII
            '⚡': '[FAST]',   # 替换为ASCII
            '⚠️': '[WARN]',   # 替换为ASCII
            '📊': '[STATS]',  # 替换为ASCII
            '🎉': '[SUCCESS]', # 替换为ASCII
            '🔍': '[SEARCH]',  # 替换为ASCII
            '📝': '[TEST]',    # 替换为ASCII
        }

        modified = False
        for old, new in replacements.items():
            if old in content:
                content = content.replace(old, new)
                modified = True

        # 修复包含Unicode的print语句
        unicode_patterns = [
            (r'print\(f?"[^"]*\\u[0-9a-fA-F]{4}[^"]*"\)', 'print statement with unicode'),
            (r'print\(f?"[^"]*\\U[0-9a-fA-F]{8}[^"]*"\)', 'print statement with unicode32'),
        ]

        for pattern, desc in unicode_patterns:
            matches = re.findall(pattern, content)
            if matches:
                print(f"Found {len(matches)} {desc} in {filepath}")

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"Error fixing {filepath}: {e}")

    return False

def main():
    """修复所有Python文件的Unicode问题"""
    files_to_fix = [
        'test_processor.py',
        'test_processor_ru.py',
        'performance_benchmark.py',
        'test_surname_fix.py',
        'test_transliterated_names.py',
        'demo_trie_performance.py'
    ]

    print("=== Unicode编码问题修复工具 ===")

    fixed_count = 0
    for filename in files_to_fix:
        if os.path.exists(filename):
            if fix_unicode_in_file(filename):
                print(f"修复了 {filename}")
                fixed_count += 1
            else:
                print(f"检查了 {filename} (无需修复)")
        else:
            print(f"文件不存在: {filename}")

    print(f"\n总计修复了 {fixed_count} 个文件")

    # 重新测试修复后的集成
    print("\n=== 重新测试Trie集成 ===")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_trie_integration import test_trie_integration
        test_trie_integration()
    except Exception as e:
        print(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    main()