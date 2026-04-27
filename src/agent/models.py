"""
意图理解核心数据模型
"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class QueryType(str, Enum):
    """查询类型"""
    FACT = "fact"                     # 事实查询："什么是X？"
    RELATION = "relation"             # 关系查询："X和Y的关系？"
    REASONING = "reasoning"           # 推理查询："为什么X？"
    AGGREGATION = "aggregation"       # 聚合查询："所有X"
    OPEN_ENDED = "open_ended"        # 开放查询："介绍一下X"
    GENERATION = "generation"         # 生成类："写代码"、"写文章"
    SYSTEM = "system"                 # 系统问题："你是什么"、"你使用什么模型"
    REALTIME = "realtime"             # 实时数据："天气"、"股票"、"新闻"


class ComplexityLevel(str, Enum):
    """复杂度级别"""
    LOW = "low"                       # 简单：单步检索即可
    MEDIUM = "medium"                 # 中等：需要多步处理
    HIGH = "high"                     # 复杂：需要深度推理


class Capability(str, Enum):
    """所需能力"""
    GRAPH_SEARCH = "graph_search"
    VECTOR_SEARCH = "vector_search"
    MULTI_HOP = "multi_hop_reasoning"
    REALTIME_DATA = "realtime_data"
    CODE_EXECUTION = "code_execution"
    MCP_ACCESS = "mcp_access"
    SYSTEM_INFO = "system_info"


class SubIntent(BaseModel):
    """子意图（用于多意图查询）"""

    # 子查询内容
    sub_query: str = Field(..., description="子查询内容")

    # 查询类型
    query_type: QueryType = Field(..., description="查询类型")

    # 提取的信息
    entities: List[str] = Field(default_factory=list, description="提取的实体")
    keywords: List[str] = Field(default_factory=list, description="关键词")

    # 能力需求
    requires: List[Capability] = Field(default_factory=list, description="所需能力")
    preferred_tools: List[str] = Field(default_factory=list, description="推荐的工具")

    class Config:
        json_encoders = {
            QueryType: lambda v: v.value,
            Capability: lambda v: v.value
        }


class QueryIntent(BaseModel):
    """查询意图分析结果"""

    # 原始查询
    query: str = Field(..., description="用户查询")

    # 查询类型
    query_type: QueryType = Field(..., description="查询类型")

    # 提取的信息
    entities: List[str] = Field(default_factory=list, description="提取的实体")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    domain: Optional[str] = Field(None, description="领域（如：技术、医疗、金融）")

    # 复杂度评估
    complexity: ComplexityLevel = Field(default=ComplexityLevel.MEDIUM)

    # 能力需求
    requires: List[Capability] = Field(default_factory=list, description="所需能力")
    preferred_tools: List[str] = Field(default_factory=list, description="推荐的工具")

    # 元数据
    confidence: float = Field(default=0.8, ge=0, le=1, description="分析置信度 0-1")
    estimated_difficulty: float = Field(default=0.5, ge=0, le=1, description="预估难度 0-1")

    # 推理过程（用于可解释性）
    reasoning: Optional[str] = Field(default=None, description="分析推理过程")

    # 建议的执行策略
    suggested_strategy: Optional[str] = Field(default=None, description="建议的执行策略")

    # 多意图支持
    has_multiple_intents: bool = Field(default=False, description="是否包含多个意图")
    sub_intents: List[SubIntent] = Field(default_factory=list, description="子意图列表")

    class Config:
        json_encoders = {
            QueryType: lambda v: v.value,
            ComplexityLevel: lambda v: v.value,
            Capability: lambda v: v.value
        }


class StrategyType(str, Enum):
    """执行策略类型"""
    SIMPLE = "simple"                   # 简单策略：直接检索
    GRAPH = "graph"                     # 图谱策略：图谱检索
    HYBRID = "hybrid"                   # 混合策略：图谱+向量
    ADAPTIVE = "adaptive"               # 自适应：根据中间结果调整


class ExecutionPlan(BaseModel):
    """执行计划"""

    # 计划信息
    plan_id: str = Field(..., description="计划ID")
    query: str = Field(..., description="原始查询")

    # 策略选择
    strategy_type: StrategyType = Field(default=StrategyType.SIMPLE)
    description: str = Field(default="", description="策略描述")

    # 执行步骤
    steps: List[str] = Field(default_factory=list, description="执行步骤描述")

    # 预估
    estimated_duration: float = Field(default=5.0, description="预估时长（秒）")
    estimated_cost: float = Field(default=0.001, description="预估Token成本")

    class Config:
        json_encoders = {
            StrategyType: lambda v: v.value
        }
