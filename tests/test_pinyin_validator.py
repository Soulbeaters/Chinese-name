# -*- coding: utf-8 -*-
"""
拼音验证器单元测试
Unit tests for Pinyin Validator
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pinyin_validator import (
    segment_pinyin,
    is_valid_pinyin_name,
    calculate_given_name_confidence_v7,
)


def test_segment_pinyin_chinese_names():
    """测试中文名拼音分词"""
    # 2音节名字
    is_valid, count, syllables = segment_pinyin("tianxiang")
    assert is_valid == True
    assert count == 2
    assert syllables == ['tian', 'xiang']

    is_valid, count, syllables = segment_pinyin("yuhui")
    assert is_valid == True
    assert count == 2

    # 3音节名字
    is_valid, count, syllables = segment_pinyin("xiaohua")
    assert is_valid == True
    assert count == 2  # xiao-hua

    # 单音节
    is_valid, count, syllables = segment_pinyin("bo")
    assert is_valid == True
    assert count == 1


def test_segment_pinyin_western_names():
    """测试西方姓名应该失败"""
    # 芬兰姓氏
    is_valid, count, _ = segment_pinyin("savolainen")
    assert is_valid == False

    # 法国姓氏
    is_valid, count, _ = segment_pinyin("desrichard")
    assert is_valid == False

    # 德国姓氏
    is_valid, count, _ = segment_pinyin("friedemann")
    assert is_valid == False

    # 英语姓氏
    is_valid, count, _ = segment_pinyin("smith")
    assert is_valid == False


def test_calculate_given_name_confidence():
    """测试名字置信度计算"""
    # 2音节中文名
    conf, reason = calculate_given_name_confidence_v7("tianxiang")
    assert conf >= 0.8

    conf, reason = calculate_given_name_confidence_v7("yuhui")
    assert conf >= 0.8

    # 单音节
    conf, reason = calculate_given_name_confidence_v7("bo")
    assert 0.4 <= conf <= 0.6

    # 西方姓氏
    conf, reason = calculate_given_name_confidence_v7("savolainen")
    assert conf == 0.0

    conf, reason = calculate_given_name_confidence_v7("smith")
    assert conf == 0.0


def test_edge_cases():
    """测试边界情况"""
    # 空字符串
    is_valid, count, _ = segment_pinyin("")
    assert is_valid == False

    # 非字母字符
    is_valid, count, _ = segment_pinyin("123")
    assert is_valid == False

    # 连字符
    is_valid, count, syllables = segment_pinyin("tian-xiang")
    assert is_valid == True
    assert count == 2


if __name__ == '__main__':
    test_segment_pinyin_chinese_names()
    test_segment_pinyin_western_names()
    test_calculate_given_name_confidence()
    test_edge_cases()
    print("All pinyin validator tests passed!")
