# -*- coding: utf-8 -*-
"""
性能测量模块 / Performance Metrics Module

用于测量算法的性能指标：wall time, CPU time, 内存使用
Measures algorithm performance metrics: wall time, CPU time, memory usage

作者: Ma Jiaxin
日期: 2025-12-19
"""

import time
import platform
from dataclasses import dataclass, asdict
from typing import Callable, Any, Optional
import sys

# 跨平台资源监控 / Cross-platform resource monitoring
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class PerformanceMetrics:
    """
    性能指标数据结构 / Performance metrics data structure
    """
    # 时间指标 / Time metrics
    wall_time_s: float         # 墙上时钟时间（秒）/ Wall clock time
    cpu_user_s: float          # 用户态CPU时间（秒）/ User CPU time
    cpu_sys_s: float           # 系统态CPU时间（秒）/ System CPU time

    # 内存指标 / Memory metrics
    peak_rss_mb: float         # 峰值常驻集大小（MB）/ Peak resident set size

    # 吞吐量指标 / Throughput metrics
    n_records: int = 0         # 处理记录数 / Number of records processed
    names_per_sec: float = 0.0 # 每秒处理姓名数 / Names processed per second

    def to_dict(self) -> dict:
        """转换为字典 / Convert to dictionary"""
        return asdict(self)


class PerformanceMonitor:
    """
    性能监控器 / Performance Monitor

    支持跨平台的性能测量，包括 Windows 和 Linux
    Supports cross-platform performance measurement including Windows and Linux
    """

    def __init__(self):
        """初始化性能监控器 / Initialize performance monitor"""
        self.start_wall_time = 0.0
        self.start_cpu_user = 0.0
        self.start_cpu_sys = 0.0
        self.start_rss_mb = 0.0

        self.end_wall_time = 0.0
        self.end_cpu_user = 0.0
        self.end_cpu_sys = 0.0
        self.end_rss_mb = 0.0

        self.n_records = 0
        self.is_windows = platform.system() == 'Windows'

    def start(self) -> None:
        """开始监控 / Start monitoring"""
        # Wall time / 墙上时钟时间
        self.start_wall_time = time.perf_counter()

        # CPU time / CPU时间
        if HAS_RESOURCE and not self.is_windows:
            # Linux/Unix: 使用 resource 模块
            usage = resource.getrusage(resource.RUSAGE_SELF)
            self.start_cpu_user = usage.ru_utime
            self.start_cpu_sys = usage.ru_stime
        elif HAS_PSUTIL:
            # Windows 或有 psutil: 使用 psutil
            p = psutil.Process()
            cpu_times = p.cpu_times()
            self.start_cpu_user = cpu_times.user
            self.start_cpu_sys = cpu_times.system
        else:
            # 无资源监控：设为0
            self.start_cpu_user = 0.0
            self.start_cpu_sys = 0.0

        # Memory / 内存
        if HAS_PSUTIL:
            p = psutil.Process()
            self.start_rss_mb = p.memory_info().rss / (1024 * 1024)
        else:
            self.start_rss_mb = 0.0

    def stop(self, n_records: int = 0) -> PerformanceMetrics:
        """
        停止监控并返回性能指标 / Stop monitoring and return metrics

        Args:
            n_records: 处理的记录数 / Number of records processed

        Returns:
            PerformanceMetrics 对象
        """
        self.n_records = n_records

        # Wall time / 墙上时钟时间
        self.end_wall_time = time.perf_counter()

        # CPU time / CPU时间
        if HAS_RESOURCE and not self.is_windows:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            self.end_cpu_user = usage.ru_utime
            self.end_cpu_sys = usage.ru_stime
        elif HAS_PSUTIL:
            p = psutil.Process()
            cpu_times = p.cpu_times()
            self.end_cpu_user = cpu_times.user
            self.end_cpu_sys = cpu_times.system
        else:
            self.end_cpu_user = 0.0
            self.end_cpu_sys = 0.0

        # Memory / 内存
        if HAS_PSUTIL:
            p = psutil.Process()
            self.end_rss_mb = p.memory_info().rss / (1024 * 1024)
        else:
            self.end_rss_mb = 0.0

        # 计算差值 / Calculate deltas
        wall_time_s = self.end_wall_time - self.start_wall_time
        cpu_user_s = self.end_cpu_user - self.start_cpu_user
        cpu_sys_s = self.end_cpu_sys - self.start_cpu_sys
        peak_rss_mb = max(self.end_rss_mb, self.start_rss_mb)

        # 计算吞吐量 / Calculate throughput
        names_per_sec = n_records / wall_time_s if wall_time_s > 0 else 0.0

        return PerformanceMetrics(
            wall_time_s=wall_time_s,
            cpu_user_s=cpu_user_s,
            cpu_sys_s=cpu_sys_s,
            peak_rss_mb=peak_rss_mb,
            n_records=n_records,
            names_per_sec=names_per_sec
        )


def measure_performance(
    func: Callable,
    *args,
    n_records: int = 0,
    **kwargs
) -> tuple[Any, PerformanceMetrics]:
    """
    测量函数性能 / Measure function performance

    Args:
        func: 要测量的函数 / Function to measure
        *args: 函数位置参数 / Function positional arguments
        n_records: 处理的记录数 / Number of records
        **kwargs: 函数关键字参数 / Function keyword arguments

    Returns:
        (函数返回值, 性能指标) / (function result, performance metrics)
    """
    monitor = PerformanceMonitor()
    monitor.start()

    result = func(*args, **kwargs)

    metrics = monitor.stop(n_records=n_records)

    return result, metrics


def get_system_info() -> dict:
    """
    获取系统信息 / Get system information

    Returns:
        包含系统信息的字典 / Dictionary with system information
    """
    info = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
    }

    # CPU 信息 / CPU information
    if HAS_PSUTIL:
        info["cpu_count"] = psutil.cpu_count(logical=False)
        info["cpu_count_logical"] = psutil.cpu_count(logical=True)
        try:
            # 尝试获取 CPU 型号（不是所有平台都支持）
            info["cpu_model"] = platform.processor()
        except:
            info["cpu_model"] = "unknown"

        # RAM 信息 / RAM information
        mem = psutil.virtual_memory()
        info["ram_total_gb"] = round(mem.total / (1024**3), 2)
    else:
        info["cpu_count"] = "unknown"
        info["cpu_count_logical"] = "unknown"
        info["cpu_model"] = platform.processor()
        info["ram_total_gb"] = "unknown"

    return info


if __name__ == "__main__":
    # 测试示例 / Test example
    print("系统信息 / System Information:")
    import json
    print(json.dumps(get_system_info(), indent=2, ensure_ascii=False))

    print("\n性能测量测试 / Performance measurement test:")

    def test_func(n):
        """测试函数 / Test function"""
        return sum(range(n))

    result, metrics = measure_performance(test_func, 1000000, n_records=1000000)
    print(f"结果 / Result: {result}")
    print(f"性能指标 / Metrics:")
    print(json.dumps(metrics.to_dict(), indent=2))
