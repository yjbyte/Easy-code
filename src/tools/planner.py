"""
Calling Planner - 调用规划器
"""
from typing import List, Optional

from src.tools.models import (
    FunctionCall,
    ExecutionPlan,
    Tool
)
from src.tools.registry import FunctionRegistry


class CallingPlanner:
    """调用规划器 - 分析和规划函数调用"""

    def __init__(self, registry: FunctionRegistry):
        self.registry = registry

    def plan_calls(
        self,
        calls: List[FunctionCall],
        mode: str = "auto"
    ) -> ExecutionPlan:
        """
        规划调用执行

        Args:
            calls: 函数调用列表
            mode: 执行模式 (auto/parallel/sequential)

        Returns:
            执行计划
        """
        # 为调用分配 ID
        for call in calls:
            if not call.call_id:
                from uuid import uuid4
                call.call_id = str(uuid4())

        # 分析依赖关系
        if mode == "auto":
            mode = self._determine_execution_mode(calls)

        # 估算执行时长
        estimated_duration = self._estimate_duration(calls)

        return ExecutionPlan(
            calls=calls,
            execution_mode=mode,
            estimated_duration=estimated_duration
        )

    def plan_from_tool_calls(
        self,
        tool_calls: List[dict]
    ) -> ExecutionPlan:
        """
        从 LLM 返回的 tool_calls 规划执行

        Args:
            tool_calls: LLM 返回的工具调用列表

        Returns:
            执行计划
        """
        calls = []
        for tool_call in tool_calls:
            call = FunctionCall(
                tool_name=tool_call.get("name", ""),
                parameters=tool_call.get("arguments", {})
            )
            calls.append(call)

        return self.plan_calls(calls)

    def _determine_execution_mode(self, calls: List[FunctionCall]) -> str:
        """
        确定执行模式

        Args:
            calls: 函数调用列表

        Returns:
            执行模式: parallel 或 sequential
        """
        # 检查是否有依赖关系
        has_dependencies = any(call.depends_on for call in calls)
        if has_dependencies:
            return "sequential"

        # 检查是否有状态依赖的工具
        for call in calls:
            tool = self.registry.get(call.tool_name)
            if tool:
                # 标记为非幂等的工具需要串行执行
                if not tool.metadata.get("idempotent", True):
                    return "sequential"

        # 默认并行执行
        return "parallel"

    def _estimate_duration(self, calls: List[FunctionCall]) -> float:
        """
        估算执行时长

        Args:
            calls: 函数调用列表

        Returns:
            预计时长（秒）
        """
        total_duration = 0.0

        for call in calls:
            tool = self.registry.get(call.tool_name)
            if tool:
                # 使用工具的典型时长或默认超时
                typical_duration = tool.metadata.get("typical_duration", tool.timeout / 2)
                total_duration += typical_duration
            else:
                total_duration += 10.0  # 默认估算

        return total_duration
