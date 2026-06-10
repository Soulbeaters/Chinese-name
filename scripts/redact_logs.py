# -*- coding: utf-8 -*-
"""
日志脱敏工具 / Log Redaction Tool

将完整的决策日志脱敏为可随论文提交的安全样本
Redact full decision logs to safe samples for paper submission

核心功能 / Core Features:
1. 移除input_tokens原文 / Remove original input_tokens
2. 替换为统计特征+token hash / Replace with statistical features + token hash
3. 保留reasons_topk（可解释性证据）/ Preserve reasons_topk (interpretability evidence)
4. 确定性采样策略（可复现）/ Deterministic sampling strategy (reproducible)

作者 / Author: Ma Jiaxin
日期 / Date: 2025-12-20
"""

import argparse
import json
import hashlib
import os
import random
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone


class LogRedactor:
    """
    日志脱敏器 / Log Redactor

    按照GDPR和数据安全要求设计的日志脱敏处理
    Log redaction designed following GDPR and data security requirements
    """

    def __init__(
        self,
        salt_env: str = "ISTINA_LOG_SALT",
        seed: int = 42,
    ):
        """
        初始化脱敏器

        Args:
            salt_env: Salt环境变量名
            seed: 随机种子（用于确定性采样）
        """
        self.salt = os.getenv(salt_env, "")
        self.salt_env = salt_env

        # A3: 强制要求salt，不允许为空
        if not self.salt:
            raise ValueError(
                f"[ERROR] Environment variable {salt_env} is not set or empty.\n"
                f"Salt is REQUIRED for secure, reproducible redaction.\n"
                f"Please set it before running:\n"
                f"  Windows: $env:{salt_env} = \"<your-secure-random-string>\"\n"
                f"  Linux/Mac: export {salt_env}=\"<your-secure-random-string>\"\n"
                f"\nNote: Salt must be at least 32 characters (recommend using: openssl rand -hex 32)"
            )

        self.seed = seed
        random.seed(seed)

    def hash_token(self, token: str) -> str:
        """计算token的哈希值 / Compute token hash"""
        normalized = token.strip().lower()
        return hashlib.sha256(f"{self.salt}{normalized}".encode('utf-8')).hexdigest()[:16]

    def analyze_token(self, token: str) -> Dict[str, any]:
        """
        分析token的统计特征 / Analyze token statistical features

        Args:
            token: 原始token

        Returns:
            特征字典 / Feature dictionary
        """
        # Detect script
        has_latin = any('\u0041' <= c <= '\u007A' for c in token)
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in token)
        has_han = any('\u4E00' <= c <= '\u9FFF' for c in token)

        if has_han and not has_latin and not has_cyrillic:
            script = "han"
        elif has_cyrillic and not has_latin and not has_han:
            script = "cyrillic"
        elif has_latin and not has_cyrillic and not has_han:
            script = "latin"
        elif has_han or has_cyrillic or has_latin:
            script = "mixed"
        else:
            script = "other"

        # Generate shape pattern
        shape = ""
        for c in token:
            if c.isupper():
                shape += "X"
            elif c.islower():
                shape += "x"
            elif c.isdigit():
                shape += "9"
            elif c in ['-', '.', "'", ' ']:
                shape += c
            else:
                shape += "*"

        # Other features
        has_hyphen = '-' in token
        has_apostrophe = "'" in token
        has_dot = '.' in token

        return {
            "tok_hash": self.hash_token(token),
            "len": len(token),
            "script": script,
            "shape": shape,
            "has_hyphen": has_hyphen,
            "has_apostrophe": has_apostrophe,
            "has_dot": has_dot,
        }

    def redact_event(self, event: Dict) -> Dict:
        """
        脱敏单个事件 / Redact single event

        Args:
            event: 原始事件

        Returns:
            脱敏后的事件
        """
        redacted = event.copy()

        # Redact input_tokens
        if "input_tokens" in redacted and redacted["input_tokens"]:
            original_tokens = redacted["input_tokens"]

            # Replace with redacted version
            redacted["input_tokens_redacted"] = [
                self.analyze_token(tok) for tok in original_tokens
            ]

            # Remove original
            del redacted["input_tokens"]

            # Add metadata
            redacted["input_metadata"] = {
                "token_count": len(original_tokens),
                "total_length": sum(len(tok) for tok in original_tokens),
            }

        return redacted

    def sample_events(
        self,
        events: List[Dict],
        n_samples: int = 200,
    ) -> List[Dict]:
        """
        采样事件（确定性策略）/ Sample events (deterministic strategy)

        优先级 / Priority:
        1. unknown predictions (低置信度)
        2. 低score_margin (决策边界附近)
        3. 异常cases (有exception)
        4. 随机补齐 / Random fill

        Args:
            events: 所有事件
            n_samples: 采样数量

        Returns:
            采样的事件列表
        """
        # Priority 1: unknown predictions
        unknown_events = [e for e in events if e.get("prediction", {}).get("label") == "unknown"]

        # Priority 2: low margin (< 0.2) - C: handle None values
        low_margin_events = [
            e for e in events
            if e.get("score_margin") is not None and e.get("score_margin") < 0.2
        ]

        # Priority 3: exceptions
        exception_events = [e for e in events if e.get("exception") is not None]

        # Combine priority events (deduplicate by record_id_hash)
        seen = set()
        priority_events = []

        for event_list in [unknown_events, low_margin_events, exception_events]:
            for event in event_list:
                record_id = event.get("record_id_hash", "")
                if record_id and record_id not in seen:
                    priority_events.append(event)
                    seen.add(record_id)

        # If not enough, sample randomly from remaining
        if len(priority_events) < n_samples:
            remaining_events = [
                e for e in events
                if e.get("record_id_hash", "") not in seen
            ]

            # Deterministic random sample
            random.shuffle(remaining_events)
            n_fill = min(n_samples - len(priority_events), len(remaining_events))
            sampled = priority_events + remaining_events[:n_fill]
        else:
            # Take first n_samples from priority
            sampled = priority_events[:n_samples]

        return sampled

    def redact_logs(
        self,
        input_path: Path,
        output_path: Path,
        policy_path: Path,
        n_samples: int = 200,
    ):
        """
        脱敏日志文件 / Redact log file

        Args:
            input_path: 输入日志路径（完整版）
            output_path: 输出日志路径（脱敏样本）
            policy_path: 脱敏策略文档路径
            n_samples: 采样行数
        """
        print(f"\n{'='*80}")
        print(f"Log Redaction Tool")
        print(f"{'='*80}")
        print(f"Input: {input_path}")
        print(f"Output: {output_path}")
        print(f"Sample size: {n_samples}")
        print(f"")

        # Load full logs
        print(f"[Step 1/4] Loading full logs...")
        events = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        print(f"  Loaded {len(events)} events")

        # Sample events
        print(f"\n[Step 2/4] Sampling events (seed={self.seed})...")
        sampled_events = self.sample_events(events, n_samples)
        print(f"  Sampled {len(sampled_events)} events")

        # Count by category
        unknown_count = sum(1 for e in sampled_events if e.get("prediction", {}).get("label") == "unknown")
        # C: Handle None values for score_margin
        low_margin_count = sum(
            1 for e in sampled_events
            if e.get("score_margin") is not None and e.get("score_margin") < 0.2
        )
        exception_count = sum(1 for e in sampled_events if e.get("exception") is not None)

        print(f"  Categories:")
        print(f"    - Unknown: {unknown_count}")
        print(f"    - Low margin: {low_margin_count}")
        print(f"    - Exceptions: {exception_count}")
        print(f"    - Random: {len(sampled_events) - unknown_count - low_margin_count - exception_count}")

        # Redact sampled events
        print(f"\n[Step 3/4] Redacting sampled events...")
        redacted_events = [self.redact_event(e) for e in sampled_events]
        print(f"  Redacted {len(redacted_events)} events")

        # Write redacted sample
        with open(output_path, 'w', encoding='utf-8') as f:
            for event in redacted_events:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        print(f"  [OK] {output_path}")

        # Write redaction policy
        print(f"\n[Step 4/4] Writing redaction policy...")
        with open(policy_path, 'w', encoding='utf-8') as f:
            f.write("# Log Redaction Policy / 日志脱敏策略\n\n")

            f.write("## Redaction Rules / 脱敏规则\n\n")
            f.write("### Input Tokens\n\n")
            f.write("原始input_tokens字段已移除，替换为input_tokens_redacted，包含：\n")
            f.write("Original input_tokens field removed and replaced with input_tokens_redacted, containing:\n\n")
            f.write("- `tok_hash`: SHA-256(salt + normalized_token)[:16]\n")
            f.write("- `len`: Token length\n")
            f.write("- `script`: Script type (latin/cyrillic/han/mixed/other)\n")
            f.write("- `shape`: Shape pattern (X=upper, x=lower, 9=digit, *=other)\n")
            f.write("- `has_hyphen`: Boolean\n")
            f.write("- `has_apostrophe`: Boolean\n")
            f.write("- `has_dot`: Boolean\n\n")

            f.write("### Preserved Fields / 保留字段\n\n")
            f.write("以下字段完整保留（论文可解释性证据）/ Following fields fully preserved (interpretability evidence):\n\n")
            f.write("- `reasons_topk`: 决策原因和权重 / Decision reasons and weights\n")
            f.write("- `prediction`: 预测结果 / Prediction result\n")
            f.write("- `scores`: 分数分布 / Score distribution\n")
            f.write("- `score_margin`: 决策边界 / Decision margin\n")
            f.write("- `fired_modules`: 触发模块 / Fired modules\n")
            f.write("- `latency_ms`: 处理延迟 / Processing latency\n")
            f.write("- `exception`: 异常信息 / Exception info\n\n")

            f.write("### Sampling Strategy / 采样策略\n\n")
            f.write(f"- **Total events**: {len(events)}\n")
            f.write(f"- **Sample size**: {len(sampled_events)}\n")
            f.write(f"- **Sampling seed**: {self.seed}\n")
            f.write(f"- **Sampling time**: {datetime.now(timezone.utc).isoformat()}\n\n")

            f.write("**Priority categories** (in order):\n\n")
            f.write(f"1. Unknown predictions: {unknown_count} / {len(sampled_events)}\n")
            f.write(f"2. Low margin (< 0.2): {low_margin_count} / {len(sampled_events)}\n")
            f.write(f"3. Exceptions: {exception_count} / {len(sampled_events)}\n")
            f.write(f"4. Random fill: {len(sampled_events) - unknown_count - low_margin_count - exception_count} / {len(sampled_events)}\n\n")

            f.write("## Security Considerations / 安全考虑\n\n")
            f.write("⚠️ **重要 / Important**:\n\n")
            f.write("- Salt必须保密，不得公开 / Salt must be kept secret\n")
            f.write("- Token hash为单向函数，不可逆 / Token hash is one-way, irreversible\n")
            f.write("- Shape pattern仅保留结构信息，不保留内容 / Shape pattern preserves structure only, not content\n")
            f.write("- 脱敏样本可随论文提交，不泄露个人信息 / Redacted sample can be submitted with paper without leaking PII\n\n")

            f.write("## Compliance / 合规性\n\n")
            f.write("本脱敏策略按照以下要求设计 / This redaction policy is designed following:\n\n")
            f.write("- GDPR Article 25: Data Protection by Design\n")
            f.write("- GDPR Article 32: Security of Processing\n")
            f.write("- 俄罗斯联邦152-FZ法：个人数据保护 / Russian Federal Law 152-FZ: Personal Data Protection\n\n")
            f.write("**注意 / Note**: 最终合规性以机构审查为准 / Final compliance subject to institutional review\n\n")

        print(f"  [OK] {policy_path}")

        print(f"\n{'='*80}")
        print(f"Redaction completed successfully!")
        print(f"{'='*80}")


def main():
    """主函数 / Main function"""
    parser = argparse.ArgumentParser(
        description="Log Redaction Tool / 日志脱敏工具"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Full log path (e.g., logs/istina_batch_full.jsonl)"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Redacted sample output path (e.g., logs/istina_batch_redacted_200.jsonl)"
    )
    parser.add_argument(
        "--policy",
        type=str,
        required=True,
        help="Redaction policy output path (e.g., logs/istina_batch_redaction_policy.md)"
    )
    parser.add_argument(
        "--salt_env",
        type=str,
        default="ISTINA_LOG_SALT",
        help="Environment variable for salt (default: ISTINA_LOG_SALT)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)"
    )
    parser.add_argument(
        "--sample_lines",
        type=int,
        default=200,
        help="Number of lines to sample (default: 200)"
    )

    args = parser.parse_args()

    # Create redactor
    redactor = LogRedactor(
        salt_env=args.salt_env,
        seed=args.seed,
    )

    # Redact logs
    try:
        redactor.redact_logs(
            input_path=Path(args.input),
            output_path=Path(args.output),
            policy_path=Path(args.policy),
            n_samples=args.sample_lines,
        )

        print(f"\nSuccess!")

    except Exception as e:
        print(f"\n[ERROR] Redaction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
