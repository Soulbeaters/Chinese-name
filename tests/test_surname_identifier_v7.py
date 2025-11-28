# -*- coding: utf-8 -*-
"""
v7.0算法单元测试
Unit tests for v7.0 Algorithm
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.surname_identifier_v7 import identify_surname_position_v7


def test_abbreviation_detection():
    """测试缩写检测"""
    order, conf, reason = identify_surname_position_v7("Liu W.")
    assert order == "family_first"
    assert conf == 1.0

    order, conf, reason = identify_surname_position_v7("Chen J.M.")
    assert order == "family_first"
    assert conf == 1.0


def test_chinese_mode():
    """测试Chinese模式"""
    # 中文顺序（姓在前）
    order, conf, _ = identify_surname_position_v7(
        "Tang Tianxiang", mode_hint="Chinese"
    )
    assert order == "family_first"

    order, conf, _ = identify_surname_position_v7(
        "Liu Yuhui",
        affiliation="Tsinghua University, Beijing",
        mode_hint="Chinese"
    )
    assert order == "family_first"

    # 双姓氏在Chinese模式下默认family_first
    order, conf, _ = identify_surname_position_v7(
        "Lu Liu", mode_hint="Chinese"
    )
    assert order == "family_first"


def test_western_mode():
    """测试Western模式"""
    # 西方姓氏后缀
    order, conf, _ = identify_surname_position_v7("David Smith")
    assert order == "given_first"

    order, conf, _ = identify_surname_position_v7("Chris Aberson")
    assert order == "given_first"

    # 芬兰姓氏
    order, conf, _ = identify_surname_position_v7("Tuomas Savolainen")
    assert order == "given_first"


def test_mixed_mode():
    """测试Mixed模式"""
    # 无明显证据的情况
    order, conf, _ = identify_surname_position_v7("Peter Mueller")
    assert order in ["given_first", "unknown"]


def test_edge_cases():
    """测试边界情况"""
    # 空姓名
    order, conf, _ = identify_surname_position_v7("")
    assert order == "unknown"

    # 单个token
    order, conf, _ = identify_surname_position_v7("Liu")
    assert order == "unknown"


if __name__ == '__main__':
    test_abbreviation_detection()
    test_chinese_mode()
    test_western_mode()
    test_mixed_mode()
    test_edge_cases()
    print("All v7.0 algorithm tests passed!")
