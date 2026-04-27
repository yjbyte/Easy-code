"""
MCP Adapter - 将 MCP 工具适配为 Function Calling 工具
"""
from typing import Any, Dict, List, Optional

from src.mcp.models import MCPTool, MCPToolType
from src.mcp.client import MCPClient, get_mcp_manager
from src.tools.models import Tool, ToolCategory, ToolParameter
from src.tools.errors import ToolNotFoundError


class MCPToolAdapter:
    """
    MCP 工具适配器

    将 MCP Server 提供的工具转换为 Function Calling 引擎可用的工具
    """

    def __init__(self, mcp_client_name: str):
        self.mcp_client_name = mcp_client_name

    async def convert_tools(self) -> List[Tool]:
        """
        从 MCP Server 获取工具并转换

        Returns:
            Function Calling 工具列表
        """
        manager = get_mcp_manager()
        mcp_client = manager.get(self.mcp_client_name)

        if not mcp_client:
            raise ToolNotFoundError(f"MCP client '{self.mcp_client_name}' not found")

        if not mcp_client.is_connected:
            raise MCPConnectionError(f"MCP client '{self.mcp_client_name}' not connected")

        # 获取 MCP 工具列表
        mcp_tools = await mcp_client.list_tools()

        # 转换为 Function Calling 工具
        tools = []
        for mcp_tool in mcp_tools:
            tool = self._convert_single_tool(mcp_tool)
            if tool:
                tools.append(tool)

        return tools

    def _convert_single_tool(self, mcp_tool: MCPTool) -> Optional[Tool]:
        """转换单个 MCP 工具"""
        # 解析 input_schema 为 ToolParameter 列表
        parameters = self._parse_input_schema(mcp_tool.input_schema)

        # 创建包装函数
        async def mcp_wrapper(**kwargs):
            return await self._execute_mcp_tool(mcp_tool.name, kwargs)

        # 创建 Tool
        tool = Tool(
            name=f"{self.mcp_client_name}.{mcp_tool.name}",
            description=mcp_tool.description or f"MCP tool from {self.mcp_client_name}",
            category=ToolCategory.MCP,
            parameters=parameters,
            async_mode=True,
            metadata={
                "mcp_client": self.mcp_client_name,
                "mcp_tool": mcp_tool.name,
                "original_schema": mcp_tool.input_schema,
            },
        )

        # 设置执行函数
        tool.set_function(mcp_wrapper)

        return tool

    def _parse_input_schema(self, schema: Dict[str, Any]) -> List[ToolParameter]:
        """解析 MCP input_schema 为 ToolParameter 列表"""
        parameters = []

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for param_name, param_def in properties.items():
            param_type = self._map_json_type_to_tool_type(param_def.get("type", "string"))

            tool_param = ToolParameter(
                name=param_name,
                type=param_type,
                description=param_def.get("description", ""),
                required=param_name in required,
                default=param_def.get("default"),
                enum=param_def.get("enum"),
            )
            parameters.append(tool_param)

        return parameters

    def _map_json_type_to_tool_type(self, json_type: str) -> str:
        """映射 JSON Schema 类型到工具参数类型"""
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "number": "integer",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
        }
        return type_mapping.get(json_type, "string")

    async def _execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """执行 MCP 工具"""
        manager = get_mcp_manager()
        mcp_client = manager.get(self.mcp_client_name)

        if not mcp_client:
            raise ToolNotFoundError(f"MCP client '{self.mcp_client_name}' not found")

        # 调用 MCP 工具
        result = await mcp_client.call_tool(tool_name, arguments)

        # 检查错误
        if result.isError:
            raise MCPError(f"MCP tool execution failed: {result.content}")

        # 返回内容
        return result.content


class MCPResourceAdapter:
    """
    MCP 资源适配器

    将 MCP 资源转换为 Function Calling 工具
    """

    def __init__(self, mcp_client_name: str):
        self.mcp_client_name = mcp_client_name

    async def convert_resources(self) -> List[Tool]:
        """
        从 MCP Server 获取资源并转换为读取工具

        Returns:
            Function Calling 工具列表
        """
        manager = get_mcp_manager()
        mcp_client = manager.get(self.mcp_client_name)

        if not mcp_client:
            raise ToolNotFoundError(f"MCP client '{self.mcp_client_name}' not found")

        if not mcp_client.is_connected:
            raise MCPConnectionError(f"MCP client '{self.mcp_client_name}' not connected")

        # 获取 MCP 资源列表
        mcp_resources = await mcp_client.list_resources()

        # 为每个资源创建一个读取工具
        tools = []
        for resource in mcp_resources:
            tool = self._create_resource_tool(resource)
            if tool:
                tools.append(tool)

        return tools

    def _create_resource_tool(self, resource) -> Optional[Tool]:
        """为资源创建读取工具"""
        # 生成工具名称（移除特殊字符）
        safe_name = self._sanitize_name(resource.uri)

        # 创建包装函数
        async def resource_wrapper(**kwargs):
            return await self._read_resource(resource.uri)

        tool = Tool(
            name=f"{self.mcp_client_name}.resource.{safe_name}",
            description=f"读取资源: {resource.name}",
            category=ToolCategory.MCP,
            parameters=[
                ToolParameter(
                    name="uri",
                    type="string",
                    description="资源URI",
                    required=False,
                    default=resource.uri,
                )
            ],
            async_mode=True,
            metadata={
                "mcp_client": self.mcp_client_name,
                "resource_uri": resource.uri,
                "resource_type": "resource",
            },
        )

        tool.set_function(resource_wrapper)
        return tool

    def _sanitize_name(self, uri: str) -> str:
        """清理 URI 为安全的工具名称"""
        # 移除协议和特殊字符
        name = uri
        for prefix in ["file://", "http://", "https://"]:
            if name.startswith(prefix):
                name = name[len(prefix):]

        # 替换特殊字符
        name = name.replace("/", "_").replace("\\", "_").replace("?", "_").replace("&", "_")

        return name

    async def _read_resource(self, uri: str) -> Any:
        """读取资源内容"""
        manager = get_mcp_manager()
        mcp_client = manager.get(self.mcp_client_name)

        if not mcp_client:
            raise ToolNotFoundError(f"MCP client '{self.mcp_client_name}' not found")

        # 读取资源
        content = await mcp_client.read_resource(uri)

        return {
            "uri": content.uri,
            "content": content.content,
            "mime_type": content.mime_type,
        }


# 导入
from src.mcp.errors import MCPConnectionError, MCPError
