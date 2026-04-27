"""
Function Calling 测试脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools import (
    get_function_calling_engine,
    register_builtin_tools
)


async def test_basic_call():
    """测试基础调用"""
    print("=" * 50)
    print("测试 1: 基础工具调用")
    print("=" * 50)

    engine = get_function_calling_engine()
    register_builtin_tools(engine)

    # 列出所有工具
    tools = engine.list_tools()
    print(f"\n可用工具 ({len(tools)} 个):")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    # 调用 get_current_time 工具
    print("\n调用 get_current_time...")
    result = await engine.call(
        tool_name="get_current_time",
        parameters={"timezone": "Asia/Shanghai"}
    )
    print(f"结果: {result}")


async def test_calculate():
    """测试计算器"""
    print("\n" + "=" * 50)
    print("测试 2: 计算器工具")
    print("=" * 50)

    engine = get_function_calling_engine()

    expressions = [
        "2 + 3",
        "10 * 5",
        "100 / 4",
        "(2 + 3) * 4"
    ]

    for expr in expressions:
        print(f"\n计算: {expr}")
        result = await engine.call(
            tool_name="calculate",
            parameters={"expression": expr}
        )
        if result.get("success"):
            print(f"  结果: {result['result']}")
        else:
            print(f"  错误: {result.get('error')}")


async def test_batch_call():
    """测试批量调用"""
    print("\n" + "=" * 50)
    print("测试 3: 批量工具调用")
    print("=" * 50)

    engine = get_function_calling_engine()

    calls = [
        {"tool_name": "calculate", "parameters": {"expression": "2 + 3"}},
        {"tool_name": "get_current_time", "parameters": {}},
        {"tool_name": "calculate", "parameters": {"expression": "10 * 5"}}
    ]

    print(f"\n批量执行 {len(calls)} 个调用...")
    results = await engine.execute_batch(calls)

    for i, result in enumerate(results):
        print(f"\n调用 {i+1}: {result.tool_name}")
        print(f"  成功: {result.success}")
        print(f"  耗时: {result.duration:.3f}s")
        if result.success:
            print(f"  结果: {result.result}")
        else:
            print(f"  错误: {result.error}")


async def test_openai_format():
    """测试 OpenAI 格式转换"""
    print("\n" + "=" * 50)
    print("测试 4: OpenAI 格式转换")
    print("=" * 50)

    engine = get_function_calling_engine()

    openai_tools = engine.to_openai_format()
    print(f"\nOpenAI 格式工具定义 ({len(openai_tools)} 个):")

    for tool in openai_tools[:2]:  # 只显示前两个
        print(f"\n工具: {tool['function']['name']}")
        print(f"  描述: {tool['function']['description']}")
        print(f"  参数: {list(tool['function']['parameters']['properties'].keys())}")


async def test_find_tools():
    """测试工具查找"""
    print("\n" + "=" * 50)
    print("测试 5: 按能力查找工具")
    print("=" * 50)

    engine = get_function_calling_engine()

    # 查找不同能力的工具
    capabilities = ["搜索", "计算", "时间", "代码"]

    for capability in capabilities:
        tools = engine.find_tools_by_capability(capability)
        print(f"\n能力 '{capability}' 匹配的工具:")
        if tools:
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
        else:
            print("  (无)")


async def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("     Function Calling 功能测试")
    print("=" * 50 + "\n")

    try:
        await test_basic_call()
        await test_calculate()
        await test_batch_call()
        await test_openai_format()
        await test_find_tools()

        print("\n" + "=" * 50)
        print("所有测试完成!")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
