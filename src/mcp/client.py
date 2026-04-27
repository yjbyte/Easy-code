"""
MCP Client - MCP 协议客户端
"""
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError

from src.mcp.models import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    MCPMethod,
    MCPInitializeRequest,
    MCPInitializeResult,
    MCPResource,
    MCPResourceContent,
    MCPTool,
    MCPToolCallRequest,
    MCPToolCallResult,
    MCPPrompt,
    MCPPromptMessage,
    MCPCapability,
)
from src.mcp.errors import (
    MCPError,
    MCPConnectionError,
    MCPProtocolError,
    MCPToolNotFoundError,
)


class MCPClient:
    """
    MCP 客户端

    通过 stdio 或 SSE 与 MCP Server 通信
    """

    def __init__(
        self,
        name: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._process: Optional[asyncio.subprocess.Process] = None
        self._initialized = False
        self._server_capabilities: Optional[MCPCapability] = None
        self._request_id = 0

    async def connect(self) -> None:
        """连接到 MCP Server"""
        if not self.command:
            raise MCPConnectionError("No command specified for MCP connection")

        # 启动子进程
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**self._get_env(), **self.env},
        )

        # 初始化握手
        await self._initialize()

    async def disconnect(self) -> None:
        """断开连接"""
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            self._process = None
        self._initialized = False

    async def _initialize(self) -> None:
        """执行初始化握手"""
        init_request = MCPInitializeRequest(
            protocol_version="2024-11-05",
            capabilities=MCPCapability(
                resources=True,
                tools=True,
                prompts=True,
            ),
            client_info={
                "name": "agentic-graphrag",
                "version": "0.1.0",
            },
        )

        response = await self._send_request(
            method=MCPMethod.INITIALIZE,
            params=init_request.dict(),
        )

        try:
            init_result = MCPInitializeResult(**response["result"])
            self._server_capabilities = init_result.capabilities
            self._initialized = True
        except (ValidationError, KeyError) as e:
            raise MCPProtocolError(f"Invalid initialize response: {e}")

    async def list_resources(self) -> List[MCPResource]:
        """列出可用资源"""
        if not self._server_capabilities or not self._server_capabilities.resources:
            return []

        response = await self._send_request(
            method=MCPMethod.LIST_RESOURCES,
        )

        try:
            resources_data = response.get("result", {}).get("resources", [])
            return [MCPResource(**r) for r in resources_data]
        except (ValidationError, TypeError) as e:
            raise MCPProtocolError(f"Invalid list_resources response: {e}")

    async def read_resource(self, uri: str) -> MCPResourceContent:
        """读取资源内容"""
        response = await self._send_request(
            method=MCPMethod.READ_RESOURCE,
            params={"uri": uri},
        )

        try:
            content_data = response.get("result", {})
            return MCPResourceContent(**content_data)
        except (ValidationError, TypeError) as e:
            raise MCPProtocolError(f"Invalid read_resource response: {e}")

    async def list_tools(self) -> List[MCPTool]:
        """列出可用工具"""
        if not self._server_capabilities or not self._server_capabilities.tools:
            return []

        response = await self._send_request(
            method=MCPMethod.LIST_TOOLS,
        )

        try:
            tools_data = response.get("result", {}).get("tools", [])
            return [MCPTool(**t) for t in tools_data]
        except (ValidationError, TypeError) as e:
            raise MCPProtocolError(f"Invalid list_tools response: {e}")

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> MCPToolCallResult:
        """调用工具"""
        response = await self._send_request(
            method=MCPMethod.CALL_TOOL,
            params={
                "name": name,
                "arguments": arguments or {},
            },
        )

        try:
            result_data = response.get("result", {})
            return MCPToolCallResult(**result_data)
        except (ValidationError, TypeError) as e:
            raise MCPProtocolError(f"Invalid call_tool response: {e}")

    async def list_prompts(self) -> List[MCPPrompt]:
        """列出可用提示词"""
        if not self._server_capabilities or not self._server_capabilities.prompts:
            return []

        response = await self._send_request(
            method=MCPMethod.LIST_PROMPTS,
        )

        try:
            prompts_data = response.get("result", {}).get("prompts", [])
            return [MCPPrompt(**p) for p in prompts_data]
        except (ValidationError, TypeError) as e:
            raise MCPProtocolError(f"Invalid list_prompts response: {e}")

    async def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> List[MCPPromptMessage]:
        """获取提示词"""
        response = await self._send_request(
            method=MCPMethod.GET_PROMPT,
            params={
                "name": name,
                "arguments": arguments or {},
            },
        )

        try:
            messages_data = response.get("result", {}).get("messages", [])
            return [MCPPromptMessage(**m) for m in messages_data]
        except (ValidationError, TypeError) as e:
            raise MCPProtocolError(f"Invalid get_prompt response: {e}")

    async def _send_request(
        self,
        method: Union[str, MCPMethod],
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发送 JSON-RPC 请求"""
        if not self._process or self._process.stdin is None:
            raise MCPConnectionError("Not connected to MCP server")

        # 准备请求
        self._request_id += 1
        request = JSONRPCRequest(
            id=self._request_id,
            method=str(method),
            params=params,
        )

        # 发送请求
        request_json = json.dumps(request.dict(exclude_none=True))
        try:
            self._process.stdin.write((request_json + "\n").encode())
            await self._process.stdin.drain()
        except (BrokenPipeError, ConnectionError) as e:
            raise MCPConnectionError(f"Failed to send request: {e}")

        # 读取响应
        try:
            response_line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            raise MCPError("Request timeout")

        if not response_line:
            raise MCPConnectionError("Connection closed by server")

        try:
            response_data = json.loads(response_line.decode())
        except json.JSONDecodeError as e:
            raise MCPProtocolError(f"Invalid JSON response: {e}")

        response = JSONRPCResponse(**response_data)

        # 检查错误
        if response.error:
            raise MCPError(
                f"MCP error: {response.error.message}",
                code=response.error.code,
            )

        if response.result is None:
            raise MCPProtocolError("Empty response result")

        return response.result

    def _get_env(self) -> Dict[str, str]:
        """获取环境变量"""
        import os
        return os.environ.copy()

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._process is not None and self._initialized

    @property
    def capabilities(self) -> Optional[MCPCapability]:
        """服务端能力"""
        return self._server_capabilities

    async def __aenter__(self):
        """上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        await self.disconnect()


class MCPClientManager:
    """MCP 客户端管理器 - 管理多个 MCP 连接"""

    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}

    def register(self, name: str, client: MCPClient) -> None:
        """注册客户端"""
        self._clients[name] = client

    def unregister(self, name: str) -> None:
        """注销客户端"""
        if name in self._clients:
            del self._clients[name]

    def get(self, name: str) -> Optional[MCPClient]:
        """获取客户端"""
        return self._clients.get(name)

    def list_clients(self) -> List[str]:
        """列出所有客户端名称"""
        return list(self._clients.keys())

    async def connect_all(self) -> None:
        """连接所有客户端"""
        for client in self._clients.values():
            if not client.is_connected:
                await client.connect()

    async def disconnect_all(self) -> None:
        """断开所有客户端"""
        for client in self._clients.values():
            if client.is_connected:
                await client.disconnect()


# 全局客户端管理器
_global_manager: Optional[MCPClientManager] = None


def get_mcp_manager() -> MCPClientManager:
    """获取全局 MCP 客户端管理器"""
    global _global_manager
    if _global_manager is None:
        _global_manager = MCPClientManager()
    return _global_manager
