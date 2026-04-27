"""
Execution Engine - 执行引擎
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.tools.models import (
    Tool,
    FunctionCall,
    FunctionResult,
    ExecutionPlan
)
from src.tools.registry import FunctionRegistry
from src.tools.errors import (
    ToolNotFoundError,
    ParameterValidationError,
    ExecutionTimeoutError,
    ExecutionFailedError
)


class ExecutionEngine:
    """执行引擎 - 负责执行函数调用"""

    def __init__(self, registry: FunctionRegistry):
        self.registry = registry

    async def execute(
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
        if plan.execution_mode == "parallel":
            return await self._execute_parallel(plan.calls)
        elif plan.execution_mode == "sequential":
            return await self._execute_sequential(plan.calls)
        else:  # auto
            return await self._execute_auto(plan.calls)

    async def execute_single(
        self,
        call: FunctionCall
    ) -> FunctionResult:
        """
        执行单个调用

        Args:
            call: 函数调用

        Returns:
            执行结果
        """
        if not call.call_id:
            call.call_id = str(uuid.uuid4())

        start_time = datetime.now()
        tool = None

        try:
            # 获取工具
            tool = self.registry.get_or_raise(call.tool_name)

            # 验证参数
            self._validate_parameters(tool, call.parameters)

            # 执行（带超时）
            timeout = tool.timeout
            result = await asyncio.wait_for(
                tool.execute(**call.parameters),
                timeout=timeout
            )

            # 计算执行时长
            duration = (datetime.now() - start_time).total_seconds()

            return FunctionResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=True,
                result=result,
                duration=duration
            )

        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            return FunctionResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Execution timeout after {duration}s",
                duration=duration
            )

        except ToolNotFoundError as e:
            duration = (datetime.now() - start_time).total_seconds()
            return FunctionResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=str(e),
                duration=duration
            )

        except ParameterValidationError as e:
            duration = (datetime.now() - start_time).total_seconds()
            return FunctionResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Parameter validation failed: {e.message}",
                duration=duration
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return FunctionResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Execution failed: {str(e)}",
                duration=duration
            )

    async def _execute_parallel(
        self,
        calls: List[FunctionCall]
    ) -> List[FunctionResult]:
        """并行执行"""
        tasks = [self.execute_single(call) for call in calls]
        return await asyncio.gather(*tasks)

    async def _execute_sequential(
        self,
        calls: List[FunctionCall]
    ) -> List[FunctionResult]:
        """串行执行"""
        results = []
        for call in calls:
            result = await self.execute_single(call)
            results.append(result)

            # 如果失败且后续调用依赖它，停止执行
            if not result.success:
                # 检查是否有后续调用依赖这个失败的调用
                has_dependents = any(
                    call.call_id in other.depends_on
                    for other in calls
                )
                if has_dependents:
                    break

        return results

    async def _execute_auto(
        self,
        calls: List[FunctionCall]
    ) -> List[FunctionResult]:
        """自动选择执行策略"""
        # 分析依赖关系
        dependency_map = self._build_dependency_map(calls)

        # 如果没有依赖关系，并行执行
        if not any(dependency_map.values()):
            return await self._execute_parallel(calls)

        # 有依赖关系，按批次执行
        return await self._execute_in_batches(calls, dependency_map)

    async def _execute_in_batches(
        self,
        calls: List[FunctionCall],
        dependency_map: Dict[str, List[str]]
    ) -> List[FunctionResult]:
        """按批次执行（有依赖关系的）"""
        results = {}
        remaining_calls = {call.call_id: call for call in calls}

        while remaining_calls:
            # 找出可以并行执行的调用（所有依赖都已满足）
            ready_calls = []
            for call_id, call in remaining_calls.items():
                dependencies = dependency_map.get(call_id, [])
                dependencies_met = all(
                    dep in results and results[dep].success
                    for dep in dependencies
                )
                if dependencies_met:
                    ready_calls.append(call)

            if not ready_calls:
                # 循环依赖或无法继续
                break

            # 并行执行当前批次
            batch_results = await self._execute_parallel(ready_calls)
            for result in batch_results:
                results[result.call_id] = result
                remaining_calls.pop(result.call_id, None)

        # 按原始顺序返回结果
        ordered_results = [
            results[call.call_id]
            for call in calls
            if call.call_id in results
        ]
        return ordered_results

    def _build_dependency_map(
        self,
        calls: List[FunctionCall]
    ) -> Dict[str, List[str]]:
        """构建依赖关系图"""
        return {
            call.call_id: call.depends_on
            for call in calls
            if call.depends_on
        }

    def _validate_parameters(
        self,
        tool: Tool,
        parameters: Dict[str, Any]
    ) -> None:
        """
        验证参数

        Args:
            tool: 工具定义
            parameters: 调用参数

        Raises:
            ParameterValidationError: 参数验证失败
        """
        # 检查必需参数
        required_params = {p.name for p in tool.parameters if p.required}
        provided_params = set(parameters.keys())

        missing_params = required_params - provided_params
        if missing_params:
            raise ParameterValidationError(
                f"Missing required parameters: {', '.join(missing_params)}",
                parameter=list(missing_params)[0] if missing_params else None
            )

        # 检查参数类型（基础验证）
        for param in tool.parameters:
            if param.name in parameters:
                value = parameters[param.name]

                # 枚举值检查
                if param.enum and value not in param.enum:
                    raise ParameterValidationError(
                        f"Parameter '{param.name}' must be one of {param.enum}, got '{value}'",
                        parameter=param.name
                    )

                # 类型检查（基础）
                if param.type == "integer" and not isinstance(value, int):
                    raise ParameterValidationError(
                        f"Parameter '{param.name}' must be integer, got {type(value).__name__}",
                        parameter=param.name
                    )
                elif param.type == "boolean" and not isinstance(value, bool):
                    raise ParameterValidationError(
                        f"Parameter '{param.name}' must be boolean, got {type(value).__name__}",
                        parameter=param.name
                    )
                elif param.type == "array" and not isinstance(value, list):
                    raise ParameterValidationError(
                        f"Parameter '{param.name}' must be array, got {type(value).__name__}",
                        parameter=param.name
                    )
                elif param.type == "object" and not isinstance(value, dict):
                    raise ParameterValidationError(
                        f"Parameter '{param.name}' must be object, got {type(value).__name__}",
                        parameter=param.name
                    )
