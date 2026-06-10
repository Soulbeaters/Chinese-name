# -*- coding: utf-8 -*-
"""
验证工具 / Validation Utilities

提供N一致性检查、random seed管理、canonical hash等功能
Provides N consistency checks, random seed management, canonical hashing, etc.

作者: Ma Jiaxin
日期: 2025-12-19
"""

import json
import hashlib
import random
import numpy as np
import os
from typing import Dict, Any, List, Optional
from pathlib import Path


def set_random_seeds(seed: int = 42):
    """
    设置所有随机种子以确保可复现
    Set all random seeds for reproducibility

    Args:
        seed: Random seed value
    """
    random.seed(seed)
    np.random.seed(seed)

    # Python hash seed (需要在进程启动前设置，这里仅记录)
    os.environ.setdefault('PYTHONHASHSEED', str(seed))


def get_random_state() -> Dict[str, Any]:
    """
    获取当前随机状态
    Get current random state

    Returns:
        Dict containing random seeds and state info
    """
    return {
        "random_seed": 42,  # Default seed (应在实际运行时设置)
        "numpy_seed": 42,
        "python_hash_seed": os.environ.get('PYTHONHASHSEED', '0'),
        "random_state_available": True
    }


def compute_canonical_config_hash(config_dict: Dict) -> str:
    """
    计算配置的canonical hash (确保跨机器一致性)
    Compute canonical hash of configuration (ensures cross-machine consistency)

    使用sorted keys的JSON序列化，确保即使字典顺序不同也能得到相同hash
    Uses sorted-key JSON serialization to ensure same hash regardless of dict order

    Args:
        config_dict: Configuration dictionary

    Returns:
        SHA256 hex digest
    """
    # 转换为canonical JSON string
    canonical_json = json.dumps(
        config_dict,
        sort_keys=True,      # 关键：排序所有键
        ensure_ascii=False,  # 保持Unicode字符
        separators=(',', ':')  # 去除空格以确保一致性
    )

    # 计算SHA256
    hash_obj = hashlib.sha256(canonical_json.encode('utf-8'))
    return hash_obj.hexdigest()


def validate_n_consistency(
    n_records_total: int,
    n_records_labeled: int,
    stats_ci: Dict,
    module_coverage: Dict,
    run_manifest: Dict,
    strict: bool = True
) -> List[str]:
    """
    验证所有输出中的N值一致性
    Validate N consistency across all outputs

    Args:
        n_records_total: Total number of records
        n_records_labeled: Number of labeled records (used in k/n)
        stats_ci: stats_ci dictionary
        module_coverage: module_coverage dictionary
        run_manifest: run_manifest dictionary
        strict: If True, raise ValueError on inconsistency; if False, return warnings

    Returns:
        List of warnings/errors

    Raises:
        ValueError: If strict=True and inconsistencies found
    """
    errors = []
    warnings = []

    # 1. Check run_manifest
    if "n_records_total" in run_manifest:
        if run_manifest["n_records_total"] != n_records_total:
            errors.append(
                f"run_manifest.n_records_total ({run_manifest['n_records_total']}) != "
                f"expected ({n_records_total})"
            )

    if "n_records_labeled" in run_manifest:
        if run_manifest["n_records_labeled"] != n_records_labeled:
            errors.append(
                f"run_manifest.n_records_labeled ({run_manifest['n_records_labeled']}) != "
                f"expected ({n_records_labeled})"
            )

    # 2. Check stats_ci metadata
    if "metadata" in stats_ci:
        metadata = stats_ci["metadata"]

        if "n_records_total" in metadata:
            if metadata["n_records_total"] != n_records_total:
                errors.append(
                    f"stats_ci.metadata.n_records_total ({metadata['n_records_total']}) != "
                    f"expected ({n_records_total})"
                )

        if "n_records_labeled" in metadata:
            if metadata["n_records_labeled"] != n_records_labeled:
                errors.append(
                    f"stats_ci.metadata.n_records_labeled ({metadata['n_records_labeled']}) != "
                    f"expected ({n_records_labeled})"
                )

        # CRITICAL: Check CI's n values
        # - end_to_end_accuracy.n MUST equal n_records_labeled (unknown counted as error)
        # - conditional_accuracy.n MUST be <= n_records_labeled (unknown excluded)
        # - coverage.n MUST equal n_records_labeled
        # - accuracy.n (legacy) MUST equal n_records_labeled
        for config_name, cis in stats_ci.get("confidence_intervals", {}).items():
            for metric_name, ci in cis.items():
                if "n" in ci:
                    # P1-3: conditional_accuracy excludes unknown, so n <= n_records_labeled is OK
                    if metric_name == "conditional_accuracy":
                        if ci["n"] > n_records_labeled:
                            errors.append(
                                f"stats_ci[{config_name}][{metric_name}].n ({ci['n']}) > "
                                f"n_records_labeled ({n_records_labeled}) - conditional_accuracy.n should be <= n_labeled"
                            )
                    else:
                        # All other metrics: n must equal n_records_labeled
                        if ci["n"] != n_records_labeled:
                            errors.append(
                                f"stats_ci[{config_name}][{metric_name}].n ({ci['n']}) != "
                                f"n_records_labeled ({n_records_labeled})"
                            )

    # 3. Check module_coverage
    if "n_records_total" in module_coverage:
        if module_coverage["n_records_total"] != n_records_total:
            errors.append(
                f"module_coverage.n_records_total ({module_coverage['n_records_total']}) != "
                f"expected ({n_records_total})"
            )

    if "n_records_labeled" in module_coverage:
        if module_coverage["n_records_labeled"] != n_records_labeled:
            errors.append(
                f"module_coverage.n_records_labeled ({module_coverage['n_records_labeled']}) != "
                f"expected ({n_records_labeled})"
            )

    # Report
    if errors:
        error_msg = "\n[N CONSISTENCY VALIDATION FAILED]\n" + "\n".join(f"  - {e}" for e in errors)
        if strict:
            raise ValueError(error_msg)
        else:
            warnings.append(error_msg)

    return warnings if not strict else []


def check_git_clean() -> Dict[str, Any]:
    """
    检查Git工作区是否clean
    Check if Git working directory is clean

    Returns:
        Dict with is_dirty, uncommitted_files, and patch (if dirty)
    """
    import subprocess

    try:
        # Check if there are uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )

        uncommitted = result.stdout.strip()
        is_dirty = len(uncommitted) > 0

        uncommitted_files = []
        if is_dirty:
            uncommitted_files = [line.strip() for line in uncommitted.split('\n') if line.strip()]

        # Get diff if dirty
        patch = ""
        if is_dirty:
            diff_result = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10
            )
            patch = diff_result.stdout

        return {
            "is_dirty": is_dirty,
            "uncommitted_files": uncommitted_files,
            "patch": patch if is_dirty else None
        }

    except Exception as e:
        return {
            "is_dirty": None,
            "error": str(e)
        }


def generate_extended_manifest(
    base_manifest: Dict,
    configs_dict: Dict,
    sampling_params: Dict[str, Any],
    run_dir: Optional[str] = None
) -> Dict:
    """
    生成扩展的run_manifest,包含随机性、hash、Git状态等
    Generate extended run_manifest with randomness, hash, Git status, etc.

    Args:
        base_manifest: Basic manifest dict
        configs_dict: Ablation configs dictionary
        sampling_params: Sampling strategy parameters
        run_dir: Run directory path (for saving git patch file)

    Returns:
        Extended manifest dict
    """
    # Compute canonical config hash
    config_hash = compute_canonical_config_hash(configs_dict)

    # Get random state
    random_state = get_random_state()

    # Check Git status
    git_clean_status = check_git_clean()

    # Extend manifest
    extended = base_manifest.copy()

    # Rename fields for clarity
    if "dataset_size" in extended:
        extended["n_records_total"] = extended.pop("dataset_size")

    if "ground_truth_size" in extended:
        extended["n_records_labeled"] = extended.pop("ground_truth_size")

    # Add reproducibility section
    extended["reproducibility"] = {
        "random_seed": random_state["random_seed"],
        "numpy_seed": random_state["numpy_seed"],
        "python_hash_seed": random_state["python_hash_seed"],
        "sampling_params": sampling_params,
        "config_hash": config_hash,
        "config_hash_method": "sha256(json.dumps(config, sort_keys=True, separators=(',',':')))"
    }

    # Add Git clean status
    if "git_info" in extended:
        extended["git_info"]["is_dirty"] = git_clean_status.get("is_dirty")
        extended["git_info"]["uncommitted_files"] = git_clean_status.get("uncommitted_files", [])

        # P1-4: Save patch to file if dirty
        if git_clean_status.get("is_dirty") and git_clean_status.get("patch") and run_dir:
            patch_content = git_clean_status["patch"]

            # Save to file
            patch_file_path = Path(run_dir) / "git_dirty.patch"
            try:
                with open(patch_file_path, 'w', encoding='utf-8') as f:
                    f.write(patch_content)

                # Compute SHA256 of patch
                patch_sha256 = hashlib.sha256(patch_content.encode('utf-8')).hexdigest()

                # Record in manifest
                extended["git_info"]["patch_file"] = "git_dirty.patch"  # Relative path
                extended["git_info"]["patch_sha256"] = patch_sha256
                extended["git_info"]["patch_size_bytes"] = len(patch_content.encode('utf-8'))

                # Remove inline patch from json (too large)
                if "patch" in extended["git_info"]:
                    del extended["git_info"]["patch"]

            except Exception as e:
                # Fallback: save inline if file write fails
                if len(git_clean_status["patch"]) < 50000:
                    extended["git_info"]["patch"] = git_clean_status["patch"]
                    extended["git_info"]["patch_file_error"] = str(e)
        elif git_clean_status.get("patch") and len(git_clean_status["patch"]) < 50000:
            # No run_dir provided, save inline for backward compatibility
            extended["git_info"]["patch"] = git_clean_status["patch"]

    return extended
