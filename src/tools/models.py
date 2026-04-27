"""
Function Calling 核心数据模型
"""
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class ToolCategory(str, Enum):
    """工具分类"""
    GRAPH_RAG = "graph_rag"       # GraphRAG 引擎
    MCP = "mcp"                   # MCP 协议
    BUILTIN = "builtin"           # 内置工具
    CUSTOM = "custom"             # 自定义工具


class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型: string/integer/boolean/array/object")
    description: str = Field(..., description="参数描述")
    required: bool = Field(default=False, description="是否必需")
    default: Optional[Any] = Field(default=None, description="默认值")
    enum: Optional[List[Any]] = Field(default=None, description="枚举值")


class Tool(BaseModel):
    """工具定义"""
    name: str = Field(..., description="工具名称，唯一标识")
    description: str = Field(..., description="工具功能描述")
    category: ToolCategory = Field(default=ToolCategory.BUILTIN, description="工具分类")
    parameters: List[ToolParameter] = Field(default_factory=list, description="参数列表")
    async_mode: bool = Field(default=False, description="是否异步执行")
    timeout: int = Field(default=30, description="超时时间（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    # 函数引用不参与序列化
    class Config:
        arbitrary_types_allowed = True

    # 内部存储函数引用
    _function: Optional[Callable] = None

    def set_function(self, func: Callable) -> None:
        """设置执行函数"""
        self._function = func

    def get_function(self) -> Callable:
        """获取执行函数"""
        if self._function is None:
            raise RuntimeError(f"Tool {self.name} has no function set")
        return self._function

    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        func = self.get_function()
        if self.async_mode:
            return await func(**kwargs)
        else:
            return func(**kwargs)


class FunctionCall(BaseModel):
    """函数调用请求"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="调用参数")
    call_id: Optional[str] = Field(default=None, description="调用ID")
    depends_on: List[str] = Field(default_factory=list, description="依赖的调用ID")


class FunctionResult(BaseModel):
    """函数调用结果"""
    call_id: str = Field(..., description="调用ID")
    tool_name: str = Field(..., description="工具名称")
    success: bool = Field(..., description="是否成功")
    result: Optional[Any] = Field(default=None, description="返回结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    duration: float = Field(default=0, description="执行时长（秒）")


class ExecutionPlan(BaseModel):
    """执行计划"""
    calls: List[FunctionCall] = Field(default_factory=list, description="调用列表")
    execution_mode: str = Field(default="auto", description="执行模式: auto/parallel/sequential")
    estimated_duration: float = Field(default=0, description="预计时长")


class ToolMetadata(BaseModel):
    """工具元数据"""
    version: str = Field(default="1.0.0", description="版本号")
    author: str = Field(default="", description="作者")
    tags: List[str] = Field(default_factory=list, description="标签")
    dependencies: List[str] = Field(default_factory=list, description="依赖包")
    rate_limit: Optional[int] = Field(default=None, description="速率限制（每分钟）")
    cost_per_call: float = Field(default=0, description="每次调用成本")
