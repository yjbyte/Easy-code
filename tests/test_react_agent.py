"""
ReAct Agent 测试脚本

测试场景：
1. 系统问题："你底层使用的什么LLM名字"
2. 实时数据查询："无锡市今天的天气"
3. 多意图查询："你底层使用的什么LLM名字，以及无锡市今天的天气"
4. 知识查询："什么是知识图谱"
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_react_agent():
    """测试 ReAct Agent"""
    from src.agent import get_react_agent

    agent = get_react_agent()

    # 测试用例
    test_cases = [
        "你底层使用的什么LLM名字",
        "无锡市今天的天气",
        "你底层使用的什么LLM名字，以及无锡市今天的天气",
        "什么是知识图谱？"
    ]

    for query in test_cases:
        print(f"\n{'='*60}")
        print(f"用户查询: {query}")
        print(f"{'='*60}")

        result = await agent.run(query)

        print(f"\n最终答案:\n{result.answer}")
        print(f"\n执行步骤:")
        for i, step in enumerate(result.steps, 1):
            print(f"{i}. [{step.step_type.upper()}] {step.content[:100]}...")

        # 性能指标
        print(f"\n性能指标:")
        print(f"  LLM 调用次数: {result.llm_calls}")
        print(f"  工具调用次数: {result.tool_calls}")
        print(f"  Token 消耗: {result.tokens_used}")
        print(f"  总耗时: {result.duration:.2f}s" if result.duration else "  总耗时: N/A")
        print(f"  迭代次数: {result.iterations}")

        print(f"\n成功: {result.success}")
        if result.error:
            print(f"错误: {result.error}")


if __name__ == "__main__":
    asyncio.run(test_react_agent())
