"""
可观测性 - 追踪模块

提供全链路追踪功能
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from enum import Enum


class StepType(str, Enum):
    """步骤类型"""
    USER = "user"
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    ANSWER = "answer"
    PARTIAL_ANSWER = "partial_answer"
    ERROR = "error"


@dataclass
class TraceStep:
    """追踪步骤"""
    step_type: StepType
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None


@dataclass
class ExecutionTrace:
    """执行追踪"""
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    query: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    steps: List[TraceStep] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    # 性能指标
    llm_calls: int = 0
    tool_calls: int = 0
    tokens_used: int = 0
    iterations: int = 0

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(
        self,
        step_type: StepType,
        content: str,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """添加步骤"""
        step = TraceStep(
            step_type=step_type,
            content=content,
            data=data,
            duration_ms=duration_ms
        )
        self.steps.append(step)

    def finish(self, success: bool = True, error: Optional[str] = None) -> None:
        """结束追踪"""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.success = success
        self.error = error

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        step_counts = {}
        for step in self.steps:
            step_counts[step.step_type] = step_counts.get(step.step_type, 0) + 1

        return {
            "execution_id": self.execution_id,
            "query": self.query,
            "duration": self.duration,
            "success": self.success,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "tokens_used": self.tokens_used,
            "iterations": self.iterations,
            "step_counts": step_counts,
            "error": self.error
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "query": self.query,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "steps": [
                {
                    "step_type": s.step_type,
                    "content": s.content,
                    "timestamp": s.timestamp.isoformat(),
                    "data": s.data,
                    "duration_ms": s.duration_ms
                }
                for s in self.steps
            ],
            "success": self.success,
            "error": self.error,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "tokens_used": self.tokens_used,
            "iterations": self.iterations,
            "metadata": self.metadata
        }


class TraceRecorder:
    """
    追踪记录器

    负责创建和管理 ExecutionTrace
    """

    def __init__(self):
        self._traces: Dict[str, ExecutionTrace] = {}

    def create_trace(self, query: str) -> ExecutionTrace:
        """创建新的追踪"""
        trace = ExecutionTrace(query=query)
        self._traces[trace.execution_id] = trace
        return trace

    def get_trace(self, execution_id: str) -> Optional[ExecutionTrace]:
        """获取追踪"""
        return self._traces.get(execution_id)

    def list_traces(
        self,
        limit: int = 100,
        success_only: bool = False
    ) -> List[ExecutionTrace]:
        """列出追踪"""
        traces = list(self._traces.values())

        if success_only:
            traces = [t for t in traces if t.success]

        # 按时间倒序
        traces.sort(key=lambda t: t.start_time, reverse=True)

        return traces[:limit]

    def delete_trace(self, execution_id: str) -> bool:
        """删除追踪"""
        if execution_id in self._traces:
            del self._traces[execution_id]
            return True
        return False

    def clear(self) -> None:
        """清空所有追踪"""
        self._traces.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        traces = list(self._traces.values())

        if not traces:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "avg_duration": 0,
                "avg_llm_calls": 0,
                "avg_tool_calls": 0
            }

        success_traces = [t for t in traces if t.success]
        failed_traces = [t for t in traces if not t.success]

        return {
            "total": len(traces),
            "success": len(success_traces),
            "failed": len(failed_traces),
            "avg_duration": sum(t.duration or 0 for t in traces) / len(traces),
            "avg_llm_calls": sum(t.llm_calls for t in traces) / len(traces),
            "avg_tool_calls": sum(t.tool_calls for t in traces) / len(traces)
        }


# 全局实例
_global_recorder: Optional[TraceRecorder] = None


def get_trace_recorder() -> TraceRecorder:
    """获取全局追踪记录器"""
    global _global_recorder
    if _global_recorder is None:
        _global_recorder = TraceRecorder()
    return _global_recorder
