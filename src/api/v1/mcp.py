"""
MCP API 接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from src.mcp.servers import get_mcp_server_manager, MCPServerConfig


router = APIRouter()


class MCPConnectRequest(BaseModel):
    """MCP 连接请求"""
    name: str = Field(..., description="服务器名称")
    command: Optional[str] = Field(None, description="启动命令（预设服务器可省略）")
    args: Optional[List[str]] = Field(None, description="命令参数")
    env: Optional[Dict[str, str]] = Field(None, description="环境变量")
    register_tools: bool = Field(default=True, description="是否自动注册工具")


class MCPConnectResponse(BaseModel):
    """MCP 连接响应"""
    success: bool
    server: str
    message: str
    tools_registered: int = 0


class MCPServerInfo(BaseModel):
    """MCP 服务器信息"""
    name: str
    description: str
    connected: bool


@router.get("/mcp/presets")
async def list_mcp_presets():
    """
    列出所有预设的 MCP Servers

    返回可用的预设服务器配置
    """
    presets = MCPServerConfig.list_presets()

    return {
        "presets": [
            {
                "name": name,
                **MCPServerConfig.get_preset(name)
            }
            for name in presets
        ]
    }


@router.get("/mcp/servers")
async def list_connected_servers():
    """
    列出已连接的 MCP Servers

    返回当前已连接的服务器列表
    """
    manager = get_mcp_server_manager()
    connected = manager.get_connected_servers()

    servers = []
    for name in connected:
        from src.mcp import get_mcp_manager
        mcp_manager = get_mcp_manager()
        client = mcp_manager.get(name)

        if client:
            servers.append({
                "name": name,
                "connected": client.is_connected,
                "capabilities": {
                    "resources": client.capabilities.resources if client.capabilities else False,
                    "tools": client.capabilities.tools if client.capabilities else False,
                    "prompts": client.capabilities.prompts if client.capabilities else False,
                }
            })

    return {"servers": servers}


@router.post("/mcp/connect")
async def connect_mcp_server(request: MCPConnectRequest) -> MCPConnectResponse:
    """
    连接到 MCP Server

    支持两种方式：
    1. 预设服务器：只提供 name，使用预设配置
    2. 自定义服务器：提供 command, args, env

    示例:
    ```json
    {
        "name": "filesystem",
        "register_tools": true
    }
    ```
    """
    manager = get_mcp_server_manager()

    try:
        # 检查是否是预设服务器
        if request.name in MCPServerConfig.list_presets():
            if request.command:
                raise HTTPException(
                    status_code=400,
                    detail="Preset server should not specify command"
                )

            client = await manager.connect_preset(
                request.name,
                register_tools=request.register_tools
            )
            return MCPConnectResponse(
                success=True,
                server=request.name,
                message=f"Connected to preset MCP server '{request.name}'"
            )

        else:
            # 自定义服务器
            if not request.command:
                raise HTTPException(
                    status_code=400,
                    detail="Custom server must specify command"
                )

            client = await manager.connect_server(
                name=request.name,
                command=request.command,
                args=request.args,
                env=request.env,
                register_tools=request.register_tools
            )
            return MCPConnectResponse(
                success=True,
                server=request.name,
                message=f"Connected to custom MCP server '{request.name}'"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to MCP server: {str(e)}"
        )


@router.post("/mcp/disconnect/{server_name}")
async def disconnect_mcp_server(server_name: str):
    """
    断开 MCP Server 连接

    Args:
        server_name: 服务器名称
    """
    from src.mcp import get_mcp_manager

    manager = get_mcp_manager()
    client = manager.get(server_name)

    if not client:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")

    try:
        await client.disconnect()
        manager.unregister(server_name)

        # 从管理器中移除
        mcp_server_manager = get_mcp_server_manager()
        mcp_server_manager._connected_servers = [
            s for s in mcp_server_manager._connected_servers
            if s != server_name
        ]

        return {"success": True, "message": f"Disconnected from '{server_name}'"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect: {str(e)}"
        )


@router.post("/mcp/disconnect-all")
async def disconnect_all_mcp_servers():
    """断开所有 MCP Server 连接"""
    manager = get_mcp_server_manager()

    try:
        await manager.disconnect_all()
        return {"success": True, "message": "Disconnected all MCP servers"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect: {str(e)}"
        )


@router.get("/mcp/{server_name}/tools")
async def list_mcp_tools(server_name: str):
    """
    列出 MCP Server 提供的工具

    Args:
        server_name: 服务器名称
    """
    from src.mcp import get_mcp_manager

    manager = get_mcp_manager()
    client = manager.get(server_name)

    if not client:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")

    if not client.is_connected:
        raise HTTPException(status_code=400, detail=f"Server '{server_name}' not connected")

    try:
        tools = await client.list_tools()

        return {
            "server": server_name,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                }
                for tool in tools
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tools: {str(e)}"
        )


@router.get("/mcp/{server_name}/resources")
async def list_mcp_resources(server_name: str):
    """
    列出 MCP Server 提供的资源

    Args:
        server_name: 服务器名称
    """
    from src.mcp import get_mcp_manager

    manager = get_mcp_manager()
    client = manager.get(server_name)

    if not client:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")

    if not client.is_connected:
        raise HTTPException(status_code=400, detail=f"Server '{server_name}' not connected")

    try:
        resources = await client.list_resources()

        return {
            "server": server_name,
            "resources": [
                {
                    "uri": r.uri,
                    "name": r.name,
                    "description": r.description,
                    "mime_type": r.mime_type,
                }
                for r in resources
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list resources: {str(e)}"
        )
