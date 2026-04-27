# Skills 系统设计文档

## 文档概述

**版本**: v1.0
**创建日期**: 2026-03-11
**最后更新**: 2026-03-11

---

## 一、概述

### 1.1 什么是 Skills 系统

Skills 系统是 Agent 能力的模块化封装，将复杂的推理、检索、分析等能力分解为可组合、可复用的技能单元。

### 1.2 设计目标

| 目标 | 说明 |
|------|------|
| **模块化** | 每个技能专注单一职责，易于测试和维护 |
| **可组合** | 多个技能可以组合完成复杂任务 |
| **可扩展** | 新增技能无需修改核心框架 |
| **可观测** | 技能执行过程可追踪、可调试 |
| **动态加载** | 运行时动态学习和遗忘技能 |

### 1.3 与传统函数的区别

| 维度 | 传统函数 | Skill |
|------|---------|-------|
| 输入输出 | 固定参数 | 结构化 Input/Output Schema |
| 元数据 | 无 | 名称、描述、类别、版本 |
| 执行追踪 | 无 | 完整的执行日志和指标 |
| 错误处理 | 异常 | 结构化错误信息和恢复策略 |
| 组合能力 | 手动调用 | 支持工作流编排 |

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Skills 系统                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Skill Registry                        │   │
│  │  - 技能注册  -  元数据管理  -  依赖解析  -  版本控制      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Skill Executor                          │   │
│  │  - 执行调度  -  超时控制  -  错误处理  -  结果验证       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Skill Composer                         │   │
│  │  - 技能组合  -  工作流编排  -  数据传递                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  预置 Skills (Built-in Skills)                                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│  │查询分析  │ │多跳推理  │ │上下文整合│ │质量评估  │         │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### 2.2.1 Skill 基类

```python
class Skill(ABC):
    """技能基类"""

    # 元数据
    name: str                          # 技能名称
    description: str                   # 技能描述
    category: SkillCategory            # 技能分类
    version: str                       # 版本号
    author: str                        # 作者

    # 执行定义
    input_schema: BaseModel            # 输入 Schema
    output_schema: BaseModel           # 输出 Schema

    # 配置
    timeout: int = 30                  # 超时时间
    retry_count: int = 0               # 重试次数
    dependencies: List[str] = []      # 依赖的其他技能

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行技能"""
        pass
```

#### 2.2.2 Skill Context（技能上下文）

```python
class SkillContext:
    """技能执行上下文"""

    # 输入数据
    inputs: Dict[str, Any]

    # 共享状态
    shared_memory: Dict[str, Any]

    # 执行历史
    execution_history: List[SkillExecution]

    # 元数据
    metadata: Dict[str, Any]

    # 配置
    config: Dict[str, Any]

    def get_input(self, key: str, default=None):
        """获取输入参数"""

    def set_output(self, key: str, value: Any):
        """设置输出结果"""

    def get_shared(self, key: str, default=None):
        """获取共享状态"""

    def set_shared(self, key: str, value: Any):
        """设置共享状态"""
```

#### 2.2.3 Skill Result（技能结果）

```python
class SkillResult:
    """技能执行结果"""

    # 执行状态
    success: bool
    status: str                       # success/failed/partial

    # 输出数据
    outputs: Dict[str, Any]

    # 执行信息
    duration: float                   # 执行时长
    steps: List[SkillStep]            # 执行步骤

    # 错误信息
    error: Optional[str] = None
    error_code: Optional[str] = None

    # 元数据
    metadata: Dict[str, Any] = {}
```

---

## 三、技能分类

### 3.1 技能类型

```python
class SkillCategory(str, Enum):
    """技能分类"""
    ANALYSIS = "analysis"           # 分析类
    RETRIEVAL = "retrieval"         # 检索类
    REASONING = "reasoning"         # 推理类
    SYNTHESIS = "synthesis"         # 综合类
    VALIDATION = "validation"       # 验证类
    GENERATION = "generation"       # 生成类
    UTILITY = "utility"             # 工具类
```

### 3.2 预置技能定义

#### 3.2.1 查询分析技能 (QueryAnalysisSkill)

```python
class QueryAnalysisSkill(Skill):
    """查询分析技能"""

    name = "query_analysis"
    description = "分析用户查询的意图和类型"
    category = SkillCategory.ANALYSIS

    input_schema = QueryAnalysisInput
    output_schema = QueryAnalysisOutput

    async def execute(self, context: SkillContext) -> SkillResult:
        # 1. 识别查询类型
        # 2. 提取关键实体
        # 3. 判断所需能力
        # 4. 生成分析结果
```

**输出结构**：
```python
{
    "query_type": "fact_query | relation_query | reasoning_query | open_ended",
    "entities": ["实体1", "实体2"],
    "keywords": ["关键词1", "关键词2"],
    "requires_capabilities": ["graph_search", "vector_search"],
    "complexity": "low | medium | high",
    "estimated_tools": ["query_knowledge_graph", "vector_search"]
}
```

#### 3.2.2 多跳推理技能 (MultiHopReasoningSkill)

```python
class MultiHopReasoningSkill(Skill):
    """多跳推理技能"""

    name = "multi_hop_reasoning"
    description = "在知识图谱上进行多跳推理"
    category = SkillCategory.REASONING

    dependencies = ["graph_retrieval"]

    async def execute(self, context: SkillContext) -> SkillResult:
        # 1. 起始实体
        # 2. 逐跳遍历
        # 3. 路径验证
        # 4. 推理链生成
```

**输出结构**：
```python
{
    "reasoning_path": [
        {"hop": 1, "entity": "BERT", "relation": "基于", "target": "Transformer"},
        {"hop": 2, "entity": "GPT-4", "relation": "基于", "target": "Transformer"}
    ],
    "conclusion": "BERT和GPT-4都基于Transformer架构",
    "confidence": 0.95,
    "evidence": ["路径1的证据", "路径2的证据"]
}
```

#### 3.2.3 上下文整合技能 (ContextSynthesisSkill)

```python
class ContextSynthesisSkill(Skill):
    """上下文整合技能"""

    name = "context_synthesis"
    description = "整合多源上下文信息"
    category = SkillCategory.SYNTHESIS

    async def execute(self, context: SkillContext) -> SkillResult:
        # 1. 接收多源上下文
        # 2. 去重和排序
        # 3. 格式化整合
        # 4. 生成最终上下文
```

**输入结构**：
```python
{
    "graph_context": "图谱检索结果",
    "vector_context": "向量检索结果",
    "mcp_context": "MCP 实时数据",
    "history_context": "历史对话",
    "synthesis_strategy": "merge | prioritize | summarize"
}
```

#### 3.2.4 质量评估技能 (QualityAssessmentSkill)

```python
class QualityAssessmentSkill(Skill):
    """质量评估技能"""

    name = "quality_assessment"
    description = "评估检索结果和回答质量"
    category = SkillCategory.VALIDATION

    async def execute(self, context: SkillContext) -> SkillResult:
        # 1. 结果相关性评估
        # 2. 事实一致性检查
        # 3. 完整性评估
        # 4. 生成质量报告
```

**输出结构**：
```python
{
    "overall_score": 0.85,          # 总体质量分数 0-1
    "relevance_score": 0.90,        # 相关性分数
    "accuracy_score": 0.80,         # 准确性分数
    "completeness_score": 0.85,      # 完整性分数
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}
```

---

## 四、技能工作流

### 4.1 技能组合

```python
class SkillWorkflow:
    """技能工作流"""

    name: str
    description: str
    skills: List[str]                # 技能列表
    edges: List[SkillEdge]           # 技能间的连接
    parallel_execution: bool        # 是否支持并行执行

    async def execute(self, initial_context: SkillContext) -> SkillResult:
        # 按拓扑序执行技能
        # 处理数据传递
        # 聚合结果
```

### 4.2 工作流示例：查询处理流水线

```
用户查询
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ QueryAnalysisSkill                                       │
│ - 分析查询意图                                            │
│ - 识别实体和关键词                                        │
│ - 判断所需能力                                            │
└─────────────────────────────────────────────────────────┘
    │
    ├─────────────────┬─────────────────┬─────────────────┐
    ▼                 ▼                 ▼                 ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│GraphRetrieval│ │VectorSearch│ │  MCP Search │ │HistoryLookup│
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
    │                 │                 │                 │
    └─────────────────┴─────────────────┴─────────────────┘
                            │
                            ▼
                ┌─────────────────────────────┐
                │   ContextSynthesisSkill     │
                │   - 整合多源检索结果          │
                │   - 去重和排序               │
                └─────────────────────────────┘
                            │
                            ▼
                ┌─────────────────────────────┐
                │  QualityAssessmentSkill     │
                │   - 评估结果质量             │
                │   - 生成质量报告             │
                └─────────────────────────────┘
```

---

## 五、技能注册表

### 5.1 SkillRegistry

```python
class SkillRegistry:
    """技能注册表"""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[SkillCategory, List[str]] = defaultdict(list)
        self._workflows: Dict[str, SkillWorkflow] = {}

    def register(self, skill: Skill) -> None:
        """注册技能"""

    def unregister(self, name: str) -> bool:
        """注销技能"""

    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""

    def list_by_category(self, category: SkillCategory) -> List[Skill]:
        """按分类列出技能"""

    def find_by_capability(self, capability: str) -> List[Skill]:
        """按能力查找技能"""

    def register_workflow(self, workflow: SkillWorkflow) -> None:
        """注册工作流"""
```

### 5.2 技能发现

```python
# 技能自动发现机制
class SkillDiscovery:
    """技能发现器"""

    async def discover_from_directory(self, path: str) -> List[Skill]:
        """从目录发现技能"""
        # 扫描指定目录
        # 动态导入技能类
        # 自动注册

    async def discover_from_mcp(self, server_name: str) -> List[Skill]:
        """从 MCP Server 发现技能"""
        # 获取 MCP 工具
        # 转换为技能
        # 注册到系统
```

---

## 六、技能执行

### 6.1 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 技能准备                                                │
│    - 验证输入参数                                            │
│    - 检查依赖技能                                            │
│    - 初始化执行上下文                                        │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 技能执行                                                │
│    - 调用技能的 execute 方法                                │
│    - 记录执行步骤                                            │
│    - 处理异常情况                                            │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 结果验证                                                │
│    - 验证输出 Schema                                        │
│    - 检查输出质量                                            │
│    - 记录执行指标                                            │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 结果返回                                                │
│    - 格式化输出                                              │
│    - 附加元数据                                              │
│    - 返回调用方                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 技能编排器

```python
class SkillOrchestrator:
    """技能编排器"""

    async def execute_skill(
        self,
        skill_name: str,
        context: SkillContext
    ) -> SkillResult:
        """执行单个技能"""

    async def execute_workflow(
        self,
        workflow_name: str,
        context: SkillContext
    ) -> SkillResult:
        """执行工作流"""

    async def execute_parallel(
        self,
        skill_names: List[str],
        context: SkillContext
    ) -> List[SkillResult]:
        """并行执行多个技能"""
```

---

## 七、可观测性

### 7.1 执行追踪

```python
class SkillExecutionTrace:
    """技能执行追踪"""

    skill_name: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str

    # 执行详情
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    error: Optional[str]

    # 性能指标
    duration: float
    memory_usage: float

    # 调用链
    parent_execution_id: Optional[str]
    child_execution_ids: List[str]
```

### 7.2 性能监控

```python
class SkillMetrics:
    """技能指标"""

    # 执行统计
    total_executions: int
    successful_executions: int
    failed_executions: int

    # 性能指标
    avg_duration: float
    p95_duration: float
    p99_duration: float

    # 质量指标
    avg_quality_score: float
    user_satisfaction: float
```

---

## 八、API 接口

### 8.1 管理 API

```python
# 列出所有技能
GET /api/v1/skills

# 获取技能详情
GET /api/v1/skills/{skill_name}

# 执行技能
POST /api/v1/skills/{skill_name}/execute

# 执行工作流
POST /api/v1/skills/workflows/{workflow_name}/execute

# 获取技能统计
GET /api/v1/skills/{skill_name}/metrics
```

### 8.2 请求/响应示例

**执行技能请求**：
```json
POST /api/v1/skills/query_analysis/execute
{
  "inputs": {
    "query": "BERT和GPT-4有什么共同点？"
  },
  "config": {
    "timeout": 10
  }
}
```

**技能执行响应**：
```json
{
  "success": true,
  "outputs": {
    "query_type": "reasoning_query",
    "entities": ["BERT", "GPT-4"],
    "requires_capabilities": ["graph_search", "multi_hop_reasoning"]
  },
  "duration": 0.523,
  "execution_id": "exec_12345"
}
```

---

## 九、最佳实践

### 9.1 技能设计原则

| 原则 | 说明 | 示例 |
|------|------|------|
| **单一职责** | 每个技能只做一件事 | 查询分析 ≠ 检索执行 |
| **幂等性** | 相同输入产生相同输出 | 检索类技能保持幂等 |
| **可测试** | 易于单元测试 | 明确的输入输出 |
| **可观测** | 记录执行过程 | 详细的日志和指标 |
| **容错性** | 优雅处理错误 | 返回部分结果而非崩溃 |

### 9.2 技能组合模式

```python
# 顺序组合
result1 = await execute("skill_a", context)
result2 = await execute("skill_b", context.with_inputs(result1.outputs))

# 并行组合
results = await execute_parallel(["skill_a", "skill_b"], context)

# 条件组合
if result1.outputs.get("need_more_info"):
    result2 = await execute("skill_c", context)

# 循环组合
while not context.get("satisfied"):
    result = await execute("refine", context)
```

---

## 十、扩展指南

### 10.1 添加新技能

```python
from src.skills import Skill, SkillCategory, SkillContext, SkillResult

class MyCustomSkill(Skill):
    """自定义技能"""

    name = "my_custom_skill"
    description = "我的自定义技能描述"
    category = SkillCategory.ANALYSIS
    version = "1.0.0"

    def get_input_schema(self):
        """返回输入 Schema"""
        return MyInputModel

    def get_output_schema(self):
        """返回输出 Schema"""
        return MyOutputModel

    async def execute(self, context: SkillContext) -> SkillResult:
        # 1. 获取输入
        input_data = context.get_input("param_name")

        # 2. 执行逻辑
        output_data = await self._do_something(input_data)

        # 3. 返回结果
        return SkillResult(
            success=True,
            outputs={"result": output_data},
            duration=0.1
        )

# 注册技能
from src.skills import get_skill_registry
registry = get_skill_registry()
registry.register(MyCustomSkill())
```

### 10.2 添加技能依赖

```python
class AdvancedSkill(Skill):
    """依赖其他技能的技能"""

    dependencies = ["query_analysis", "graph_retrieval"]

    async def execute(self, context: SkillContext):
        # 使用依赖技能
        analysis_result = await self.execute_dependency("query_analysis", context)
        graph_result = await self.execute_dependency("graph_retrieval", context)

        # 结合结果
        return self._combine_results(analysis_result, graph_result)
```

---

## 十一、与系统集成

### 11.1 与 Agent Orchestrator 集成

```python
class AgenticOrchestrator:
    """Agent 编排器"""

    def __init__(self):
        self.skill_registry = get_skill_registry()

    async def process_query(self, query: str):
        # 1. 使用查询分析技能
        analysis = await self.skill_registry.execute(
            "query_analysis",
            SkillContext(inputs={"query": query})
        )

        # 2. 根据分析结果选择技能
        required_skills = self._select_skills(analysis.outputs)

        # 3. 执行技能工作流
        result = await self.skill_registry.execute_workflow(
            "retrieval_and_synthesis",
            SkillContext(inputs=analysis.outputs)
        )

        return result
```

### 11.2 与 Function Calling 集成

```python
# 将 Skill 暴露为 Function Calling 工具
def skill_to_tool(skill: Skill) -> Tool:
    return Tool(
        name=f"skill.{skill.name}",
        description=skill.description,
        parameters=skill._get_tool_parameters(),
        function=lambda **kwargs: skill.execute(**kwargs)
    )
```

---

*文档版本：v1.0*
*创建日期：2026-03-11*
