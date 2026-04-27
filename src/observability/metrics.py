"""
可观测性 - 指标收集模块

提供性能指标收集和统计
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import time


@dataclass
class MetricPoint:
    """指标点"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricStats:
    """指标统计"""
    name: str
    count: int = 0
    total: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    avg: float = 0.0
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0

    def update(self, value: float) -> None:
        """更新统计"""
        self.count += 1
        self.total += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.avg = self.total / self.count

    def calculate_percentiles(self, values: List[float]) -> None:
        """计算百分位数"""
        if not values:
            return

        sorted_values = sorted(values)
        n = len(sorted_values)

        self.p50 = sorted_values[int(n * 0.5)] if n > 0 else 0
        self.p95 = sorted_values[int(n * 0.95)] if n > 0 else 0
        self.p99 = sorted_values[int(n * 0.99)] if n > 0 else 0


class MetricsCollector:
    """
    指标收集器

    收集和统计各种性能指标
    """

    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._metric_points: List[MetricPoint] = []

    def increment(self, name: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        """
        增加计数器

        Args:
            name: 指标名称
            value: 增量值
            tags: 标签
        """
        key = self._make_key(name, tags)
        self._counters[key] += value

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """
        设置仪表盘值

        Args:
            name: 指标名称
            value: 值
            tags: 标签
        """
        key = self._make_key(name, tags)
        self._gauges[key] = value

    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Dict[str, str] = None
    ) -> None:
        """
        记录直方图值

        Args:
            name: 指标名称
            value: 值
            tags: 标签
        """
        key = self._make_key(name, tags)
        self._histograms[key].append(value)

        # 保留最近 1000 个值
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]

    def record_metric_point(
        self,
        name: str,
        value: float,
        tags: Dict[str, str] = None
    ) -> None:
        """记录指标点"""
        point = MetricPoint(
            name=name,
            value=value,
            tags=tags or {}
        )
        self._metric_points.append(point)

        # 保留最近 10000 个点
        if len(self._metric_points) > 10000:
            self._metric_points = self._metric_points[-10000:]

    def get_counter(self, name: str, tags: Dict[str, str] = None) -> int:
        """获取计数器值"""
        key = self._make_key(name, tags)
        return self._counters.get(key, 0)

    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        """获取仪表盘值"""
        key = self._make_key(name, tags)
        return self._gauges.get(key)

    def get_histogram_stats(
        self,
        name: str,
        tags: Dict[str, str] = None
    ) -> Optional[MetricStats]:
        """获取直方图统计"""
        key = self._make_key(name, tags)
        values = self._histograms.get(key)

        if not values:
            return None

        stats = MetricStats(name=name)
        stats.count = len(values)

        for v in values:
            stats.update(v)

        stats.calculate_percentiles(values)

        return stats

    def get_all_metrics(self) -> Dict[str, Dict]:
        """获取所有指标"""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                key: {
                    "count": len(values),
                    "avg": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0
                }
                for key, values in self._histograms.items()
            }
        }

    def reset(self) -> None:
        """重置所有指标"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._metric_points.clear()

    def _make_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        """生成指标键"""
        if not tags:
            return name

        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}@{tag_str}"

    # 常用指标的便捷方法
    def record_llm_call(self, model: str, tokens: int, duration: float) -> None:
        """记录 LLM 调用"""
        self.increment("llm_calls_total", tags={"model": model})
        self.increment("llm_tokens_total", tokens, tags={"model": model})
        self.record_histogram("llm_duration_seconds", duration, tags={"model": model})

    def record_tool_call(self, tool_name: str, duration: float, success: bool) -> None:
        """记录工具调用"""
        self.increment("tool_calls_total", tags={"tool": tool_name, "status": "success" if success else "error"})
        self.record_histogram("tool_duration_seconds", duration, tags={"tool": tool_name})

    def record_agent_execution(
        self,
        success: bool,
        duration: float,
        iterations: int,
        llm_calls: int,
        tool_calls: int
    ) -> None:
        """记录 Agent 执行"""
        self.increment(
            "agent_executions_total",
            tags={"status": "success" if success else "error"}
        )
        self.record_histogram("agent_duration_seconds", duration)
        self.record_histogram("agent_iterations", iterations)
        self.record_histogram("agent_llm_calls", llm_calls)
        self.record_histogram("agent_tool_calls", tool_calls)


# 全局实例
_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
