# Agent Team 设计文档

## 1. 概述

### 1.1 背景

当前系统已有单个 ReAct Agent，但处理复杂任务时存在局限性：
- 单一 Agent 难以同时精通多个领域
- 复杂任务需要分工协作
- 缺少任务分解和并行执行能力

Agent Team 旨在通过多 Agent 协作解决这些问题。

### 1.2 设计目标

- **模块化**: 每种 Worker 专注特定领域
- **可扩展**: 易于添加新的 Worker 类型
- **可协作**: Workers 之间可共享上下文
- **可观测**: 完整的执行过程跟踪

### 1.3 架构选择

采用 **Orchestrator-Workers 模式**：

```
┌─────────────────────────────────────────────────────────────┐
│                      TeamOrchestrator                        │
│  - 意图分析与任务分解                                         │
│  - Worker 选择与任务分配                                      │
│  - 结果收集与整合                                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┬───────────────┐
        │                 │                 │               │
    ┌───▼────┐       ┌───▼────┐       ┌───▼────┐     ┌────▼─────┐
    │Research │       │ Coding │       │  RAG   │     │   Todo   │
    │ Worker  │       │ Worker │       │ Worker │     │  Worker  │
    └─────────┘       └─────────┘       └─────────┘     └──────────┘
```

**核心设计决策**：

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Worker 设计 | 独立 Agent（自有 LLM） | 更强的独立性和扩展性 |
| 通信方式 | 共享内存对象 | 简单直接，适合 Python |
| 依赖管理 | Orchestrator 手动编排 | 实现简单，可控性强 |
| 复杂任务 | 单次编排 | 后续可扩展多轮迭代 |

---

## 2. 核心组件设计

### 2.1 架构图

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   TeamOrchestrator                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │IntentAnalyzer│→│TaskDecomposer│→│WorkerRouter  │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
│                          │                               │
│                          ▼                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │              TeamContext                        │    │
│  │  - shared_data: Dict[str, Any]                 │    │
│  │  - conversation_history: List[Message]         │    │
│  │  - execution_plan: ExecutionPlan               │    │
│  │  - intermediate_results: Dict[str, Any]        │    │
│  └─────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
   ┌─────────┐        ┌─────────┐        ┌─────────┐
   │ Worker  │        │ Worker  │        │ Worker  │
   │ (async) │        │ (async) │        │ (async) │
   └────┬────┘        └────┬────┘        └────┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ ResultAggregator│
                  └─────────────────┘
                           │
                           ▼
                    Final Response
```

### 2.2 数据模型

#### AgentTask

传递给 Worker 的任务对象：

```python
@dataclass
class AgentTask:
    """Agent 任务"""
    task_id: str
    task_type: str  # 对应 Worker 类型
    input_data: Dict[str, Any]
    context: AgentContext  # 共享上下文
    dependencies: List[str]  # 依赖的其他 task_id
    timeout: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)
```

#### AgentContext

在 Orchestrator 和 Workers 之间共享：

```python
@dataclass
class AgentContext:
    """Agent 上下文"""
    context_id: str
    original_query: str
    shared_data: Dict[str, Any]  # Workers 共享数据
    conversation_history: List[Dict]  # 对话历史
    intermediate_results: Dict[str, Any]  # 中间结果
    execution_plan: Optional[ExecutionPlan] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_result(self, task_id: str) -> Optional[Any]:
        """获取指定任务的结果"""
        return self.intermediate_results.get(task_id)

    def set_result(self, task_id: str, result: Any) -> None:
        """设置任务结果"""
        self.intermediate_results[task_id] = result
```

#### WorkerResult

Worker 返回的结果：

```python
@dataclass
class WorkerResult:
    """Worker 执行结果"""
    task_id: str
    worker_type: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    next_actions: List[str] = field(default_factory=list)  # 建议的后续动作
```

#### TeamResult

Orchestrator 最终返回的结果：

```python
@dataclass
class TeamResult:
    """Team 执行结果"""
    original_query: str
    success: bool
    final_answer: str
    steps: List[Dict[str, Any]]  # 执行步骤
    worker_results: Dict[str, WorkerResult]
    context: AgentContext
    execution_time: float
    error: Optional[str] = None
```

---

## 3. Worker 接口设计

### 3.1 BaseWorker 抽象类

```python
class BaseWorker(ABC):
    """Worker 基类"""

    def __init__(self, name: str, llm_client=None):
        self.name = name
        self.llm_client = llm_client or get_glm_client()
        self.tools: List[Tool] = []

    @property
    @abstractmethod
    def worker_type(self) -> str:
        """Worker 类型标识"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Worker 描述（用于 Orchestrator 选择）"""
        pass

    @property
    def capabilities(self) -> List[str]:
        """Worker 能力列表"""
        return []

    @abstractmethod
    async def execute(self, task: AgentTask) -> WorkerResult:
        """执行任务"""
        pass

    async def pre_process(self, task: AgentTask) -> AgentTask:
        """任务前置处理（可选重写）"""
        return task

    async def post_process(self, result: WorkerResult) -> WorkerResult:
        """结果后处理（可选重写）"""
        return result

    def can_handle(self, task: AgentTask) -> float:
        """判断是否能处理该任务，返回置信度 0-1"""
        return 1.0 if task.task_type == self.worker_type else 0.0
```

### 3.2 具体 Worker 实现

#### ResearchWorker

研究型任务，如资料收集、信息整合：

```python
class ResearchWorker(BaseWorker):
    """研究 Worker - 处理信息收集和研究类任务"""

    @property
    def worker_type(self) -> str:
        return "research"

    @property
    def description(self) -> str:
        return "处理信息收集、资料研究、事实核查类任务"

    @property
    def capabilities(self) -> List[str]:
        return ["web_search", "knowledge_retrieval", "fact_checking"]

    async def execute(self, task: AgentTask) -> WorkerResult:
        """执行研究任务"""
        start = time.time()

        # 构建研究 Prompt
        research_query = task.input_data.get("query", "")

        # 使用 ReAct 方式进行研究
        # 调用 web_search, knowledge_search 等工具

        return WorkerResult(
            task_id=task.task_id,
            worker_type=self.worker_type,
            success=True,
            data={
                "findings": "研究发现...",
                "sources": ["source1", "source2"]
            },
            execution_time=time.time() - start
        )
```

#### CodingWorker

代码生成和修改任务：

```python
class CodingWorker(BaseWorker):
    """代码 Worker - 处理代码生成、修改、解释任务"""

    @property
    def worker_type(self) -> str:
        return "coding"

    @property
    def description(self) -> str:
        return "处理代码生成、代码修改、代码解释任务"

    @property
    def capabilities(self) -> List[str]:
        return ["code_generation", "code_review", "code_explanation"]

    async def execute(self, task: AgentTask) -> WorkerResult:
        """执行代码任务"""
        # 实现...
        pass
```

#### RAGWorker

知识库检索任务：

```python
class RAGWorker(BaseWorker):
    """RAG Worker - 处理知识库检索任务"""

    @property
    def worker_type(self) -> str:
        return "rag"

    @property
    def description(self) -> str:
        return "处理知识库检索、文档查询任务"

    @property
    def capabilities(self) -> List[str]:
        return ["vector_search", "graph_search", "hybrid_search"]

    async def execute(self, task: AgentTask) -> WorkerResult:
        """执行 RAG 任务"""
        # 实现...
        pass
```

#### TodoWorker

待办事项管理：

```python
class TodoWorker(BaseWorker):
    """Todo Worker - 处理待办事项管理任务"""

    @property
    def worker_type(self) -> str:
        return "todo"

    @property
    def description(self) -> str:
        return "处理待办事项的增删改查任务"

    @property
    def capabilities(self) -> List[str]:
        return ["todo_add", "todo_list", "todo_complete", "todo_delete"]

    async def execute(self, task: AgentTask) -> WorkerResult:
        """执行 Todo 任务"""
        # 直接调用 todo 工具
        pass
```

---

## 4. TeamOrchestrator 设计

### 4.1 核心类

```python
class TeamOrchestrator:
    """Team Orchestrator - 协调多个 Workers"""

    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.workers: Dict[str, BaseWorker] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._register_default_workers()

    def _register_default_workers(self):
        """注册默认 Workers"""
        self.register_worker(ResearchWorker())
        self.register_worker(CodingWorker())
        self.register_worker(RAGWorker())
        self.register_worker(TodoWorker())

    def register_worker(self, worker: BaseWorker) -> None:
        """注册 Worker"""
        self.workers[worker.worker_type] = worker

    def get_worker(self, worker_type: str) -> Optional[BaseWorker]:
        """获取 Worker"""
        return self.workers.get(worker_type)

    async def run(self, query: str, history: List[Dict] = None) -> TeamResult:
        """
        运行 Team

        Args:
            query: 用户查询
            history: 对话历史

        Returns:
            TeamResult: 执行结果
        """
        start_time = time.time()

        # 1. 创建上下文
        context = AgentContext(
            context_id=str(uuid4()),
            original_query=query,
            conversation_history=history or [],
            shared_data={},
            intermediate_results={}
        )

        steps = []

        try:
            # 2. 分析意图
            intent = await self._analyze_intent(query, context)
            steps.append({
                "step": "intent_analysis",
                "intent": intent.dict()
            })

            # 3. 分解任务
            tasks = await self._decompose_tasks(intent, context)
            steps.append({
                "step": "task_decomposition",
                "tasks": [t.task_id for t in tasks]
            })

            # 4. 按依赖顺序执行任务
            worker_results = await self._execute_tasks(tasks, context)
            steps.append({
                "step": "task_execution",
                "results": {k: v.success for k, v in worker_results.items()}
            })

            # 5. 聚合结果
            final_answer = await self._aggregate_results(
                query, worker_results, context
            )

            return TeamResult(
                original_query=query,
                success=True,
                final_answer=final_answer,
                steps=steps,
                worker_results=worker_results,
                context=context,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return TeamResult(
                original_query=query,
                success=False,
                final_answer=f"执行出错: {str(e)}",
                steps=steps,
                worker_results={},
                context=context,
                execution_time=time.time() - start_time,
                error=str(e)
            )

    async def _analyze_intent(self, query: str, context: AgentContext) -> QueryIntent:
        """分析意图"""
        return await self.intent_analyzer.analyze(query)

    async def _decompose_tasks(
        self,
        intent: QueryIntent,
        context: AgentContext
    ) -> List[AgentTask]:
        """
        分解任务

        根据意图分析结果，决定需要创建哪些任务
        """
        tasks = []

        # 多意图：每个子意图创建一个任务
        if intent.has_multiple_intents and intent.sub_intents:
            for i, sub_intent in enumerate(intent.sub_intents):
                task = AgentTask(
                    task_id=f"task_{i}_{uuid4().hex[:8]}",
                    task_type=self._map_intent_to_worker(sub_intent.query_type),
                    input_data={
                        "query": sub_intent.sub_query,
                        "entities": sub_intent.entities,
                        "keywords": sub_intent.keywords
                    },
                    context=context,
                    dependencies=[]
                )
                tasks.append(task)
        else:
            # 单意图：创建一个任务
            task = AgentTask(
                task_id=f"task_0_{uuid4().hex[:8]}",
                task_type=self._map_intent_to_worker(intent.query_type),
                input_data={
                    "query": intent.query,
                    "entities": intent.entities,
                    "keywords": intent.keywords
                },
                context=context,
                dependencies=[]
            )
            tasks.append(task)

        return tasks

    def _map_intent_to_worker(self, query_type: QueryType) -> str:
        """将查询类型映射到 Worker"""
        mapping = {
            QueryType.FACT: "rag",
            QueryType.RELATION: "rag",
            QueryType.REASONING: "research",
            QueryType.AGGREGATION: "rag",
            QueryType.OPEN_ENDED: "research",
            QueryType.GENERATION: "coding",
            QueryType.REALTIME: "research",
            QueryType.SYSTEM: "research",  # 系统问题由 research worker 处理
        }
        return mapping.get(query_type, "research")

    async def _execute_tasks(
        self,
        tasks: List[AgentTask],
        context: AgentContext
    ) -> Dict[str, WorkerResult]:
        """
        执行任务

        按依赖关系执行任务，支持并行执行无依赖的任务
        """
        results = {}

        # 简单实现：按顺序执行（后续可优化为并行执行无依赖任务）
        for task in tasks:
            # 检查依赖是否满足
            dependencies_met = all(
                dep_id in results and results[dep_id].success
                for dep_id in task.dependencies
            )

            if not dependencies_met:
                results[task.task_id] = WorkerResult(
                    task_id=task.task_id,
                    worker_type=task.task_type,
                    success=False,
                    error="依赖任务未完成"
                )
                continue

            # 获取对应的 Worker
            worker = self.get_worker(task.task_type)
            if not worker:
                results[task.task_id] = WorkerResult(
                    task_id=task.task_id,
                    worker_type=task.task_type,
                    success=False,
                    error=f"未找到 {task.task_type} 类型的 Worker"
                )
                continue

            # 执行任务
            try:
                result = await asyncio.wait_for(
                    worker.execute(task),
                    timeout=task.timeout
                )
                results[task.task_id] = result

                # 更新上下文
                context.set_result(task.task_id, result.data)

            except asyncio.TimeoutError:
                results[task.task_id] = WorkerResult(
                    task_id=task.task_id,
                    worker_type=task.task_type,
                    success=False,
                    error=f"任务超时 ({task.timeout}s)"
                )
            except Exception as e:
                results[task.task_id] = WorkerResult(
                    task_id=task.task_id,
                    worker_type=task.task_type,
                    success=False,
                    error=str(e)
                )

        return results

    async def _aggregate_results(
        self,
        query: str,
        worker_results: Dict[str, WorkerResult],
        context: AgentContext
    ) -> str:
        """
        聚合 Worker 结果生成最终答案
        """
        # 收集所有成功的结果
        successful_results = {
            k: v for k, v in worker_results.items() if v.success
        }

        if not successful_results:
            return "抱歉，所有任务都失败了。"

        # 如果只有一个结果，直接返回
        if len(successful_results) == 1:
            result = list(successful_results.values())[0]
            if isinstance(result.data, dict) and "answer" in result.data:
                return result.data["answer"]
            return str(result.data)

        # 多个结果：使用 LLM 聚合
        llm_client = get_glm_client()

        prompt = f"""请根据以下 Worker 的执行结果，为用户生成一个完整、连贯的答案。

用户问题：{query}

Worker 执行结果：
{self._format_worker_results(successful_results)}

请生成最终答案，要求：
1. 完整回答用户的问题
2. 将多个 Worker 的结果有机整合
3. 语言简洁清晰
"""

        response = await llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        return response.content

    def _format_worker_results(self, results: Dict[str, WorkerResult]) -> str:
        """格式化 Worker 结果用于 LLM 聚合"""
        formatted = []
        for task_id, result in results.items():
            formatted.append(f"- {result.worker_type} ({task_id}): {result.data}")
        return "\n".join(formatted)
```

---

## 5. 使用示例

### 5.1 基本使用

```python
from src.agent.team.orchestrator import TeamOrchestrator, get_team_orchestrator

# 获取 Orchestrator
orchestrator = get_team_orchestrator()

# 执行查询
result = await orchestrator.run("帮我研究一下视频隐写技术")

print(result.final_answer)
print(f"执行耗时: {result.execution_time:.2f}s")
```

### 5.2 带对话历史

```python
history = [
    {"role": "user", "content": "什么是 GraphRAG？"},
    {"role": "assistant", "content": "GraphRAG 是..."}
]

result = await orchestrator.run("它有什么优点？", history=history)
```

### 5.3 注册自定义 Worker

```python
class MyCustomWorker(BaseWorker):
    @property
    def worker_type(self) -> str:
        return "custom"

    @property
    def description(self) -> str:
        return "处理自定义任务"

    async def execute(self, task: AgentTask) -> WorkerResult:
        # 自定义逻辑
        return WorkerResult(
            task_id=task.task_id,
            worker_type="custom",
            success=True,
            data={"result": "自定义结果"}
        )

orchestrator.register_worker(MyCustomWorker())
```

---

## 6. 目录结构

```
src/agent/team/
├── __init__.py              # 导出接口
├── orchestrator.py           # TeamOrchestrator 实现
├── workers.py                # Workers 基类和具体实现
├── models.py                 # Team 相关数据模型
└── router.py                 # Worker 路由逻辑（可选）

src/agent/
├── __init__.py              # 更新导出
├── team.py                  # 保留旧的 AgentTeam（向后兼容）
├── react_agent.py           # 现有 ReAct Agent
├── intent.py                # 现有意图分析
└── models.py                # 现有模型定义
```

---

## 7. 实现计划

### 阶段 1：核心框架（优先级：高）

1. **数据模型** (`models.py`)
   - AgentTask
   - AgentContext
   - WorkerResult
   - TeamResult

2. **BaseWorker** (`workers.py`)
   - 抽象基类
   - 基本方法

3. **TeamOrchestrator** (`orchestrator.py`)
   - 基本框架
   - 意图分析集成
   - 任务执行和结果聚合

### 阶段 2：默认 Workers（优先级：高）

1. **ResearchWorker** - 研究任务
2. **RAGWorker** - 知识库检索
3. **CodingWorker** - 代码相关
4. **TodoWorker** - 待办管理

### 阶段 3：增强功能（优先级：中）

1. **并行执行** - 无依赖任务并行
2. **重试机制** - 失败任务重试
3. **执行追踪** - 详细日志和可观测性

### 阶段 4：高级特性（优先级：低）

1. **动态 Worker 加载**
2. **Worker 性能指标**
3. **执行缓存**
4. **多轮对话支持**

---

## 8. 与现有系统集成

### 8.1 API 集成

```python
# src/api/routes/chat.py

@router.post("/chat")
async def chat(request: ChatRequest):
    # 检测是否需要使用 Team
    if is_complex_query(request.message):
        orchestrator = get_team_orchestrator()
        result = await orchestrator.run(
            request.message,
            request.history
        )
        return {"answer": result.final_answer}
    else:
        # 使用原有的 ReAct Agent
        agent = get_react_agent()
        result = await agent.run(request.message, request.history)
        return {"answer": result.answer}
```

### 8.2 前端显示

前端可以展示 Team 执行过程：

```json
{
  "answer": "最终答案",
  "execution_info": {
    "mode": "team",
    "workers_used": ["research", "coding"],
    "steps": [
      {"step": "intent_analysis", "result": {...}},
      {"step": "task_decomposition", "tasks": ["task_1", "task_2"]},
      {"step": "task_execution", "results": {...}},
      {"step": "result_aggregation", "result": "最终答案"}
    ],
    "execution_time": 15.3
  }
}
```

---

## 9. 配置

```python
# src/config/team_config.py

class TeamConfig(BaseSettings):
    """Team 配置"""

    # Orchestrator 配置
    enable_parallel_execution: bool = True
    max_parallel_tasks: int = 5
    default_task_timeout: int = 300

    # Worker 配置
    default_workers: List[str] = [
        "research", "rag", "coding", "todo"
    ]

    # LLM 配置
    aggregation_temperature: float = 0.3
    intent_analysis_temperature: float = 0.1
```

---

## 10. 注意事项

### 10.1 向后兼容

- 保留原有的 `AgentTeam` 和 `ReActAgent`
- 新的 `TeamOrchestrator` 作为可选功能
- API 层可以根据请求类型选择使用

### 10.2 性能考虑

- Worker 的 LLM 调用会增加成本
- 考虑添加缓存机制
- 复杂查询才使用 Team，简单查询用 ReAct Agent

### 10.3 扩展性

- Worker 接口设计支持第三方扩展
- 可通过配置文件动态加载 Workers

---

## 11. 参考资料

- LangGraph: https://github.com/langchain-ai/langgraph
- AutoGen: https://github.com/microsoft/autogen
- CrewAI: https://github.com/joaomdmoura/crewAI
