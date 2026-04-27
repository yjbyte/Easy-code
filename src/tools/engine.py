"""
Function Calling Engine - 主引擎
"""
from typing import List, Optional, Any
from uuid import uuid4

from src.tools.models import (
    Tool,
    ToolCategory,
    FunctionCall,
    FunctionResult,
    ExecutionPlan
)
from src.tools.registry import FunctionRegistry, get_function_registry
from src.tools.executor import ExecutionEngine
from src.tools.planner import CallingPlanner


class FunctionCallingEngine:
    """
    Function Calling 引擎

    负责工具注册、调用规划和执行管理
    """

    def __init__(self, registry: Optional[FunctionRegistry] = None):
        self.registry = registry or get_function_registry()
        self.planner = CallingPlanner(self.registry)
        self.executor = ExecutionEngine(self.registry)

    def register_tool(self, tool: Tool) -> None:
        """
        注册工具

        Args:
            tool: 工具定义
        """
        self.registry.register(tool)

    def register_tools(self, tools: List[Tool]) -> None:
        """
        批量注册工具

        Args:
            tools: 工具列表
        """
        for tool in tools:
            self.register_tool(tool)

    def unregister_tool(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            是否成功
        """
        return self.registry.unregister(name)

    def list_tools(
        self,
        category: Optional[ToolCategory] = None
    ) -> List[Tool]:
        """
        列出工具

        Args:
            category: 工具分类筛选

        Returns:
            工具列表
        """
        return self.registry.list(category)

    async def call(
        self,
        tool_name: str,
        parameters: dict,
        timeout: Optional[int] = None
    ) -> Any:
        """
        调用单个工具

        Args:
            tool_name: 工具名称
            parameters: 调用参数
            timeout: 超时时间（秒）

        Returns:
            工具执行结果

        Raises:
            ToolNotFoundError: 工具不存在
            ParameterValidationError: 参数验证失败
            ExecutionTimeoutError: 执行超时
            ExecutionFailedError: 执行失败
        """
        tool = self.registry.get_or_raise(tool_name)

        # 验证参数
        self.executor._validate_parameters(tool, parameters)

        # 执行
        call = FunctionCall(
            call_id=str(uuid4()),
            tool_name=tool_name,
            parameters=parameters
        )

        result = await self.executor.execute_single(call)

        if not result.success:
            if "timeout" in result.error.lower():
                from src.tools.errors import ExecutionTimeoutError
                raise ExecutionTimeoutError(result.error, timeout or tool.timeout)
            else:
                from src.tools.errors import ExecutionFailedError
                raise ExecutionFailedError(result.error)

        return result.result

    async def execute_plan(
        self,
        plan: ExecutionPlan
    ) -> List[FunctionResult]:
        """
        执行计划

        Args:
            plan: 执行计划

        Returns:
            执行结果列表
        """
        return await self.executor.execute(plan)

    async def execute_batch(
        self,
        calls: List[dict]
    ) -> List[FunctionResult]:
        """
        批量执行工具调用

        Args:
            calls: 调用列表，格式: [{"tool_name": "...", "parameters": {...}}, ...]

        Returns:
            执行结果列表
        """
        # 转换为 FunctionCall
        function_calls = []
        for call in calls:
            function_calls.append(FunctionCall(
                tool_name=call["tool_name"],
                parameters=call.get("parameters", {}),
                depends_on=call.get("depends_on", [])
            ))

        # 创建执行计划
        plan = self.planner.plan_calls(function_calls)

        # 执行
        return await self.execute_plan(plan)

    def to_openai_format(self) -> List[dict]:
        """
        转换为 OpenAI Function Calling 格式

        Returns:
            OpenAI 格式的工具列表
        """
        return self.registry.to_openai_format()

    def find_tools_by_capability(self, capability: str) -> List[Tool]:
        """
        按能力查找工具

        Args:
            capability: 能力关键词

        Returns:
            匹配的工具列表
        """
        return self.registry.find_by_capability(capability)

    def get_tool_count(self) -> int:
        """获取工具总数"""
        return self.registry.count()


# 全局引擎实例
_global_engine: Optional[FunctionCallingEngine] = None


def get_function_calling_engine() -> FunctionCallingEngine:
    """获取全局 Function Calling 引擎"""
    global _global_engine
    if _global_engine is None:
        _global_engine = FunctionCallingEngine()
    return _global_engine
