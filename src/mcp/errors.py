"""
MCP 错误定义
"""
from typing import Any, Dict, Optional


class MCPError(Exception):
    """MCP 基础错误"""

    def __init__(self, message: str, code: int = 0, data: Any = None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(self.message)


class MCPConnectionError(MCPError):
    """MCP 连接错误"""
    pass


class MCPProtocolError(MCPError):
    """MCP 协议错误"""
    pass


class MCPToolNotFoundError(MCPError):
    """MCP 工具不存在"""
    pass


class MCPResourceNotFoundError(MCPError):
    """MCP 资源不存在"""
    pass


class MCPTimeoutError(MCPError):
    """MCP 超时错误"""
    pass
