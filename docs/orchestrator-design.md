# Agentic Orchestrator 设计文档

## 文档概述

**版本**: v1.1
**创建日期**: 2026-03-11
**最后更新**: 2026-03-11
**更新内容**: 新增多意图理解设计章节（第四章）

---

## 一、概述

### 1.1 什么是 Agentic Orchestrator

Agentic Orchestrator（Agent 编排器）是系统的"大脑"，负责：
- 理解用户查询意图
- 规划最优检索策略
- 协调多个 Agent/Skills
- 整合多源信息
- 生成最终回答

### 1.2 设计目标

| 目标 | 说明 |
|------|------|
| **智能决策** | 根据查询自动选择最优策略 |
| **动态编排** | 灵活组合不同的 Skills 和 Tools |
| **可解释性** | 决策过程透明可追踪 |
| **容错性** | 部分失败时仍能给出结果 |
| **可扩展** | 新增策略无需修改核心逻辑 |

### 1.3 在系统中的位置

```
用户查询
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│              Agentic Orchestrator ◄──── 本文档              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  意图理解  │  策略规划  │  协调执行  │  结果整合     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
    │
    ├─────────────────────────────────────────────────────────┐
    │                                                         │
    ▼                                                         ▼
┌──────────────────┐                              ┌──────────────────┐
│   Skills 系统     │                              │  Function Calling  │
│  - 查询分析        │                              │  - 工具调用        │
│  - 多跳推理        │                              │  - MCP 数据源      │
│  - 上下文整合      │                              │  - 并行执行        │
└──────────────────┘                              └──────────────────┘
    │                                                         │
    └─────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │   GraphRAG 核心     │
                  │   (图谱+向量检索)   │
                  └─────────────────────┘
```

---

## 二、架构设计

### 2.1 核心组件

```python
class AgenticOrchestrator:
    """Agent 编排器"""

    def __init__(self):
        # 组件
        self.intent_analyzer: IntentAnalyzer
        self.strategy_planner: StrategyPlanner
        self.skill_coordinator: SkillCoordinator
        self.result_synthesizer: ResultSynthesizer

        # 配置
        self.config: OrchestratorConfig

        # 状态
        self.state: OrchestratorState
```

### 2.2 组件详解

#### 2.2.1 IntentAnalyzer（意图分析器）

```python
class IntentAnalyzer:
    """意图分析器"""

    async def analyze(self, query: str) -> QueryIntent:
        """
        分析查询意图

        Returns:
            QueryIntent: 查询意图分析结果
        """
```

**输出结构**：
```python
{
    "query_type": "fact | relation | reasoning | open_ended",
    "entities": ["实体1", "实体2"],
    "keywords": ["关键词1", "关键词2"],
    "domain": "技术 | 医疗 | 金融 ...",
    "complexity": "low | medium | high",
    "urgency": "normal | high",
    "requires": [
        "graph_search",
        "vector_search",
        "realtime_data",
        "multi_hop_reasoning"
    ],
    "estimated_difficulty": 0.7  # 0-1
}
```

#### 2.2.2 StrategyPlanner（策略规划器）

```python
class StrategyPlanner:
    """策略规划器"""

    async def plan(
        self,
        intent: QueryIntent,
        available_capabilities: List[str]
    ) -> ExecutionStrategy:
        """
        规划执行策略

        Returns:
            ExecutionStrategy: 执行策略
        """
```

**策略类型**：
```python
class StrategyType(str, Enum):
    """策略类型"""
    SIMPLE = "simple"           # 简单单步检索
    PARALLEL = "parallel"       # 并行多源检索
    SEQUENTIAL = "sequential"   # 串行依赖检索
    ADAPTIVE = "adaptive"       # 自适应策略
```

**策略输出**：
```python
{
    "strategy_type": "parallel",
    "steps": [
        {
            "step_id": "step_1",
            "skills": ["query_analysis"],
            "tools": [],
            "parallel_group": ["graph_retrieval", "vector_search"]
        },
        {
            "step_id": "step_2",
            "skills": ["context_synthesis"],
            "tools": [],
            "depends_on": ["step_1"]
        },
        {
            "step_id": "step_3",
            "skills": ["quality_assessment"],
            "tools": [],
            "depends_on": ["step_2"]
        }
    ],
    "estimated_duration": 3.5,
    "fallback_strategy": "simple_rag"
}
```

#### 2.2.3 SkillCoordinator（技能协调器）

```python
class SkillCoordinator:
    """技能协调器"""

    async def coordinate(
        self,
        strategy: ExecutionStrategy,
        query: str
    ) -> CoordinationResult:
        """
        协调技能执行

        Args:
            strategy: 执行策略
            query: 原始查询

        Returns:
            CoordinationResult: 协调执行结果
        """
```

#### 2.2.4 ResultSynthesizer（结果整合器）

```python
class ResultSynthesizer:
    """结果整合器"""

    async def synthesize(
        self,
        query: str,
        coordination_result: CoordinationResult,
        llm_context: str
    ) -> FinalResponse:
        """
        整合结果生成最终回答

        Returns:
            FinalResponse: 最终回答
        """
```

---

## 三、工作流程

### 3.1 完整处理流程

```
用户查询: "BERT和GPT-4有什么共同点？"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. 意图分析 (IntentAnalyzer)                                │
│    输入: "BERT和GPT-4有什么共同点？"                            │
│    输出:                                                    │
│    {                                                      │
│      query_type: "reasoning_query",                      │
│      entities: ["BERT", "GPT-4"],                          │
│      requires: ["graph_search", "multi_hop_reasoning"]    │
│    }                                                     │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 策略规划 (StrategyPlanner)                                │
│    输入: 意图分析结果                                          │
│    输出:                                                    │
│    {                                                      │
│      strategy_type: "sequential",                          │
│      steps: [                                            │
│        {skills: ["graph_multi_hop"], tools: []},          │
│        {skills: ["context_synthesis"], tools: []},         │
│        {skills: ["response_generation"], tools: []}        │
│      ]                                                   │
│    }                                                     │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 技能协调执行 (SkillCoordinator)                            │
│    Step 1: graph_multi_hop                                  │
│      └─ BERT → [基于] → Transformer ←─ [基于] ← GPT-4      │
│    Step 2: context_synthesis                               │
│      └─ 整合图谱路径和上下文                                  │
│    Step 3: response_generation                              │
│      └─ 生成最终回答                                          │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 结果整合 (ResultSynthesizer)                              │
│    输入: 技能执行结果                                        │
│    输出:                                                    │
│    {                                                      │
│      answer: "BERT和GPT-4都基于Transformer架构...",       │
│      reasoning_path: ["BERT → Transformer", "GPT-4 → Transformer"], │
│      confidence: 0.92,                                     │
│      sources: ["图谱节点: Transformer"]                   │
│    }                                                     │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 决策树

```
用户查询
    │
    ▼
查询类型判断
    │
    ├─→ 简单事实查询
│   └─→ 策略: 向量检索 → LLM 生成
│
├─→ 关系查询 (A和B的关系?)
│   └─→ 策略: 图谱检索 → 路径提取 → LLM 生成
│
├─→ 推理查询 (A的根源?)
│   └─→ 策略: 多跳推理 → 子图提取 → LLM 生成
│
├─→ 聚合查询 (X领域的所有Y)
│   └─→ 策略: 社区发现 → 批量检索 → LLM 生成
│
└─→ 开放查询
    └─→ 策略: 混合检索 → 结果融合 → LLM 生成
```

---

## 四、多意图理解设计

### 4.1 什么是多意图查询

**多意图查询**是指用户在一条查询中提出了多个独立或相关的问题，需要分别处理后再给出综合答案。

#### 4.1.1 多意图查询的特征

| 特征 | 说明 | 示例关键词 |
|------|------|-----------|
| **连接词** | 使用连接词连接多个问题 | 以及、还有、另外、同时、并且 |
| **标点符号** | 使用特定标点分隔问题 | ；（分号）、， followed by 另一个问题 |
| **语义关联** | 多个问题语义上相关但需要不同处理 | 系统问题 + 实时查询 |

#### 4.1.2 多意图查询类型

```python
class MultiIntentType(str, Enum):
    """多意图类型"""
    SEQUENTIAL = "sequential"       # 串行：依次处理
    PARALLEL = "parallel"          # 并行：同时处理
    DEPENDENT = "dependent"        # 依赖：前一个结果影响后一个
```

### 4.2 多意图检测

#### 4.2.1 基于规则的快速检测

```python
class MultiIntentDetector:
    """多意图检测器"""

    # 多意图连接词
    KEYWORDS = ["以及", "还有", "另外", "同时", "，然后", "并且"]

    @staticmethod
    def detect(query: str) -> bool:
        """检测是否为多意图查询"""
        return any(keyword in query for keyword in MultiIntentDetector.KEYWORDS)
```

#### 4.2.2 基于LLM的智能分解

```python
async def decompose_multi_intent(query: str) -> List[SubIntent]:
    """
    分解多意图查询

    Returns:
        List[SubIntent]: 子意图列表
    """
```

**Prompt 设计**：
```
请分析以下查询是否包含多个意图，如果是，请将其分解：

查询："{query}"

请按以下格式输出：
{{
  "has_multiple_intents": true/false,
  "sub_intents": [
    {{"sub_query": "...", "intent_type": "...", "requires": [...]}}
  ]
}}
```

### 4.3 ReAct 范式下的多意图处理

#### 4.3.1 核心挑战

在 ReAct 范式中处理多意图查询的核心挑战是：

1. **LLM 倾向于提前终止** - 回答第一个问题后就给出 Answer
2. **部分答案识别困难** - 难以判断 Answer 是否覆盖所有意图
3. **迭代次数限制** - 需要足够的轮次处理多个意图

#### 4.3.2 解决方案：部分答案检测与持续处理

```python
class ReActAgent:
    """ReAct 智能体 - 支持多意图处理"""

    MULTI_INTENT_KEYWORDS = ["以及", "还有", "另外", "同时", "，然后", "并且"]
    MAX_ITERATIONS = 10  # 增加迭代次数以支持多意图

    async def run(self, query: str, history: Optional[List[Dict]] = None) -> ReActResult:
        """
        运行 ReAct Agent - 支持多意图处理

        核心逻辑：
        1. 检测是否为多意图查询
        2. 收到 Answer 时检查是否为部分答案
        3. 如果是部分答案，提示 LLM 继续处理剩余意图
        """
        is_multi_intent = self._detect_multi_intent(query)
        processed_actions = []

        for iteration in range(self.max_iterations):
            response = await self.llm.chat(messages)
            thought, action, action_params, answer = self._parse_response(response)

            if answer:
                # 关键：检查是否为部分答案
                if is_multi_intent and not self._check_answer_coverage(query, answer, processed_actions):
                    # 标记为部分答案，继续循环
                    steps.append(ReActStep("partial_answer", answer))
                    messages.append({
                        "role": "user",
                        "content": f"你只回答了问题的一部分。原始问题是：{query}\n\n请继续处理问题的其他部分。"
                    })
                    continue

                # 完整答案，返回结果
                return ReActResult(answer=answer, steps=steps)

            if action:
                # 执行工具并添加观察结果
                ...
```

#### 4.3.3 答案覆盖度检查

```python
def _check_answer_coverage(self, query: str, answer: str, processed_actions: List[str]) -> bool:
    """
    检查答案是否覆盖了查询的所有部分

    启发式规则：
    1. 非多意图查询 → 直接返回 True
    2. 答案长度过短（<50字符）且查询包含"以及" → 可能未覆盖
    3. 已执行操作数量 < 预期数量 → 可能未覆盖

    Returns:
        True 如果答案完整，False 如果需要继续
    """
    if not self._detect_multi_intent(query):
        return True

    # 简单启发式：答案太短可能没覆盖所有意图
    if len(answer) < 50 and "以及" in query:
        return False

    return True
```

### 4.4 多意图处理流程

#### 4.4.1 完整流程图

```
用户查询: "你底层使用的什么LLM名字，以及无锡市今天的天气"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. 多意图检测                                               │
│    检测到关键词"以及" → 标记为多意图查询                      │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 第一轮迭代                                                │
│    Thought: 识别出两个问题                                  │
│    └─ 问题1: 系统问题（LLM名字）                            │
│    └─ 问题2: 实时查询（天气）                                │
│    Partial_Answer: "我底层使用的是智谱AI GLM-4"              │
│    → 系统检测到部分答案，提示继续                            │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 第二轮迭代                                                │
│    Thought: 需要处理第二个问题（天气）                        │
│    Action: web_search({"query": "无锡市今天天气"})           │
│    Observation: 获取天气结果                                  │
│    Thought: 分析观察结果                                     │
│    Answer: 综合两个问题的完整答案                             │
│    → 答案覆盖度检查通过，返回结果                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4.4.2 步骤类型扩展

```python
@dataclass
class ReActStep:
    """ReAct 执行步骤"""
    step_type: str  # 扩展类型：
                     # - "user": 用户查询
                     # - "thought": 思考
                     # - "action": 行动
                     # - "observation": 观察
                     # - "partial_answer": 部分答案（多意图）
                     # - "answer": 完整答案
                     # - "error": 错误
    content: str
    data: Optional[Dict[str, Any]] = None
```

### 4.5 系统提示词优化

#### 4.5.1 多意图处理指令

```
## 多问题处理（必须遵守）

如果用户问了多个问题（用"以及"、"还有"、"同时"等连接）：
1. **必须逐一处理每个问题**
2. **不能只回答第一个问题就结束**
3. **每个问题都可能需要调用工具**
4. **必须确保所有问题都有答案后，才能给出最终 Answer**

错误示例：
用户: "你使用什么模型，以及无锡市天气？"
**Answer:** 我使用的是智谱GLM-4。  ← 错误！遗漏了天气问题

正确示例：
用户: "你使用什么模型，以及无锡市天气？"
**Answer:** 我使用的是智谱GLM-4。关于无锡市的天气，让我查询一下...
```

#### 4.5.2 部分答案提示

当检测到部分答案时，系统会自动提示：

```
**User:** 你只回答了问题的一部分。
原始问题是：你底层使用的什么LLM名字，以及无锡市今天的天气如何？

你的答案：我底层使用的是智谱AI GLM-4大语言模型。

请继续处理问题的其他部分。
```

### 4.6 实现示例

#### 4.6.1 多意图查询示例

| 查询 | 意图数量 | 处理方式 |
|------|---------|---------|
| 你使用什么模型 | 1 | 直接回答（系统问题） |
| 无锡市今天天气 | 1 | web_search → Answer |
| 模型和天气 | 2 | Partial_Answer → web_search → Answer |
| A、B、C三个比较 | 3 | Partial → Partial → Partial → Answer |

#### 4.6.2 执行追踪示例

```json
{
  "query": "你底层使用的什么LLM名字，以及无锡市今天的天气如何？",
  "steps": [
    {"step_type": "user", "content": "你底层使用的什么LLM名字，以及..."},
    {"step_type": "thought", "content": "用户询问了两个问题..."},
    {"step_type": "partial_answer", "content": "我底层使用的是智谱AI GLM-4..."},
    {"step_type": "thought", "content": "用户询问无锡市今天的天气..."},
    {"step_type": "action", "content": "web_search: {\"query\": \"无锡市今天天气\"}"},
    {"step_type": "observation", "content": "1. 无锡市今日天气预报..."},
    {"step_type": "thought", "content": "根据观察结果..."},
    {"step_type": "answer", "content": "根据搜索结果，无锡市今天的天气是..."}
  ],
  "success": true
}
```

### 4.7 最佳实践

#### 4.7.1 设计原则

| 原则 | 说明 |
|------|------|
| **不强制分割** | 让 LLM 自然处理，只在需要时干预 |
| **渐进式处理** | 允许部分答案，引导完成剩余部分 |
| **可观察性** | 记录 partial_answer 步骤，方便调试 |
| **容错性** | 即使检测失败，也能通过迭代继续处理 |

#### 4.7.2 参数调优

```python
# 多意图处理相关参数
MAX_ITERATIONS = 10          # 迭代次数：单意图5次，多意图10次
ANSWER_MIN_LENGTH = 50       # 最短答案长度（用于覆盖度检查）
COVERAGE_CHECK_ENABLED = True # 是否启用覆盖度检查
```

---

## 五、数据模型

### 4.1 查询意图

```python
class QueryIntent(BaseModel):
    """查询意图"""

    # 基础信息
    query: str                       # 原始查询
    query_type: QueryType            # 查询类型
    complexity: ComplexityLevel       # 复杂度

    # 提取的信息
    entities: List[str]              # 提取的实体
    keywords: List[str]              # 关键词
    domain: Optional[str]             # 领域

    # 能力需求
    requires: List[Capability]        # 所需能力
    preferred_tools: List[str]       # 偏好的工具

    # 元数据
    confidence: float                 # 分析置信度
    estimated_difficulty: float      # 预估难度


class QueryType(str, Enum):
    """查询类型"""
    FACT = "fact"                     # 事实查询: "什么是X?"
    RELATION = "relation"             # 关系查询: "X和Y的关系?"
    REASONING = "reasoning"           # 推理查询: "为什么X?"
    AGGREGATION = "aggregation"       # 聚合查询: "所有X"
    OPEN_ENDED = "open_ended"        # 开放查询: "介绍一下X"


class Capability(str, Enum):
    """能力需求"""
    GRAPH_SEARCH = "graph_search"
    VECTOR_SEARCH = "vector_search"
    MULTI_HOP = "multi_hop_reasoning"
    REALTIME_DATA = "realtime_data"
    CODE_EXECUTION = "code_execution"
```

### 4.2 执行策略

```python
class ExecutionStrategy(BaseModel):
    """执行策略"""

    # 策略信息
    strategy_type: StrategyType
    description: str

    # 执行步骤
    steps: List[ExecutionStep]

    # 性能估计
    estimated_duration: float
    estimated_cost: float

    # 容错
    fallback_strategy: Optional[str]

    # 配置
    config: Dict[str, Any] = {}


class ExecutionStep(BaseModel):
    """执行步骤"""

    step_id: str
    description: str

    # 技能和工具
    skills: List[str] = []
    tools: List[str] = []

    # 执行控制
    parallel_group: List[str] = []     # 可并行的子步骤
    depends_on: List[str] = []        # 依赖的步骤

    # 配置
    config: Dict[str, Any] = {}
```

### 4.3 协调结果

```python
class CoordinationResult(BaseModel):
    """协调执行结果"""

    # 执行信息
    strategy: ExecutionStrategy
    execution_id: str
    start_time: datetime
    end_time: datetime

    # 各步骤结果
    step_results: List[StepResult]

    # 聚合结果
    aggregated_context: Dict[str, Any]

    # 执行统计
    total_duration: float
    steps_completed: int
    steps_failed: int
```

### 4.4 最终回答

```python
class FinalResponse(BaseModel):
    """最终回答"""

    # 核心回答
    answer: str

    # 推理过程
    reasoning_path: List[str]       # 推理链
    evidence: List[str]             # 支撑证据

    # 元信息
    confidence: float               # 置信度
    sources: List[str]              # 信息来源
    strategy_used: str              # 使用的策略

    # 质量指标
    completeness: float             # 完整性
    accuracy: float                 # 准确性（如果可验证）
```

---

## 六、策略模式

### 5.1 策略类型详解

#### 5.1.1 Simple Strategy（简单策略）

**适用场景**：简单事实查询，无需复杂推理

```
查询: "什么是Transformer？"
    │
    ▼
┌─────────────────────────┐
│  向量检索 (5篇文档)       │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  LLM 生成回答            │
└─────────────────────────┘
```

#### 51.2 Graph Strategy（图谱策略）

**适用场景**：关系查询、多跳推理

```
查询: "BERT和GPT-4有什么共同点？"
    │
    ▼
┌─────────────────────────┐
│  实体定位                 │
│  - BERT                   │
│  - GPT-4                  │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  多跳推理                 │
│  - BERT →?→ Transformer   │
│  - GPT-4 →?→ Transformer  │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  共同祖先发现             │
│  - LCA = Transformer      │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  推理链构建               │
│  - 整合证据               │
│  - 生成回答               │
└─────────────────────────┘
```

#### 5.1.3 Hybrid Strategy（混合策略）

**适用场景**：需要图谱和向量检索

```
查询: "深度学习在医疗影像中的应用进展"
    │
    ▼
┌─────────────────────────┐        ┌─────────────────────────┐
│  图谱检索                 │        │  向量检索                 │
│  - 医疗实体               │        │  - 相关论文               │
│  - 关系网络               │        │  - 应用案例               │
└─────────────────────────┘        └─────────────────────────┘
    │                                      │
    └──────────────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  结果融合与排序           │
        │  - 去重                   │
        │  - 相关性排序             │
        └─────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐
        │  LLM 生成综合回答         │
        └─────────────────────────┘
```

#### 5.1.4 Adaptive Strategy（自适应策略）

**适用场景**：复杂查询，需要根据中间结果调整

```python
class AdaptiveStrategy:
    """自适应策略"""

    async def execute(self, query: str):
        # 初始计划
        initial_plan = await self.create_initial_plan(query)

        # 执行并监控
        results = []
        for step in initial_plan:
            result = await self.execute_step(step, context=results)

            # 评估结果质量
            quality = await self.assess_quality(result)

            # 如果质量不满足，调整策略
            if quality < threshold:
                next_step = await self.plan_adjustment(query, results)
                return await self.execute_with_adjusted_plan(results, next_step)

            results.append(result)

        return self.synthesize(results)
```

---

## 七、LLM 集成

### 6.1 意图分析 Prompt

```python
INTENT_ANALYSIS_PROMPT = """你是一个查询意图分析专家。请分析用户查询，输出结构化的意图信息。

用户查询：{query}

请按以下格式分析：

1. 查询类型：fact | relation | reasoning | aggregation | open_ended
2. 提取的实体：实体1, 实体2, ...
3. 关键词：关键词1, 关键词2, ...
4. 涉及领域：（如果可识别）
5. 所需能力：
   - graph_search: 图谱检索
   - vector_search: 向量检索
   - multi_hop: 多跳推理
   - realtime: 实时数据
6. 复杂度：low | medium | high
7. 推荐工具：（具体工具名称）

以 JSON 格式输出。
"""
```

### 6.2 策略规划 Prompt

```python
STRATEGY_PLANNING_PROMPT = """你是一个检索策略规划专家。根据查询意图，规划最优的执行策略。

查询意图：
{intent_summary}

可用能力：
{available_capabilities}

请规划执行策略，考虑：
1. 效率：最短路径获得准确答案
2. 准确性：确保信息来源可靠
3. 容错：部分失败时的备选方案

输出格式：
{
  "strategy_type": "simple | graph | hybrid | adaptive",
  "steps": [
    {
      "step_id": "step_1",
      "description": "...",
      "skills": ["..."],
      "tools": ["..."],
      "parallel_group": ["..."]  # 如果可并行
    }
  ],
  "estimated_duration": 3.5,
  "fallback_strategy": "..."
}
"""
```

### 6.3 结果整合 Prompt

```python
RESULT_SYNTHESIS_PROMPT = """你是一个信息整合专家。请根据多源检索结果，生成准确、完整的回答。

用户查询：{query}

检索结果：
{retrieval_results}

图谱推理路径：
{reasoning_path}

请生成回答，要求：
1. 准确：基于检索结果，不编造信息
2. 完整：回答用户的所有问题
3. 清晰：结构化呈现，逻辑清晰
4. 可追溯：标注信息来源

如果检索结果不足以回答，请明确告知。
"""
```

---

## 八、API 接口

### 7.1 主要端点

```python
# 处理查询（主接口）
POST /api/v1/orchestrate/query
{
  "query": "BERT和GPT-4有什么共同点？",
  "options": {
    "strategy": "auto",  # auto | graph | vector | hybrid
    "explain": true     # 是否返回决策过程
  }
}

# 获取决策过程
GET /api/v1/orchestrate/{execution_id}/trace

# 获取策略选项
GET /api/v1/orchestrate/strategies

# 设置配置
POST /api/v1/orchestrate/config
```

### 7.2 请求/响应示例

**处理查询请求**：
```json
POST /api/v1/orchestrate/query
{
  "query": "BERT和GPT-4有什么共同点？"
}
```

**响应**：
```json
{
  "execution_id": "exec_12345",
  "answer": "BERT和GPT-4都基于Transformer架构...",
  "reasoning_path": [
    "BERT → [基于] → Transformer",
    "GPT-4 → [基于] → Transformer"
  ],
  "sources": ["图谱节点: Transformer"],
  "confidence": 0.92,
  "strategy_used": "graph_multi_hop",
  "decision_process": {
    "intent": {...},
    "strategy": {...},
    "steps_executed": [...]
  }
}
```

---

## 九、可观测性

### 8.1 执行追踪

```python
class ExecutionTrace:
    """执行追踪"""

    execution_id: str
    query: str
    start_time: datetime
    end_time: datetime

    # 决策过程
    intent_analysis: QueryIntent
    strategy: ExecutionStrategy
    decision_rationale: str

    # 执行详情
    steps: List[StepTrace]

    # 性能指标
    total_duration: float
    step_durations: List[float]

    # 质量指标
    confidence: float
    completeness: float
```

### 8.2 可视化决策过程

```json
{
  "decision_tree": {
    "nodes": [
      {
        "id": "intent",
        "label": "意图分析",
        "result": "reasoning_query"
      },
      {
        "id": "strategy",
        "label": "策略选择",
        "result": "graph_multi_hop",
        "reason": "涉及实体关系，需要多跳推理"
      },
      {
        "id": "execution",
        "label": "执行过程",
        "steps": [...]
      }
    ],
    "edges": [
      {"from": "intent", "to": "strategy"},
      {"from": "strategy", "to": "execution"}
    ]
  }
}
```

---

## 十、最佳实践

### 9.1 决策原则

| 原则 | 说明 | 示例 |
|------|------|------|
| **准确性优先** | 宁可多花时间，确保结果准确 | 复杂查询使用图谱而非向量 |
| **效率平衡** | 简单查询用简单策略 | "什么是X" 用向量检索 |
| **渐进式** | 先快速回答，再深入挖掘 | 简单RAG → GraphRAG 补充 |
| **可解释** | 向用户展示决策过程 | 返回推理链和证据来源 |
| **容错性** | 部分失败时给出最佳答案 | 图谱失败时用向量补充 |

### 9.2 错误处理

```python
class ErrorHandler:
    """错误处理器"""

    async def handle_step_failure(
        self,
        step: ExecutionStep,
        error: Exception,
        context: CoordinationResult
    ) -> RecoveryAction:
        """
        处理步骤失败

        Returns:
            RecoveryAction: 恢复动作
        """
        # 1. 记录错误
        self.trace_error(step, error)

        # 2. 判断是否可恢复
        if self.is_recoverable(error):
            return await self.attempt_recovery(step, context)
        else:
            return await self.execute_fallback(step, context)
```

---

## 十一、性能优化

### 10.1 优化策略

| 策略 | 说明 | 效果 |
|------|------|------|
| **缓存意图分析** | 相似查询复用策略 | 减少 LLM 调用 |
| **并行执行** | 无依赖步骤并行执行 | 减少总耗时 |
| **提前返回** | 简单查询快速返回 | 提升响应速度 |
| **增量处理** | 先返回基础结果，再补充 | 改善用户体验 |
| **智能降级** | 复杂策略失败时简化 | 确保总能返回结果 |

### 10.2 性能指标

```python
class PerformanceMetrics:
    """性能指标"""

    # 响应时间
    p50_latency: float  # 50% 请求 < 2s
    p95_latency: float  # 95% 请求 < 5s
    p99_latency: float  # 99% 请求 < 10s

    # 质量指标
    strategy_accuracy: float    # 策略选择准确率
    user_satisfaction: float    # 用户满意度

    # 资源使用
    avg_llm_calls: float       # 平均 LLM 调用次数
    avg_tool_calls: float       # 平均工具调用次数
```

---

## 十二、与系统集成

### 11.1 与 Skills 系统集成

```python
class AgenticOrchestrator:
    def __init__(self):
        # 获取技能注册表
        self.skill_registry = get_skill_registry()

        # 预加载关键技能
        self._load_skills()

    async def process(self, query: str):
        # 1. 使用查询分析技能
        intent = await self.skill_registry.execute(
            "query_analysis",
            SkillContext(inputs={"query": query})
        )

        # 2. 规划策略
        strategy = await self._plan_strategy(intent)

        # 3. 执行技能工作流
        result = await self._execute_workflow(strategy)

        return result
```

### 11.2 与 GraphRAG 集成

```python
class GraphRAGOrchestrationStrategy:
    """GraphRAG 编排策略"""

    async def execute(self, query: str):
        # 1. 分析查询
        intent = await self.analyze_query(query)

        # 2. 根据意图选择 GraphRAG 策略
        if intent.requires_graph and intent.requires_vector:
            results = await self._hybrid_retrieval(query)
        elif intent.requires_graph:
            results = await self._graph_only_retrieval(query)
        else:
            results = await self._vector_only_retrieval(query)

        # 3. 生成回答
        response = await self._generate_response(query, results)

        return response
```

---

## 十三、扩展指南

### 12.1 添加新策略

```python
class CustomStrategy(Strategy):
    """自定义策略"""

    name = "custom_strategy"
    description = "自定义策略描述"

    async def plan(
        self,
        intent: QueryIntent,
        context: OrchestratorContext
    ) -> ExecutionStrategy:
        # 实现策略规划逻辑
        return ExecutionStrategy(...)

    async def execute(
        self,
        strategy: ExecutionStrategy,
        query: str
    ) -> FinalResponse:
        # 实现执行逻辑
        return FinalResponse(...)


# 注册策略
orchestrator = get_orchestrator()
orchestrator.register_strategy(CustomStrategy())
```

### 12.2 添加新的意图类型

```python
class CustomQueryType(str, Enum):
    """自定义查询类型"""
    CUSTOM_TYPE = "custom_type"


# 扩展意图分析器
class ExtendedIntentAnalyzer(IntentAnalyzer):
    async def analyze(self, query: str) -> QueryIntent:
        # 先用基础分析
        intent = await super().analyze(query)

        # 添加自定义逻辑
        if self._is_custom_type(query):
            intent.query_type = QueryType.CUSTOM_TYPE

        return intent
```

---

## 十四、测试策略

### 13.1 单元测试

```python
# 测试意图分析
async def test_intent_analysis():
    orchestrator = get_orchestrator()

    intent = await orchestrator.analyze_intent(
        "BERT和GPT-4有什么共同点？"
    )

    assert intent.query_type == QueryType.REASONING
    assert "BERT" in intent.entities
    assert "GPT-4" in intent.entities
```

### 13.2 集成测试

```python
# 测试完整流程
async def test_end_to_end():
    orchestrator = get_orchestrator()

    response = await orchestrator.process(
        "Transformer在医疗影像中的应用进展"
    )

    assert response.answer
    assert response.confidence > 0.7
    assert len(response.sources) > 0
```

---

*文档版本：v1.1*
*创建日期：2026-03-11*
*更新日期：2026-03-11*
*更新内容：新增第四章"多意图理解设计"*
