"""
MCP (Model Context Protocol) 核心数据模型
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from enum import Enum


class MCPRole(str, Enum):
    """MCP 客户端/服务端角色"""
    CLIENT = "client"
    SERVER = "server"


class MCPMethod(str, Enum):
    """MCP JSON-RPC 方法"""
    # 初始化
    INITIALIZE = "initialize"
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"


class JSONRPCMessage(BaseModel):
    """JSON-RPC 消息基类"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None


class JSONRPCRequest(JSONRPCMessage):
    """JSON-RPC 请求"""
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(JSONRPCMessage):
    """JSON-RPC 响应"""
    result: Optional[Any] = None
    error: Optional["JSONRPCError"] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 错误"""
    code: int
    message: str
    data: Optional[Any] = None


# ============ MCP 数据模型 ============

class MCPCapability(BaseModel):
    """MCP 能力"""
    resources: Optional[bool] = None
    tools: Optional[bool] = None
    prompts: Optional[bool] = None


class MCPResourceTemplate(BaseModel):
    """MCP 资源模板"""
    uri_template: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class MCPResource(BaseModel):
    """MCP 资源"""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class MCPResourceContent(BaseModel):
    """MCP 资源内容"""
    uri: str
    content: Any  # 可以是文本或二进制
    mime_type: Optional[str] = None


class MCPToolParameter(BaseModel):
    """MCP 工具参数"""
    type: str  # "object", "string", "number", etc.
    properties: Optional[Dict[str, Dict[str, Any]]] = None
    required: Optional[List[str]] = None


class MCPTool(BaseModel):
    """MCP 工具定义"""
    name: str
    description: Optional[str] = None
    input_schema: Dict[str, Any]


class MCPToolCallRequest(BaseModel):
    """MCP 工具调用请求"""
    name: str
    arguments: Optional[Dict[str, Any]] = None


class MCPToolCallResult(BaseModel):
    """MCP 工具调用结果"""
    content: List[Dict[str, Any]]
    isError: bool = False


class MCPPrompt(BaseModel):
    """MCP 提示词"""
    name: str
    description: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None


class MCPPromptMessage(BaseModel):
    """MCP 提示词消息"""
    role: str
    content: MCPToolCallResult  # 复用 ToolCallResult 的内容结构


class MCPClientInfo(BaseModel):
    """MCP 客户端信息"""
    name: str
    version: str


class MCPServerInfo(BaseModel):
    """MCP 服务端信息"""
    name: str
    version: str


class MCPInitializeRequest(BaseModel):
    """MCP 初始化请求参数"""
    protocol_version: str
    capabilities: MCPCapability
    client_info: MCPClientInfo


class MCPInitializeResult(BaseModel):
    """MCP 初始化结果"""
    protocol_version: str
    capabilities: MCPCapability
    server_info: MCPServerInfo
    instructions: Optional[str] = None


# ============ MCP 连接配置 ============

class MCPConnectionConfig(BaseModel):
    """MCP 连接配置"""
    name: str  # 连接名称
    transport: str  # "stdio" 或 "sse" (Server-Sent Events)
    command: Optional[str] = None  # stdio 模式下的命令
    args: Optional[List[str]] = None  # 命令参数
    env: Optional[Dict[str, str]] = None  # 环境变量
    url: Optional[str] = None  # SSE 模式下的 URL


# ============ 工具类型 ============

class MCPToolType(str, Enum):
    """MCP 工具类型"""
    RESOURCE = "resource"  # 资源读取
    TOOL = "tool"  # 工具调用
    PROMPT = "prompt"  # 提示词
