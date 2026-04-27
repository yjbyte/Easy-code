"""
LLM 意图分析器
"""
import json
import asyncio
import re
from typing import Optional, List, Tuple

from src.agent.models import (
    QueryIntent,
    SubIntent,
    QueryType,
    ComplexityLevel,
    Capability,
    StrategyType
)
from src.utils.llm import get_glm_client


# 系统提示词
INTENT_ANALYSIS_SYSTEM_PROMPT = """你是一个专业的查询意图分析专家。你的任务是分析用户查询，识别其意图类型、提取关键信息，并给出最优的执行策略建议。

请严格按照 JSON 格式输出分析结果。

## 查询类型定义
- fact: 事实查询 - "什么是X？"、"X的定义是什么？"
- relation: 关系查询 - "X和Y的关系？"、"X与Y的区别？"
- reasoning: 推理查询 - "为什么X？"、"X的原因是什么？"
- aggregation: 聚合查询 - "所有X"、"X有哪些分类？"
- open_ended: 开放查询 - "介绍一下X"、"X包括哪些方面？"
- generation: 生成类 - "写代码"、"写文章"、"画图表"
- system: 系统问题 - "你是什么"、"你使用什么模型"、"你的能力"
- realtime: 实时数据查询 - "天气"、"股票"、"新闻"、"现在的时间"

## 复杂度级别
- low: 简单，单步检索即可回答
- medium: 中等，需要2-3步处理
- high: 复杂，需要深度推理或多源整合

## 能力需求
- graph_search: 需要知识图谱检索
- vector_search: 需要向量相似度检索
- multi_hop_reasoning: 需要多跳推理能力
- realtime_data: 需要实时数据（如搜索、数据库）
- code_execution: 需要代码执行能力
- mcp_access: 需要通过 MCP 访问外部数据
- system_info: 需要回答系统相关问题

## 多意图识别
如果用户查询包含多个问题（用逗号、"以及"、"和"等连接），请识别为多个子意图：
- has_multiple_intents: 是否包含多个意图
- sub_intents: 子意图列表，每个子意图是一个完整的意图分析

## 分析原则
1. **准确优先**: 优先识别明确的意图类型
2. **多意图检测**: 检测用户是否问了多个问题
3. **可解释**: 给出分析推理过程
4. **务实**: 基于实际可用的能力给出建议

请以 JSON 格式输出，不要包含任何其他文字说明。
"""


# 多意图分割符
MULTI_INTENT_PATTERNS = [
    r'以及',
    r'还有',
    r'另外',
    r'同时',
    r'，\s*另外',
    r'；',
    r'\?\s*[\u4e00-\u9fa5]+',  # 问号后跟中文（新问题）
]


# 系统问题关键词
SYSTEM_PATTERNS = [
    r'你.*?是.*?什么',
    r'你.*?叫.*?什么',
    r'你.*?名字',
    r'你.*?使用.*?什么.*?模型',
    r'你.*?底层.*?什么.*?LLM',
    r'你.*?基于.*?什么',
    r'你.*?能力',
    r'你.*?能.*?做.*?什么',
    r'介绍.*?自己',
    r'你的.*?功能',
]


# 实时数据查询关键词
REALTIME_PATTERNS = [
    r'天气',
    r'气温',
    r'温度',
    r'股票',
    r'股价',
    r'汇率',
    r'新闻',
    r'现在.*?时间',
    r'今天.*?日期',
    r'当前.*?行情',
    r'实时.*?数据',
    r'最新.*?消息',
]


class LLMIntentAnalyzer:
    """LLM 意图分析器"""

    def __init__(self):
        self.llm_client = get_glm_client()

    async def analyze(self, query: str) -> QueryIntent:
        """
        分析查询意图

        Args:
            query: 用户查询

        Returns:
            QueryIntent: 意图分析结果
        """
        # 构建 Prompt
        prompt = self._build_analysis_prompt(query)

        try:
            # 调用 LLM
            response = await self.llm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": INTENT_ANALYSIS_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # 低温度保证稳定输出
            )

            # 解析 JSON 响应
            return self._parse_response(query, response)

        except Exception as e:
            # LLM 调用失败时的降级处理
            return self._fallback_analysis(query, str(e))

    def _build_analysis_prompt(self, query: str) -> str:
        """构建分析 Prompt"""
        return f"""请分析以下用户查询的意图：

查询："{query}"

请以 JSON 格式输出以下信息：

{{
  "query_type": "查询类型 (fact/relation/reasoning/aggregation/open_ended/generation)",
  "entities": ["提取的实体列表"],
  "keywords": ["关键关键词列表"],
  "domain": "涉及的领域（如果可识别）",
  "complexity": "复杂度 (low/medium/high)",
  "requires": ["所需能力列表 (graph_search/vector_search/multi_hop_reasoning/realtime_data)"],
  "preferred_tools": ["推荐的工具名称 (query_knowledge_graph/vector_search/mcp_web_search 等)"],
  "estimated_difficulty": 0.5,
  "confidence": 0.8,
  "reasoning": "分析推理过程（简要说明为什么这样分析）",
  "suggested_strategy": "建议的执行策略 (simple/graph/hybrid)"
}}

注意：
- 准确识别查询类型
- 提取所有相关实体
- 评估复杂度和难度
- 基于实际可用能力给出建议

只返回 JSON，不要其他内容。
"""

    def _parse_response(self, query: str, response: str) -> QueryIntent:
        """解析 LLM 响应"""
        try:
            # 尝试直接解析 JSON
            data = json.loads(response)

            # 处理可能的 JSON 格式问题
            if isinstance(data, str):
                data = json.loads(data)

            return QueryIntent(
                query=query,
                query_type=QueryType(data.get("query_type", "open_ended")),
                entities=data.get("entities", []),
                keywords=data.get("keywords", []),
                domain=data.get("domain"),
                complexity=ComplexityLevel(data.get("complexity", "medium")),
                requires=[Capability(c) for c in data.get("requires", [])],
                preferred_tools=data.get("preferred_tools", []),
                confidence=data.get("confidence", 0.8),
                estimated_difficulty=data.get("estimated_difficulty", 0.5),
                reasoning=data.get("reasoning"),
                suggested_strategy=data.get("suggested_strategy")
            )

        except json.JSONDecodeError:
            # JSON 解析失败，使用降级分析
            return self._fallback_analysis(query, "JSON解析失败")

    def _fallback_analysis(self, query: str, error: str = "") -> QueryIntent:
        """降级分析（规则方法）"""
        # 简单规则匹配
        query_lower = query.lower()

        # 关键词匹配
        fact_keywords = ["什么是", "什么", "定义", "是什么", "what is"]
        relation_keywords = ["和", "与", "关系", "区别", "联系", "共同点"]
        reasoning_keywords = ["为什么", "原因", "如何", "怎么", "原理"]
        aggregation_keywords = ["所有", "每个", "列举", "都有哪些"]
        generation_keywords = ["写", "生成", "创建", "代码"]

        if any(kw in query_lower for kw in generation_keywords):
            query_type = QueryType.GENERATION
        elif any(kw in query_lower for kw in relation_keywords):
            query_type = QueryType.RELATION
        elif any(kw in query_lower for kw in reasoning_keywords):
            query_type = QueryType.REASONING
        elif any(kw in query_lower for kw in aggregation_keywords):
            query_type = QueryType.AGGREGATION
        else:
            query_type = QueryType.FACT

        # 简单实体提取（大写字母和专有名词）
        import re
        entities = re.findall(r'[A-Z][a-zA-Z0-9]+|[A-Z]+', query)

        # 关键词
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', query)

        # 复杂度评估
        complexity = ComplexityLevel.MEDIUM
        if len(query) < 20:
            complexity = ComplexityLevel.LOW
        elif len(query) > 50 or "和" in query and "的" in query:
            complexity = ComplexityLevel.HIGH

        # 能力需求
        requires = []
        preferred_tools = []

        if query_type == QueryType.RELATION:
            requires = [Capability.GRAPH_SEARCH]
            preferred_tools = ["query_knowledge_graph"]
        elif query_type == QueryType.REASONING:
            requires = [Capability.MULTI_HOP, Capability.GRAPH_SEARCH]
            preferred_tools = ["graph_multi_hop"]
        elif query_type == QueryType.GENERATION:
            pass  # 不需要检索
        else:
            requires = [Capability.VECTOR_SEARCH]
            preferred_tools = ["vector_search"]

        return QueryIntent(
            query=query,
            query_type=query_type,
            entities=entities,
            keywords=keywords,
            complexity=complexity,
            requires=requires,
            preferred_tools=preferred_tools,
            confidence=0.6,  # 降级方法的置信度较低
            reasoning=f"规则匹配分析 {query_type.value}",
            suggested_strategy=self._suggest_strategy(query_type, complexity)
        )

    def _suggest_strategy(
        self,
        query_type: QueryType,
        complexity: ComplexityLevel
    ) -> str:
        """建议执行策略"""
        if query_type == QueryType.FACT or complexity == ComplexityLevel.LOW:
            return StrategyType.SIMPLE
        elif query_type in [QueryType.RELATION, QueryType.REASONING]:
            return StrategyType.GRAPH
        else:
            return StrategyType.HYBRID


# 全局实例
_global_analyzer: Optional[LLMIntentAnalyzer] = None


def get_intent_analyzer() -> LLMIntentAnalyzer:
    """获取全局意图分析器"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = LLMIntentAnalyzer()
    return _global_analyzer


# 别名，保持一致性
IntentAnalyzer = LLMIntentAnalyzer

# 注意：QueryAnalysisSkill 已移至 src/skills/builtin/query_analysis.py
# 从 skills 模块导入即可使用

