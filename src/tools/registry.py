"""
Function Registry - 函数注册表
"""
from typing import Dict, List, Optional
from collections import defaultdict

from src.tools.models import Tool, ToolCategory
from src.tools.errors import ToolNotFoundError, ToolAlreadyRegisteredError


class FunctionRegistry:
    """函数注册表 - 管理所有可调用工具"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._category_index: Dict[ToolCategory, List[str]] = defaultdict(list)
        self._tag_index: Dict[str, List[str]] = defaultdict(list)

    def register(self, tool: Tool) -> None:
        """
        注册工具

        Args:
            tool: 工具定义

        Raises:
            ToolAlreadyRegisteredError: 工具已被注册
        """
        if tool.name in self._tools:
            raise ToolAlreadyRegisteredError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool
        self._category_index[tool.category].append(tool.name)

        # 索引标签
        for tag in tool.metadata.get("tags", []):
            self._tag_index[tag].append(tool.name)

    def unregister(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            是否成功注销
        """
        if name not in self._tools:
            return False

        tool = self._tools[name]

        # 清理分类索引
        if tool.name in self._category_index[tool.category]:
            self._category_index[tool.category].remove(tool.name)

        # 清理标签索引
        for tag in tool.metadata.get("tags", []):
            if tool.name in self._tag_index[tag]:
                self._tag_index[tag].remove(tool.name)

        del self._tools[name]
        return True

    def get(self, name: str) -> Optional[Tool]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            工具定义，不存在则返回 None
        """
        return self._tools.get(name)

    def get_or_raise(self, name: str) -> Tool:
        """
        获取工具，不存在则抛出异常

        Args:
            name: 工具名称

        Returns:
            工具定义

        Raises:
            ToolNotFoundError: 工具不存在
        """
        tool = self.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Tool '{name}' not found")
        return tool

    def list(self, category: Optional[ToolCategory] = None) -> List[Tool]:
        """
        列出工具

        Args:
            category: 工具分类筛选，None 表示全部

        Returns:
            工具列表
        """
        if category is None:
            return list(self._tools.values())

        tool_names = self._category_index.get(category, [])
        return [self._tools[name] for name in tool_names]

    def find_by_tag(self, tag: str) -> List[Tool]:
        """
        按标签查找工具

        Args:
            tag: 标签

        Returns:
            匹配的工具列表
        """
        tool_names = self._tag_index.get(tag, [])
        return [self._tools[name] for name in tool_names]

    def find_by_capability(self, capability: str) -> List[Tool]:
        """
        按能力查找工具（通过描述或标签）

        Args:
            capability: 能力关键词

        Returns:
            匹配的工具列表
        """
        results = []

        capability_lower = capability.lower()

        for tool in self._tools.values():
            # 检查名称
            if capability_lower in tool.name.lower():
                results.append(tool)
                continue

            # 检查描述
            if capability_lower in tool.description.lower():
                results.append(tool)
                continue

            # 检查标签
            tags = tool.metadata.get("tags", [])
            if any(capability_lower in tag.lower() for tag in tags):
                results.append(tool)

        return results

    def count(self) -> int:
        """返回工具总数"""
        return len(self._tools)

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        self._category_index.clear()
        self._tag_index.clear()

    def to_openai_format(self) -> List[dict]:
        """
        转换为 OpenAI Function Calling 格式

        Returns:
            OpenAI 格式的工具列表
        """
        openai_tools = []

        for tool in self._tools.values():
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }

            # 添加参数定义
            for param in tool.parameters:
                openai_tool["function"]["parameters"]["properties"][param.name] = {
                    "type": param.type,
                    "description": param.description,
                    **({"enum": param.enum} if param.enum else {})
                }

                if param.required:
                    openai_tool["function"]["parameters"]["required"].append(param.name)

            openai_tools.append(openai_tool)

        return openai_tools


# 全局注册表实例
_global_registry: Optional[FunctionRegistry] = None


def get_function_registry() -> FunctionRegistry:
    """获取全局函数注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = FunctionRegistry()
    return _global_registry


def reset_function_registry():
    """重置全局函数注册表（主要用于测试）"""
    global _global_registry
    _global_registry = None
