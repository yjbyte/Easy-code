"""
Tools 工具/函数调用模块

提供：
- FunctionCallingEngine: Function Calling 引擎
- Tool: 工具基类
- FunctionRegistry: 函数注册表
- 内置工具
"""

from .models import Tool, ToolCategory, ToolParameter
from .engine import FunctionCallingEngine, get_function_calling_engine
from .registry import FunctionRegistry, get_function_registry
from .builtin import register_builtin_tools, get_builtin_tools

__all__ = [
    "Tool",
    "ToolCategory",
    "ToolParameter",
    "FunctionCallingEngine",
    "get_function_calling_engine",
    "FunctionRegistry",
    "get_function_registry",
    "register_builtin_tools",
    "get_builtin_tools",
]
