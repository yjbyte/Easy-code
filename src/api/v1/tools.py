"""
Function Calling API 接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

from src.tools import (
    get_function_calling_engine,
    get_builtin_tools,
    register_builtin_tools
)

router = APIRouter()

# 初始化引擎并注册内置工具
_engine = None


def get_engine():
    """获取引擎实例"""
    global _engine
    if _engine is None:
        _engine = get_function_calling_engine()
        register_builtin_tools(_engine)
    return _engine


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="调用参数")


class ToolCallResponse(BaseModel):
    """工具调用响应"""
    success: bool = Field(..., description="是否成功")
    result: Optional[Any] = Field(default=None, description="返回结果")
    error: Optional[str] = Field(default=None, description="错误信息")


class BatchToolCallRequest(BaseModel):
    """批量工具调用请求"""
    calls: List[ToolCallRequest] = Field(..., description="调用列表")


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    category: str
    parameters: List[dict]


@router.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """
    列出所有可用工具

    返回所有已注册的工具信息
    """
    engine = get_engine()
    tools = engine.list_tools()

    return [
        ToolInfo(
            name=tool.name,
            description=tool.description,
            category=tool.category.value,
            parameters=[
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required
                }
                for p in tool.parameters
            ]
        )
        for tool in tools
    ]


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """
    调用单个工具

    示例:
    ```json
    {
        "tool_name": "get_current_time",
        "parameters": {"timezone": "Asia/Shanghai"}
    }
    ```
    """
    engine = get_engine()

    try:
        result = await engine.call(
            tool_name=request.tool_name,
            parameters=request.parameters
        )

        return ToolCallResponse(
            success=True,
            result=result
        )

    except Exception as e:
        return ToolCallResponse(
            success=False,
            error=str(e)
        )


@router.post("/tools/call/batch")
async def call_tools_batch(request: BatchToolCallRequest):
    """
    批量调用工具

    示例:
    ```json
    {
        "calls": [
            {"tool_name": "calculate", "parameters": {"expression": "2 + 3"}},
            {"tool_name": "get_current_time", "parameters": {}}
        ]
    }
    ```
    """
    engine = get_engine()

    try:
        calls = [
            {"tool_name": call.tool_name, "parameters": call.parameters}
            for call in request.calls
        ]

        results = await engine.execute_batch(calls)

        return {
            "results": [
                {
                    "tool_name": r.tool_name,
                    "success": r.success,
                    "result": r.result,
                    "error": r.error,
                    "duration": r.duration
                }
                for r in results
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量调用失败: {str(e)}")


@router.get("/tools/openai-format")
async def get_tools_openai_format():
    """
    获取 OpenAI Function Calling 格式的工具列表

    可直接用于 LLM 的 tools 参数
    """
    engine = get_engine()
    return engine.to_openai_format()


@router.get("/tools/stats")
async def get_tools_stats():
    """
    获取工具统计信息
    """
    engine = get_engine()

    tools = engine.list_tools()

    # 按分类统计
    category_count = {}
    for tool in tools:
        cat = tool.category.value
        category_count[cat] = category_count.get(cat, 0) + 1

    return {
        "total": len(tools),
        "by_category": category_count,
        "builtin_count": len(get_builtin_tools())
    }
