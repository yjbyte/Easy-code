"""
MCP 协议模块

提供：
- MCPClient: MCP 客户端
- MCPClientManager: MCP 客户端管理器
- MCPToolAdapter: MCP 工具适配器
- MCPResourceAdapter: MCP 资源适配器
- 预置 MCP 服务器集成
"""

from .client import MCPClient, MCPClientManager, get_mcp_manager
from .adapter import MCPToolAdapter, MCPResourceAdapter

__all__ = [
    "MCPClient",
    "MCPClientManager",
    "get_mcp_manager",
    "MCPToolAdapter",
    "MCPResourceAdapter",
]
