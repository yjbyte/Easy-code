"""
MCP 测试脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mcp.servers import get_mcp_server_manager, MCPServerConfig


async def test_list_presets():
    """测试列出预设服务器"""
    print("=" * 50)
    print("测试 1: 列出预设 MCP Servers")
    print("=" * 50)

    presets = MCPServerConfig.list_presets()
    print(f"\n可用的预设服务器 ({len(presets)} 个):")

    for name in presets:
        config = MCPServerConfig.get_preset(name)
        print(f"\n{name}:")
        print(f"  描述: {config.get('description', 'N/A')}")
        print(f"  命令: {config.get('command', 'N/A')}")
        print(f"  参数: {' '.join(config.get('args', []))}")


async def test_connect_filesystem():
    """测试连接 filesystem MCP Server"""
    print("\n" + "=" * 50)
    print("测试 2: 连接 filesystem MCP Server")
    print("=" * 50)

    manager = get_mcp_server_manager()

    try:
        print("\n正在连接 filesystem MCP Server...")
        client = await manager.connect_preset("filesystem")

        print(f"连接成功!")
        print(f"服务器名称: {client.name}")
        print(f"已连接: {client.is_connected}")

        # 列出工具
        tools = await client.list_tools()
        print(f"\n可用工具 ({len(tools)} 个):")
        for tool in tools[:5]:  # 只显示前5个
            print(f"  - {tool.name}: {tool.description}")

        # 列出资源
        resources = await client.list_resources()
        print(f"\n可用资源 ({len(resources)} 个):")
        for resource in resources[:5]:  # 只显示前5个
            print(f"  - {resource.uri}: {resource.name}")

    except Exception as e:
        print(f"\n连接失败: {e}")
        print("提示: 需要安装 Node.js 和 npx")


async def test_tool_registration():
    """测试工具注册到 Function Calling 引擎"""
    print("\n" + "=" * 50)
    print("测试 3: MCP 工具注册到 Function Calling")
    print("=" * 50)

    from src.tools import get_function_calling_engine

    engine = get_function_calling_engine()

    # 获取已注册的工具
    tools = engine.list_tools()
    mcp_tools = [t for t in tools if t.category.value == "mcp"]

    print(f"\n已注册的 MCP 工具 ({len(mcp_tools)} 个):")
    for tool in mcp_tools[:10]:  # 只显示前10个
        print(f"  - {tool.name}: {tool.description}")


async def test_call_mcp_tool():
    """测试调用 MCP 工具"""
    print("\n" + "=" * 50)
    print("测试 4: 调用 MCP 工具")
    print("=" * 50)

    from src.tools import get_function_calling_engine

    engine = get_function_calling_engine()

    # 查找 filesystem 工具
    tools = engine.find_tools_by_capability("file")

    if tools:
        tool = tools[0]
        print(f"\n找到工具: {tool.name}")
        print(f"描述: {tool.description}")

        try:
            # 尝试调用
            print("\n尝试调用工具...")
            result = await engine.call(
                tool_name=tool.name,
                parameters={}
            )
            print(f"调用成功!")
            print(f"结果: {result}")
        except Exception as e:
            print(f"调用失败: {e}")
    else:
        print("\n未找到文件系统相关的工具")


async def test_disconnect():
    """测试断开连接"""
    print("\n" + "=" * 50)
    print("测试 5: 断开 MCP 连接")
    print("=" * 50)

    manager = get_mcp_server_manager()

    try:
        await manager.disconnect_all()
        print("所有 MCP Server 已断开连接")
    except Exception as e:
        print(f"断开连接时出错: {e}")


async def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("     MCP 功能测试")
    print("=" * 50 + "\n")

    try:
        await test_list_presets()
        await test_connect_filesystem()
        await test_tool_registration()
        await test_call_mcp_tool()
        await test_disconnect()

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
