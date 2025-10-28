# 中文作者筛选与姓氏识别系统 - 最终部署报告
# Chinese Author Filter & Surname Identification System - Final Deployment Report

**项目**: ИСТИНА科学计量系统 - 中文作者处理模块
**版本**: v5.0 Enhanced (Recommended for Deployment)
**日期**: 2025年
**测试数据规模**: 301,586 authors from Crossref

---

## 执行摘要 / Executive Summary

经过全面测试和对比，**v5.0算法**被推荐作为生产部署版本。

### 关键性能指标

| 指标 | v5.0 | v6.0 | 推荐 |
|------|------|------|------|
| **识别准确率** | 99.46% | 96.78% | ✓ v5.0 |
| **误判率** | 0.54% | 3.22% | ✓ v5.0 |
| 中文作者数量 | 102,529 (34.00%) | 104,552 (34.67%) | v6.0 |
| 姓氏识别准确率 | 97.94% | 未测试 | ✓ v5.0 |
| 代码复杂度 | 低 | 高 | ✓ v5.0 |
| 可维护性 | 优秀 | 良好 | ✓ v5.0 |

**结论**: v5.0在质量和稳定性上明显优于v6.0，虽然v6.0多识别2,023个作者，但误判率增加了5倍，不可接受。

---

## 系统架构 / System Architecture

### 两阶段处理流程

```
输入: 作者原始姓名 (original_name) + 机构信息 (affiliation)
    ↓
┌───────────────────────────────────────┐
│  Stage 1: 中文作者初筛                  │
│  Chinese Author Filtering              │
│  (filter_chinese_author_v5)           │
└───────────────────────────────────────┘
    ↓
    ├─→ 非中文作者 → 排除
    └─→ 中文作者 → Stage 2
            ↓
┌───────────────────────────────────────┐
│  Stage 2: 姓氏位置识别                  │
│  Surname Position Identification       │
│  (identify_surname_position)          │
└───────────────────────────────────────┘
    ↓
输出: (position, confidence, reason)
    - position: "family_first" / "given_first"
    - confidence: 0.0 ~ 1.0
    - reason: 判断依据
```

---

## v5.0 算法详解 / Algorithm Details

### 第一性原理 / First Principles

**核心理念**: "是否明确违反中文规则"，而非"是否像中文"

1. **中文作者定义**:
   - 使用中文姓名系统（简体拼音 + 繁体拼音）
   - 包括：大陆、台湾、香港、新加坡、海外华人

2. **必要条件**:
   - 必须包含中文姓氏（简体或繁体）

3. **排除条件**:
   - 包含外国姓氏
   - 包含明确的外文专有名词
   - 复合名中包含外文成分

### 关键技术组件

#### 1. 繁体中文姓氏支持

```python
# data/traditional_chinese_surnames.py

WADE_GILES_SURNAMES = {
    'lee': ('李', 'li'),        # 台湾
    'hsu': ('徐', 'xu'),        # 台湾
    'chang': ('张', 'zhang'),
}

CANTONESE_SURNAMES = {
    'wong': ('王/黄', 'wang/huang'),  # 香港
    'chan': ('陈', 'chen'),
    'leung': ('梁', 'liang'),
}

HOKKIEN_SURNAMES = {
    'lim': ('林', 'lin'),       # 新加坡
    'tan': ('陈', 'chen'),
    'ong': ('王', 'wang'),
}
```

**覆盖范围**: 52个繁体中文姓氏拼写

#### 2. 变体拼音映射

```python
# data/variant_pinyin_map.py

VARIANT_PINYIN_MAP = {
    'tsai': ['cai'],           # 蔡
    'tseng': ['zeng'],         # 曾
    'hsieh': ['xie'],          # 谢
    # ... 40+ mappings
}
```

**作用**: 将威妥玛拼音、粤语拼音等转换为标准汉语拼音进行姓氏匹配

#### 3. 外国姓氏排除库

```python
# data/non_chinese_surnames.py

NON_CHINESE_SURNAMES = {
    # 高频外国姓氏 (420+)
    'nguyen',      # 越南
    'kim', 'park', # 韩国
    'smith', 'johnson', # 英美
    'garcia', 'rodriguez', # 西班牙
    'schmidt', 'müller', # 德国
    # ...
}
```

**覆盖范围**: 420+个外国姓氏

#### 4. 简体中文姓氏库

```python
# data/surname_pinyin_db.py

SURNAME_PINYIN_SET = {
    'wang', 'li', 'zhang', 'liu', 'chen',
    'yang', 'zhao', 'huang', 'zhou', 'wu',
    # ... 500+ Chinese surnames
}
```

**覆盖范围**: 500+个中文姓氏拼音

### 智能括号处理

**策略**: 完全移除括号，只基于主体信息判断

```python
# v5.0 logic
remove_parentheses("Bo Ma(马博)")         → "Bo Ma"    → 中文
remove_parentheses("Shengzhong(Frank) Liu") → "Shengzhong Liu" → 中文
remove_parentheses("Li(Smith) Wei")       → "Li Wei"   → 中文
```

**原理**: 括号内是补充信息（汉字、别名等），不应影响主体判断

---

## 性能测试结果 / Performance Test Results

### 测试环境

- **数据来源**: Crossref API
- **数据规模**: 301,586 authors
- **测试方法**:
  - 完整数据集处理
  - 随机抽样质量验证 (5,000 samples)
  - Crossref人工标注对照

### v5.0 详细结果

#### 初筛性能

```
总作者数:        301,586
中文作者:        102,529  (34.00%)
非中文作者:      199,057  (66.00%)
不确定:          0        (0.00%)
```

#### 质量指标

**误判率**: 0.54% (27/5,000)

**误判案例分析**:
- Crossref标注错误: 12例 (Li Jianfei → lastname标注为Jianfei)
- 遗漏外国姓氏: 8例 (Tai Phan, Lou Brillault等)
- 边界情况: 7例 (单字母+模糊token)

**误排除率**: 1.04% (52/5,000)

**误排除原因**:
- 外文专有名词判断: 10例 (Patrick Wu, Gary Zhang)
- 含"-hao"/"-hui"等音节: 42例 (Yunhao Cai, Wenhui Niu)

#### 姓氏识别性能

```
测试样本:        10,000 (中文作者)
正确识别:        9,794  (97.94%)
错误识别:        206    (2.06%)
```

**主要错误类型**:
- 双姓氏歧义: Sun Kun (孙坤 vs 坤孙)
- Crossref标注错误

### v6.0 对比结果

#### 初筛性能

```
总作者数:        301,586
中文作者:        104,552  (34.67%)  [+2,023 vs v5.0]
非中文作者:      197,034  (65.33%)
```

#### 质量指标

**误判率**: 3.22% (161/5,000) ⚠️

**新增误判类型**:
- 单字母+外文姓: 88% (R Scannell, A Feltre, L Rhodes...)
- Crossref标注错误: 12%

**问题根源**:
v6.0对单字母处理过于宽松，导致大量`X Surname`格式的外国作者被误判为中文。

---

## 部署建议 / Deployment Recommendations

### ✓ 推荐部署: v5.0 Enhanced

**理由**:
1. **质量优先**: 0.54%误判率 vs v6.0的3.22%
2. **稳定可靠**: 经过充分验证，边界情况少
3. **可维护性**: 代码简洁，逻辑清晰
4. **可扩展性**: 易于通过姓氏库更新改进

### 后续优化方向

#### 1. 补充外国姓氏库 (优先级: 高)

**目标**: 将误判率从0.54%降至0.3%以下

**待补充姓氏** (基于验证发现):
```python
# 越南姓氏
'phan', 'tran', 'le', 'hoang', 'vu'

# 遗漏的欧美姓氏
'brillault', 'rosenbloom'

# 单字母问题的特殊处理
# 建议: 如果lastname长度<3且非中文姓氏，直接排除
```

#### 2. 音节特征检测 (优先级: 中)

**目标**: 处理"-hao", "-hui"等被误排除的案例

**方案**:
```python
# 仅当同时满足以下条件时排除:
# 1. 包含"-hui"/"-hao"等音节
# 2. 另一个token也不是中文姓氏
# 3. 无中国机构信息

# 案例: Yunhao Cai
# - Yunhao包含-hao，但Cai是中文姓 → 保留
```

#### 3. ORCID集成 (优先级: 中)

**目标**: 解决双姓氏歧义 (Sun Kun类型)

**方案**:
- 查询ORCID历史发表记录
- 分析其他论文中的姓名格式
- 机构信息辅助判断

#### 4. 机器学习增强 (优先级: 低)

**目标**: 处理边界情况

**方案**:
- 基于v5.0规则输出作为特征
- 训练分类器处理uncertain cases
- 保持规则为主，ML为辅

---

## 文件清单 / File List

### 核心算法文件

```
C:\program 1 in 2025\
├── final_filter_v5_enhanced.py          # v5.0主算法 (部署版本)
├── src\surname_identifier.py           # 姓氏位置识别
│
├── data\
│   ├── surname_pinyin_db.py            # 简体中文姓氏库
│   ├── traditional_chinese_surnames.py # 繁体中文姓氏库
│   ├── non_chinese_surnames.py         # 外国姓氏排除库
│   └── variant_pinyin_map.py           # 变体拼音映射
```

### 测试与验证文件

```
├── comprehensive_validation_v5.py       # v5.0全面验证
├── comprehensive_final_test.py          # v5 vs v6完整对比
│
├── filtered_chinese_v5_enhanced.json    # v5.0筛选结果
├── comprehensive_validation_v5_results.json  # v5.0验证报告
├── comprehensive_final_test_results.json     # 最终对比报告
```

### 实验性文件 (不推荐部署)

```
├── final_filter_v6_ultimate.py          # v6.0 (误判率3.22%, 不推荐)
├── v6_false_positive_analysis.json      # v6.0问题分析
```

---

## API 接口 / API Interface

### 1. 中文作者筛选

```python
from final_filter_v5_enhanced import filter_chinese_author_v5

# 输入
original_name = "Wei Li"
affiliation = "Tsinghua University, Beijing, China"

# 调用
is_chinese, confidence, reason = filter_chinese_author_v5(
    original_name,
    affiliation
)

# 输出
# is_chinese: True
# confidence: 0.95
# reason: "中文作者 (姓氏: Wei)"
```

**返回值**:
- `is_chinese`: `True` / `False` / `None` (不确定)
- `confidence`: 0.0 ~ 1.0 (置信度)
- `reason`: 判断依据字符串

### 2. 姓氏位置识别

```python
from src.surname_identifier import identify_surname_position

# 输入
original_name = "Wei Li"
affiliation = "Tsinghua University, Beijing, China"

# 调用
position, confidence, reason = identify_surname_position(
    original_name,
    affiliation
)

# 输出
# position: "family_first"  # or "given_first"
# confidence: 0.95
# reason: "Evidence: ..."
```

**返回值**:
- `position`: `"family_first"` / `"given_first"` / `None`
- `confidence`: 0.0 ~ 1.0
- `reason`: 判断依据

---

## 使用示例 / Usage Examples

### 批量处理Crossref数据

```python
import json
from final_filter_v5_enhanced import filter_chinese_author_v5
from src.surname_identifier import identify_surname_position

# 加载数据
with open('crossref_authors.json', 'r', encoding='utf-8') as f:
    authors = json.load(f)

chinese_authors = []

for author in authors:
    name = author.get('original_name', '')
    affiliation = author.get('affiliation', '')

    # Stage 1: 筛选中文作者
    is_chinese, conf, reason = filter_chinese_author_v5(name, affiliation)

    if is_chinese:
        # Stage 2: 识别姓氏位置
        position, pos_conf, pos_reason = identify_surname_position(
            name, affiliation
        )

        author['is_chinese'] = True
        author['surname_position'] = position
        author['confidence'] = conf * pos_conf

        chinese_authors.append(author)

# 保存结果
with open('chinese_authors_processed.json', 'w', encoding='utf-8') as f:
    json.dump(chinese_authors, f, ensure_ascii=False, indent=2)
```

### 集成到ИСТИНА系统

```python
# 伪代码示例

class AuthorProcessor:
    def __init__(self):
        # 预加载数据库
        from data.surname_pinyin_db import SURNAME_PINYIN_SET
        self.surname_db = SURNAME_PINYIN_SET

    def process_author(self, author_record):
        """处理单个作者记录"""

        # 提取信息
        name = author_record['name']
        affiliation = author_record['affiliation']

        # 中文作者判断
        is_chinese, conf, reason = filter_chinese_author_v5(
            name, affiliation
        )

        if not is_chinese:
            return None  # 非中文作者，不处理

        # 姓氏识别
        position, pos_conf, pos_reason = identify_surname_position(
            name, affiliation
        )

        # 提取姓和名
        tokens = name.split()
        if position == 'family_first':
            surname = tokens[-1]
            given_name = ' '.join(tokens[:-1])
        else:
            surname = tokens[0]
            given_name = ' '.join(tokens[1:])

        # 返回标准化结果
        return {
            'original_name': name,
            'surname': surname,
            'given_name': given_name,
            'is_chinese': True,
            'confidence': conf * pos_conf,
            'surname_position': position,
            'affiliation': affiliation
        }
```

---

## 已知限制与未来工作 / Known Limitations & Future Work

### 当前限制

1. **双姓氏歧义**: Sun Kun类型无法完全解决 (需要ORCID或更多上下文)
2. **Crossref标注错误**: 部分误判实际是源数据错误 (Li Jianfei等)
3. **单音节名**: Wei, Bo, Yu等极短名字处理有局限
4. **复杂复合名**: 带多个连字符的复合名识别不完善

### 待改进项

1. ✓ **高优先级**:
   - 补充外国姓氏库 (Nguyen, Phan等)
   - 优化"-hao"/"-hui"音节处理

2. **中优先级**:
   - ORCID集成
   - 历史发表记录分析
   - 多作者联合判断 (同一论文的其他作者)

3. **低优先级**:
   - 机器学习模型辅助
   - 深度学习NER模型
   - 跨语言姓名标准化

---

## 版本历史 / Version History

### v5.0 Enhanced (Current - Recommended)
- ✓ 繁体中文姓氏支持 (Lee, Wong, Hsu等)
- ✓ 智能括号处理 (完全移除策略)
- ✓ 420+外国姓氏排除
- ✓ 误判率: 0.54%
- ✓ 姓氏识别准确率: 97.94%

### v6.0 Ultimate (Experimental - Not Recommended)
- ✗ 外文音节模式检测
- ✗ 双重验证机制
- ✗ 智能单字母处理
- ✗ 误判率: 3.22% (相比v5.0恶化5倍)
- ✗ 单字母bug导致大量误判

### v4.0 First Principles
- ✓ 第一性原理重构
- ✓ 101,330 中文作者 (33.60%)
- ✓ 不确定率降至0%

### v3.1 Bugfix
- ✓ 修复单音节名过滤问题

### v3.0 Multi-source
- 多源证据融合
- 姓氏位置识别准确率92.12%

### v2.0 Enhanced
- 变体拼音支持
- 机构信息集成

### v1.0 Baseline
- 基础姓氏匹配
- 准确率37.39%

---

## 性能基准 / Performance Benchmarks

### 处理速度

- **单条记录**: ~0.001秒
- **批量处理** (301,586 authors): ~5分钟
- **内存占用**: <100MB

### 可扩展性

- ✓ 支持百万级作者处理
- ✓ 数据库查询高效 (set lookup O(1))
- ✓ 无需GPU/大内存

---

## 联系方式 / Contact

**项目负责人**: Ма Цзясин (Ma Jiaxin)
**机构**: 俄罗斯莫斯科国立大学 计算机科学系
**研究方向**: 交互式科学计量系统中大数据的输入与验证问题
**GitHub**: https://github.com/Soulbeaters/Chinese-name

---

## 许可与引用 / License & Citation

本项目为ИСТИНА系统的一部分，用于学术研究目的。

如使用本算法，请引用:
```
Ma, J. (2025). Chinese Author Identification and Surname Recognition
for Scientometric Systems. Moscow State University.
```

---

**文档版本**: 1.0
**最后更新**: 2025年
**状态**: ✓ 已验证，推荐部署
