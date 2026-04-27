# Agentic Framework 需求文档

## 项目定位

**通用 Agent 框架**：基于 ReAct 范式的多轮推理智能体系统，通过工具系统、技能系统和上下文工程实现复杂任务的自动化处理。

**核心架构**：Vue 前端 + FastAPI 后端 + LLM 推理引擎

---

## 一、核心功能

### 1.1 ReAct Agent 引擎

**范式**：ReAct (Reasoning + Acting) 循环

**流程**：
```
用户查询 → Thought（思考） → Action（行动） → Observation（观察）
                ↑                                      ↓
                └─────────────── 循环直到 Answer ──────┘
```

**要求**：
- 支持多轮迭代，直到 LLM 输出 `Answer:` 为止
- 每轮解析 LLM 输出，提取 Thought/Action/Action Input/Answer
- Action 触发工具调用，Observation 作为下一轮输入
- 最大迭代次数可配置（默认 10 次）

**输出结构**：
```python
@dataclass
class ReActStep:
    step_type: str  # "thought" | "action" | "observation" | "answer" | "error"
    content: str
    data: Optional[Dict] = None  # 工具调用参数/结果

@dataclass
class ReActResult:
    answer: str
    steps: List[ReActStep]
    success: bool
    metadata: Dict  # 性能指标
```

### 1.2 Function Calling 工具系统

**能力要求**：
- 基于 LLM Function Calling 的工具调用
- 工具动态注册/注销
- 工具参数自动验证（Pydantic）
- 支持同步/异步工具
- 支持超时控制

**工具定义**：
```python
class Tool(BaseModel):
    name: str                           # 工具唯一标识
    description: str                    # 工具描述（给 LLM 看的）
    category: str                       # 分类：builtin/mcp/custom
    parameters: Dict                    # JSON Schema 参数定义
    function: Callable                  # 实际执行函数
    async_mode: bool = False            # 是否异步
    timeout: int = 30                   # 超时时间（秒）
```

**MCP 扩展**：
- MCP 服务器工具自动发现和注册
- MCP 工具与本地工具统一接口
- 支持 filesystem、github、database、web-search 等常见 MCP 服务器

**内置工具**：
| 工具名 | 功能 | 类别 |
|--------|------|------|
| `web_search` | 互联网搜索 | builtin |
| `code_execute` | 代码执行 | builtin |
| `query_knowledge_graph` | 知识图谱查询 | builtin |
| `vector_search` | 向量检索 | builtin |

### 1.3 Skills 系统

**定位**：Skills 是 Agent 能力的模块化封装，比 Tool 更高层级。

**与 Tool 的区别**：

| 维度 | Tool | Skill |
|------|------|-------|
| 粒度 | 单个函数调用 | 完整能力（可能包含多个 Tool） |
| 输入输出 | 固定参数 | 结构化 Schema |
| 执行追踪 | 简单 | 完整的步骤记录 |
| 适用场景 | 外部操作 | Agent 内部能力 |

**预置 Skills**：
- `query_analysis`: 查询意图分析
- `multi_hop_reasoning`: 多跳推理
- `context_synthesis`: 上下文整合
- `quality_assessment`: 质量评估

### 1.4 上下文工程

**上下文压缩策略**（按优先级）：

1. **工具输出截断**
   - 每个工具输出最大长度限制（如 5000 字符）
   - 超出部分智能截断（保留首尾，中间省略）

2. **历史消息摘要**
   - 当总 token 数超限时触发
   - **必须保留最近 10 条消息不压缩**
   - 更早的消息合并为摘要

3. **Observation 压缩**
   - 多个 Observation 合并展示
   - 去除冗余信息

**上下文窗口管理**：
```python
class ContextWindow:
    max_tokens: int = 16000        # 最大 token 数
    preserve_recent: int = 10      # 保留最近消息数
    tool_output_limit: int = 5000  # 工具输出字符限制
```

### 1.5 可观测性（Trace）

**全链路追踪**：记录每次 Agent 执行的完整过程

**追踪内容**：
- 意图分析结果
- 每轮 Thought/Action/Observation
- 工具调用详情（参数、结果、耗时）
- 最终 Answer

**性能指标**（前端展示）：
```
┌─ 执行摘要 ─────────────────────────────┐
│ 总耗时: 3.2s                           │
│ LLM 调用: 4 次                         │
│ 工具调用: 2 次                         │
│ Token 消耗: 2847                      │
│ 迭代轮数: 3                            │
└────────────────────────────────────────┘
```

**Trace 数据结构**：
```python
class ExecutionTrace:
    execution_id: str
    query: str
    start_time: datetime
    end_time: datetime
    duration: float
    steps: List[ReActStep]
    llm_calls: int
    tool_calls: int
    tokens_used: int
```

### 1.6 Agent Team

**定义**：多个独立 Agent 从共享任务队列中取任务协作完成复杂任务。

**与 SubAgent 的区别**：

| 特征 | SubAgent | Agent Team |
|------|----------|------------|
| 关系 | 父子关系（主 Agent 调用子 Agent） | 平级关系（从队列取任务） |
| 生命周期 | 临时创建，用完销毁 | 常驻运行 |
| 通信方式 | 直接调用 | 消息队列 |
| 适用场景 | 任务分解 | 并行处理 |

**实现要求**：
- 支持任务队列（内存或 Redis）
- Agent 从队列领取任务
- 支持任务优先级
- 支持任务超时和重试

### 1.7 知识图谱 RAG

**定位**：作为数据源/工具集成到工具系统中，不是独立模块。

**实现方式**：
```python
# 注册为工具
query_kg_tool = Tool(
    name="query_knowledge_graph",
    description="查询知识图谱获取实体关系",
    function=query_graph_func,
    ...
)
```

**数据源接入**：
- Neo4j 图数据库
- 实体检索、关系遍历、多跳推理
- 与向量检索混合使用

### 1.8 多意图理解

**定义**：识别用户查询中的多个问题，逐一处理。

**处理流程**：
1. 检测多意图关键词（以及、还有、另外、同时等）
2. LLM 分解子意图
3. 依次处理每个子意图
4. 合并最终答案

**关键要求**：
- 避免 LLM 提前终止（回答第一个问题就 Answer）
- 部分答案时提示继续处理
- 最大迭代次数支持多意图场景（如 15 次）

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Vue 前端                              │
│  - 聊天界面  -  Trace 可视化  -  工具管理  -  Agent 配置     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                      FastAPI 后端                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              ReAct Agent Engine                         │ │
│  │   - 多轮推理循环  -  工具调用  -  答案生成               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│  ┌──────────┬────────────┼────────────┬──────────────────┐   │
│  ▼          ▼            ▼            ▼                  ▼   │
│ ┌────────┐┌────────┐ ┌────────┐ ┌─────────┐ ┌────────────┐  │
│ │工具系统││Skills │ │上下文  │ │可观测性 │ │Agent Team  │  │
│ │        ││系统   │ │工程    │ │         │ │            │  │
│ │- FC   │ │- 查询  │ │- 压缩  │ │- Trace  │ │- 任务队列  │  │
│ │- MCP  │ │- 推理  │ │- 窗口  │ │- 日志   │ │- 协作      │  │
│ │- 注册 │ │- 整合  │ │- 格式  │ │- 指标   │ │            │  │
│ └────┬───┘└────────┘ └────────┘ └─────────┘ └────────────┘  │
│      │                                                        │
│      └───────────────────┬───────────────────────────────┘    │
│                          │                                    │
│  ┌───────────────────────▼───────────────────────────────┐   │
│  │                    数据层                               │   │
│  │  向量库  │  知识图谱  │  文档存储  │  缓存  │  历史记录  │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、技术栈

| 层级 | 技术选型 |
|------|----------|
| **LLM** | 智谱 GLM-4.7 |
| **后端框架** | FastAPI |
| **前端框架** | Vue 3 |
| **图数据库** | Neo4j |
| **向量数据库** | Qdrant |
| **MCP 协议** | MCP Python SDK |
| **任务队列** | 内存队列（asyncio.Queue） |

---

## 四、API 接口

### 4.1 核心接口

```
POST /api/v1/chat
- 发送消息，获取回复和 trace

GET /api/v1/trace/{execution_id}
- 获取完整的执行 trace

GET /api/v1/tools/list
- 列出所有可用工具

POST /api/v1/tools/register
- 注册自定义工具

GET /api/v1/agent/team/status
- Agent Team 状态查询
```

### 4.2 请求/响应示例

**聊天请求**：
```json
POST /api/v1/chat
{
  "message": "BERT和GPT-4有什么共同点？",
  "stream": false
}
```

**聊天响应**：
```json
{
  "answer": "BERT和GPT-4都基于Transformer架构...",
  "execution_id": "exec_12345",
  "success": true
}
```

**Trace 响应**：
```json
{
  "execution_id": "exec_12345",
  "query": "BERT和GPT-4有什么共同点？",
  "duration": 3.2,
  "llm_calls": 4,
  "tool_calls": 2,
  "tokens_used": 2847,
  "steps": [
    {"step_type": "thought", "content": "..."},
    {"step_type": "action", "content": "query_knowledge_graph", "data": {...}},
    {"step_type": "observation", "content": "..."},
    {"step_type": "answer", "content": "..."}
  ]
}
```

---

## 五、数据模型

### 5.1 ReAct 执行

```python
@dataclass
class ReActStep:
    step_type: str  # thought/action/observation/answer/error
    content: str
    data: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ReActResult:
    execution_id: str
    answer: str
    steps: List[ReActStep]
    success: bool
    duration: float
    metadata: Dict
```

### 5.2 工具定义

```python
class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None

class Tool(BaseModel):
    name: str
    description: str
    category: str
    parameters: List[ToolParameter]
    function: Callable
    async_mode: bool = False
    timeout: int = 30
```

### 5.3 Trace

```python
class ExecutionTrace(BaseModel):
    execution_id: str
    query: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]
    steps: List[ReActStep]
    llm_calls: int = 0
    tool_calls: int = 0
    tokens_used: int = 0
```

---

*文档版本：v4.0*
*创建日期：2026-03-12*
*核心定位：通用 Agent 框架（基于 ReAct 范式）*
