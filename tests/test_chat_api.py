"""
测试聊天 API
"""
import requests

API_URL = "http://localhost:8001/api/v1/chat"

# 测试查询
test_queries = [
    "知识图谱和向量检索有什么关系？",
    "什么是 GraphRAG？",
    "Neo4j 和 Qdrant 有什么区别？",
    "列出所有支持的技能"
]

for query in test_queries:
    print(f"\n{'=' * 50}")
    print(f"查询: {query}")
    print('=' * 50)

    try:
        response = requests.post(
            API_URL,
            json={"message": query},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            print(f"\n[意图分析]")
            if data.get("intent"):
                intent = data["intent"]
                print(f"  查询类型: {intent.get('query_type')}")
                print(f"  实体: {intent.get('entities')}")
                print(f"  关键词: {intent.get('keywords')}")
                print(f"  复杂度: {intent.get('complexity')}")
                print(f"  所需能力: {intent.get('requires')}")
                print(f"  推荐工具: {intent.get('preferred_tools')}")
                print(f"  置信度: {intent.get('confidence')}")
                print(f"  建议策略: {intent.get('suggested_strategy')}")

            print(f"\n[助手回复]")
            print(f"  {data.get('message')}")

        else:
            print(f"错误: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"请求失败: {str(e)}")

print(f"\n{'=' * 50}")
print("测试完成")
print('=' * 50)
