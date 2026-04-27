"""
意图理解集成测试

测试意图分析器与聊天 API 的集成
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.intent import get_intent_analyzer, QueryType


async def test_intent_analyzer():
    """测试意图分析器"""
    print("=" * 50)
    print("测试意图分析器")
    print("=" * 50)

    analyzer = get_intent_analyzer()

    # 测试查询列表
    test_queries = [
        "什么是知识图谱？",
        "Neo4j 和 Qdrant 有什么区别？",
        "为什么需要向量检索？",
        "列出所有的图数据库",
        "介绍一下 GraphRAG 技术",
        "写一段 Python 代码",
        "Python 和 Java 在性能上有什么关系？",
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 40)

        try:
            intent = await analyzer.analyze(query)

            print(f"  查询类型: {intent.query_type.value}")
            print(f"  实体: {intent.entities}")
            print(f"  关键词: {intent.keywords}")
            print(f"  复杂度: {intent.complexity.value}")
            print(f"  能力需求: {[c.value for c in intent.requires]}")
            print(f"  推荐工具: {intent.preferred_tools}")
            print(f"  置信度: {intent.confidence}")
            print(f"  建议策略: {intent.suggested_strategy}")
            if intent.reasoning:
                print(f"  推理: {intent.reasoning[:100]}...")

        except Exception as e:
            print(f"  [错误] {str(e)}")


async def test_skill_execution():
    """测试技能执行"""
    print("\n" + "=" * 50)
    print("测试技能执行")
    print("=" * 50)

    from src.skills import SkillContext

    # QueryAnalysisSkill 已移动到 skills.builtin
    # from src.skills.builtin import QueryAnalysisSkill

    # skill = QueryAnalysisSkill()
    # TODO: 等待实现内置技能后再测试

    print(f"\n技能名称: {skill.name}")
    print(f"技能描述: {skill.description}")
    print(f"技能分类: {skill.category.value}")

    # 执行技能
    context = SkillContext(inputs={"query": "知识图谱和向量检索有什么关系？"})

    print("\n执行技能...")
    result = await skill.execute(context)

    print(f"\n执行成功: {result.success}")
    if result.success:
        print(f"输出:")
        for key, value in result.outputs.items():
            print(f"  {key}: {value}")
    else:
        print(f"错误: {result.error}")


async def test_enhanced_prompt():
    """测试增强提示词"""
    print("\n" + "=" * 50)
    print("测试增强提示词")
    print("=" * 50)

    from src.api.v1.chat import _build_enhanced_system_prompt
    from src.agent.intent import get_intent_analyzer
    from src.config.prompts import DEFAULT_SYSTEM_PROMPT

    base_prompt = "你是一个专业的AI助手。"
    query = "知识图谱中的实体和关系是什么？"

    analyzer = get_intent_analyzer()
    intent = await analyzer.analyze(query)

    enhanced = _build_enhanced_system_prompt(base_prompt, intent)

    print(f"\n原始查询: {query}")
    print(f"\n基础提示词:\n{base_prompt}")
    print(f"\n增强后提示词:\n{enhanced}")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("意图理解集成测试套件")
    print("=" * 50 + "\n")

    # 测试1: 意图分析器
    await test_intent_analyzer()

    # 测试2: 技能执行
    await test_skill_execution()

    # 测试3: 增强提示词
    await test_enhanced_prompt()

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
