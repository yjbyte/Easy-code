# Function Calling 设计文档

## 文档概述

**版本**: v1.0
**创建日期**: 2026-03-11
**最后更新**: 2026-03-11

---

## 一、概述

### 1.1 什么是 Function Calling

Function Calling 是 LLM 与外部系统交互的核心机制，允许模型在生成文本时调用预定义的函数（工具），获取实时数据或执行操作，然后将结果整合到回复中。

### 1.2 在 Agentic GraphRAG 中的定位

```
┌─────────────────────────────────────────────────────────────┐
│                     用户查询                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Agent 智能体                                │
│  - 意图理解  -  任务规划  -  工具选择                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│            Function Calling 引擎 ◄────── 本文档重点           │
│  - 函数注册  -  参数解析  -  执行编排  -  结果整合           │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────────┐ ┌────▼────────┐ ┌───▼──────────┐
│  GraphRAG       │ │  MCP 数据源  │ │  外部工具     │
│  引擎函数        │ │             │ │              │
└─────────────────┘ └─────────────┘ └──────────────┘
```

### 1.3 设计目标

| 目标 | 说明 |
|------|------|
| **标准化** | 符合 OpenAI/Anthropic Function Calling 规范 |
| **可扩展** | 新增工具无需修改核心代码 |
| **类型安全** | 使用 Pydantic 进行参数验证 |
| **可观测** | 完整的执行追踪和日志 |
| **容错性** | 优雅处理调用失败 |

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Function Calling 引擎                     │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Function Registry                     │   │
│  │  - 工具注册  -  元数据管理  -  依赖解析                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Calling Planner                         │   │
│  │  - 调用规划  -  并行分析  -  依赖排序                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Execution Engine                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │   │
│  │  │ 并行执行器   │  │ 串行执行器   │  │  条件执行器      │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Result Processor                        │   │
│  │  - 结果验证  -  错误处理  -  格式化输出                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### 2.2.1 Function Registry（函数注册表）

```python
class FunctionRegistry:
    """函数注册表 - 管理所有可调用工具"""

    def register(self, tool: Tool) -> None
    def unregister(self, name: str) -> None
    def get(self, name: str) -> Optional[Tool]
    def list(self) -> List[Tool]
    def find_by_capability(self, capability: str) -> List[Tool]
```

#### 2.2.2 Calling Planner（调用规划器）

```python
class CallingPlanner:
    """调用规划器 - 分析和规划函数调用"""

    def plan_calls(
        self,
        intent: str,
        available_tools: List[Tool]
    ) -> ExecutionPlan
```

#### 2.2.3 Execution Engine（执行引擎）

```python
class ExecutionEngine:
    """执行引擎 - 执行函数调用"""

    async def execute(
        self,
        plan: ExecutionPlan
    ) -> ExecutionResult

    async def execute_parallel(
        self,
        calls: List[FunctionCall]
    ) -> List[FunctionResult]

    async def execute_sequential(
        self,
        calls: List[FunctionCall]
    ) -> List[FunctionResult]
```

---

## 三、工具定义规范

### 3.1 工具数据结构

```python
from pydantic import BaseModel, Field
from typing import Any, Callable, Dict, Optional
from enum import Enum

class ToolCategory(str, Enum):
    """工具分类"""
    GRAPH_RAG = "graph_rag"       # GraphRAG 引擎
    MCP = "mcp"                   # MCP 协议
    BUILTIN = "builtin"           # 内置工具
    CUSTOM = "custom"             # 自定义工具

class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[list] = None

class Tool(BaseModel):
    """工具定义"""
    name: str = Field(..., description="工具名称，唯一标识")
    description: str = Field(..., description="工具功能描述")
    category: ToolCategory = Field(default=ToolCategory.BUILTIN)
    parameters: List[ToolParameter] = Field(default_factory=list)
    function: Callable = Field(..., description="实际执行函数")
    async_mode: bool = Field(default=False, description="是否异步执行")
    timeout: int = Field(default=30, description="超时时间（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    class Config:
        arbitrary_types_allowed = True
```

### 3.2 工具定义示例

```python
# 示例1: 知识图谱查询
query_knowledge_graph = Tool(
    name="query_knowledge_graph",
    description="查询知识图谱，获取实体和关系信息",
    category=ToolCategory.GRAPH_RAG,
    parameters=[
        ToolParameter(
            name="entity",
            type="string",
            description="查询的实体名称",
            required=True
        ),
        ToolParameter(
            name="relation",
            type="string",
            description="关系类型（可选）",
            required=False
        ),
        ToolParameter(
            name="max_depth",
            type="integer",
            description="最大遍历深度",
            required=False,
            default=2
        )
    ],
    function=_query_graph_impl,
    async_mode=True
)

# 示例2: Web 搜索
web_search = Tool(
    name="web_search",
    description="在互联网上搜索实时信息",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="搜索关键词",
            required=True
        ),
        ToolParameter(
            name="num_results",
            type="integer",
            description="返回结果数量",
            required=False,
            default=5
        )
    ],
    function=_web_search_impl,
    async_mode=True
)
```

---

## 四、执行流程

### 4.1 完整调用流程

```
用户查询
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 1. LLM 意图分析                                          │
│    - 解析用户需要调用哪些工具                            │
│    - 生成函数调用参数                                    │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 2. 函数注册表查找                                        │
│    - 验证工具存在性                                      │
│    - 检查参数完整性                                      │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 3. 调用规划                                              │
│    - 分析调用依赖关系                                    │
│    - 确定执行顺序（并行/串行）                           │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 4. 参数验证                                              │
│    - Pydantic Schema 验证                                │
│    - 类型检查和转换                                      │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 5. 执行引擎                                              │
│    ├─ 并行执行：无依赖的调用同时执行                     │
│    ├─ 串行执行：有依赖的调用按序执行                     │
│    └─ 错误处理：失败重试/降级处理                        │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 6. 结果处理                                              │
│    - 结果格式化                                          │
│    - 错误信息封装                                        │
│    - 返回 LLM 生成回复                                    │
└─────────────────────────────────────────────────────────┘
```

### 4.2 执行策略

#### 并行执行

```python
# 当多个调用无依赖关系时，并行执行
async def execute_parallel(calls: List[FunctionCall]):
    tasks = [execute_single(call) for call in calls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

#### 串行执行

```python
# 当调用有依赖关系时，串行执行
async def execute_sequential(calls: List[FunctionCall]):
    results = []
    for call in calls:
        result = await execute_single(call)
        results.append(result)
        # 后续调用可能依赖前面结果
        if result.error:
            break
    return results
```

#### 混合执行

```python
# 分析依赖关系，自动选择执行策略
async def execute_smart(plan: ExecutionPlan):
    # 识别可并行组
    parallel_groups = identify_parallel_groups(plan.calls)

    results = []
    for group in parallel_groups:
        if len(group) > 1:
            group_results = await execute_parallel(group)
        else:
            group_results = await execute_sequential(group)
        results.extend(group_results)

    return results
```

---

## 五、LLM 集成

### 5.1 Tools 定义转换

将工具定义转换为 LLM 可识别的格式：

```python
def tool_to_openai_format(tool: Tool) -> dict:
    """转换为 OpenAI Function Calling 格式"""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description,
                        **({"enum": param.enum} if param.enum else {})
                    }
                    for param in tool.parameters
                },
                "required": [
                    param.name for param in tool.parameters if param.required
                ]
            }
        }
    }
```

### 5.2 GLM-4 Function Calling

```python
from zhipuai import ZhipuAI

client = ZhipuAI(api_key="...")

response = client.chat.completions.create(
    model="glm-4-plus",
    messages=[
        {"role": "user", "content": "搜索最新的AI新闻"}
    ],
    tools=[tool_to_openai_format(tool) for tool in available_tools]
)

# 处理工具调用
if response.choices[0].message.tool_calls:
    for tool_call in response.choices[0].message.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        result = await execute_function(function_name, arguments)
```

---

## 六、工具扩展

### 6.1 内置工具

| 工具名 | 功能 | 类别 |
|--------|------|------|
| `query_knowledge_graph` | 查询知识图谱 | GRAPH_RAG |
| `vector_search` | 向量相似度搜索 | GRAPH_RAG |
| `multi_hop_reasoning` | 多跳推理 | GRAPH_RAG |
| `mcp_query` | MCP 数据源查询 | MCP |
| `web_search` | Web 搜索 | BUILTIN |
| `code_execute` | 代码执行 | BUILTIN |
| `data_analyze` | 数据分析 | BUILTIN |

### 6.2 自定义工具

```python
# 定义自定义工具
from src.tools import Tool, ToolCategory, ToolParameter

async def my_custom_function(param1: str, param2: int) -> dict:
    """自定义工具实现"""
    # 实现你的逻辑
    return {"result": "success"}

# 注册工具
my_tool = Tool(
    name="my_custom_tool",
    description="我的自定义工具",
    category=ToolCategory.CUSTOM,
    parameters=[
        ToolParameter(
            name="param1",
            type="string",
            description="参数1",
            required=True
        ),
        ToolParameter(
            name="param2",
            type="integer",
            description="参数2",
            required=False,
            default=10
        )
    ],
    function=my_custom_function,
    async_mode=True
)

# 注册到系统
from src.tools import get_function_registry
registry = get_function_registry()
registry.register(my_tool)
```

### 6.3 MCP 工具自动注册

```python
class MCPToolLoader:
    """MCP 工具加载器 - 自动将 MCP 服务器暴露的工具注册"""

    async def load_from_server(self, server_name: str) -> List[Tool]:
        """从 MCP 服务器加载工具定义"""
        mcp_client = get_mcp_client(server_name)
        tools_definition = await mcp_client.list_tools()

        tools = []
        for tool_def in tools_definition:
            tool = self._create_mcp_tool(server_name, tool_def)
            tools.append(tool)

        return tools

    def _create_mcp_tool(self, server_name: str, tool_def: dict) -> Tool:
        """创建 MCP 工具包装器"""
        async def mcp_wrapper(**kwargs):
            client = get_mcp_client(server_name)
            return await client.call_tool(tool_def["name"], kwargs)

        return Tool(
            name=f"{server_name}.{tool_def['name']}",
            description=tool_def["description"],
            category=ToolCategory.MCP,
            parameters=self._parse_parameters(tool_def["inputSchema"]),
            function=mcp_wrapper,
            async_mode=True,
            metadata={"server": server_name, "original_name": tool_def["name"]}
        )
```

---

## 七、错误处理

### 7.1 错误类型

```python
class FunctionCallError(Exception):
    """Function Calling 基础错误"""
    pass

class ToolNotFoundError(FunctionCallError):
    """工具不存在"""
    pass

class ParameterValidationError(FunctionCallError):
    """参数验证失败"""
    pass

class ExecutionTimeoutError(FunctionCallError):
    """执行超时"""
    pass

class ExecutionFailedError(FunctionCallError):
    """执行失败"""
    pass
```

### 7.2 错误处理策略

```python
class ErrorHandler:
    """错误处理器"""

    async def handle(
        self,
        error: Exception,
        context: ExecutionContext
    ) -> ErrorResult:
        """处理错误"""

        # 1. 记录日志
        logger.error(f"Function call error: {error}", extra=context.dict())

        # 2. 判断错误类型
        if isinstance(error, ToolNotFoundError):
            return ErrorResult(
                error_type="TOOL_NOT_FOUND",
                message=f"工具 {context.tool_name} 不存在",
                retry=False
            )

        elif isinstance(error, ParameterValidationError):
            return ErrorResult(
                error_type="INVALID_PARAMETERS",
                message=f"参数验证失败: {error}",
                retry=False,
                corrected_parameters=self._suggest_correction(error)
            )

        elif isinstance(error, ExecutionTimeoutError):
            return ErrorResult(
                error_type="TIMEOUT",
                message=f"工具执行超时 ({context.timeout}s)",
                retry=True
            )

        elif isinstance(error, ExecutionFailedError):
            return ErrorResult(
                error_type="EXECUTION_FAILED",
                message=f"工具执行失败: {error}",
                retry=True
            )

        # 默认处理
        return ErrorResult(
            error_type="UNKNOWN",
            message=str(error),
            retry=False
        )
```

---

## 八、可观测性

### 8.1 执行追踪

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class FunctionCallTrace:
    """函数调用追踪记录"""
    call_id: str
    tool_name: str
    parameters: dict
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "pending"  # pending, success, error
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: dict = None

class Tracer:
    """调用追踪器"""

    def start_call(self, tool_name: str, parameters: dict) -> str:
        """开始追踪"""
        call_id = generate_uuid()
        trace = FunctionCallTrace(
            call_id=call_id,
            tool_name=tool_name,
            parameters=parameters,
            start_time=datetime.now()
        )
        self._traces[call_id] = trace
        return call_id

    def finish_call(
        self,
        call_id: str,
        status: str,
        result: Any = None,
        error: str = None
    ):
        """结束追踪"""
        trace = self._traces.get(call_id)
        if trace:
            trace.end_time = datetime.now()
            trace.status = status
            trace.result = result
            trace.error = error

    def get_traces(self, filter: dict = None) -> List[FunctionCallTrace]:
        """获取追踪记录"""
        traces = list(self._traces.values())
        if filter:
            traces = [t for t in traces if self._match(t, filter)]
        return traces
```

### 8.2 性能监控

```python
class PerformanceMonitor:
    """性能监控"""

    def __init__(self):
        self._call_times = {}  # tool_name -> [duration1, duration2, ...]
        self._call_counts = {}  # tool_name -> count
        self._error_rates = {}  # tool_name -> error_rate

    def record_call(
        self,
        tool_name: str,
        duration: float,
        success: bool
    ):
        """记录调用"""
        if tool_name not in self._call_times:
            self._call_times[tool_name] = []
            self._call_counts[tool_name] = 0

        self._call_times[tool_name].append(duration)
        self._call_counts[tool_name] += 1

        # 更新错误率
        if not success:
            error_count = self._error_rates.get(tool_name, 0) + 1
            self._error_rates[tool_name] = (
                error_count / self._call_counts[tool_name]
            )

    def get_stats(self, tool_name: str) -> dict:
        """获取统计信息"""
        times = self._call_times.get(tool_name, [])
        if not times:
            return {}

        return {
            "total_calls": self._call_counts.get(tool_name, 0),
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "error_rate": self._error_rates.get(tool_name, 0)
        }
```

---

## 九、使用示例

### 9.1 基础使用

```python
from src.tools import FunctionCallingEngine
from src.tools.builtin import register_builtin_tools

# 初始化引擎
engine = FunctionCallingEngine()

# 注册内置工具
register_builtin_tools(engine)

# 用户查询
user_query = "搜索最新的AI新闻，然后总结一下"

# LLM 生成工具调用
llm_response = await llm.generate_with_tools(
    query=user_query,
    tools=engine.list_tools()
)

# 提取工具调用
tool_calls = llm_response.tool_calls

# 执行工具调用
results = await engine.execute_batch(tool_calls)

# 生成最终回复
final_response = await llm.generate_with_context(
    query=user_query,
    tool_results=results
)
```

### 9.2 单个工具调用

```python
from src.tools import get_function_registry

registry = get_function_registry()

# 直接调用工具
result = await registry.call(
    tool_name="web_search",
    parameters={
        "query": "人工智能最新进展",
        "num_results": 5
    }
)

print(result)
```

### 9.3 自定义工具使用

```python
from src.tools import Tool, ToolCategory, ToolParameter
from src.tools import get_function_registry

# 定义工具
def calculate_fibonacci(n: int) -> int:
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

fib_tool = Tool(
    name="calculate_fibonacci",
    description="计算斐波那契数列的第n项",
    category=ToolCategory.CUSTOM,
    parameters=[
        ToolParameter(
            name="n",
            type="integer",
            description="要计算的项数",
            required=True
        )
    ],
    function=calculate_fibonacci
)

# 注册工具
registry = get_function_registry()
registry.register(fib_tool)

# 使用工具
result = await registry.call(
    tool_name="calculate_fibonacci",
    parameters={"n": 10}
)
print(f"Fibonacci(10) = {result}")
```

---

## 十、最佳实践

### 10.1 工具设计原则

| 原则 | 说明 | 示例 |
|------|------|------|
| **单一职责** | 每个工具只做一件事 | `web_search` 和 `vector_search` 分开 |
| **参数精简** | 必需参数最少化 | 搜索设置合理的默认值 |
| **描述清晰** | LLM 能理解工具用途 | "搜索Web获取实时信息" |
| **返回结构化** | 返回标准化的结果 | `{"results": [...], "total": 10}` |
| **幂等性** | 相同参数返回相同结果 | 查询类操作保持幂等 |

### 10.2 性能优化

```python
# 1. 批量操作
@tool
async def batch_vector_search(queries: List[str]) -> List[SearchResult]:
    """批量向量搜索，减少网络往返"""
    return await vector_store.batch_search(queries)

# 2. 缓存结果
@tool
@cache(ttl=300)  # 缓存5分钟
async def get_weather(city: str) -> dict:
    """获取天气信息（带缓存）"""
    return await weather_api.get(city)

# 3. 超时控制
@tool(timeout=10)
async def quick_search(query: str) -> List[str]:
    """快速搜索，10秒超时"""
    return await search_api.search(query, timeout=10)
```

### 10.3 安全考虑

```python
# 1. 参数验证
@tool
async def code_execute(code: str, sandbox: bool = True) -> ExecutionResult:
    """代码执行 - 强制沙箱"""
    if not sandbox:
        raise ValueError("沙箱必须启用")
    return await safe_execute(code)

# 2. 敏感信息过滤
@tool
async def send_email(to: str, subject: str, body: str) -> bool:
    """发送邮件 - 验证收件人"""
    if not is_allowed_recipient(to):
        raise ValueError(f"不允许发送到: {to}")
    return await email_service.send(to, subject, body)

# 3. 权限控制
@tool(requires_permission="data:read")
async def query_database(sql: str) -> List[dict]:
    """数据库查询 - 需要权限"""
    check_permission("data:read")
    return await database.execute(sql)
```

---

## 十一、参考实现

### 11.1 核心接口

```python
# src/tools/engine.py
class FunctionCallingEngine:
    """Function Calling 引擎"""

    def __init__(self):
        self.registry = FunctionRegistry()
        self.planner = CallingPlanner()
        self.executor = ExecutionEngine()
        self.tracer = Tracer()
        self.monitor = PerformanceMonitor()

    async def call(
        self,
        tool_name: str,
        parameters: dict,
        timeout: int = None
    ) -> Any:
        """单个工具调用"""
        tool = self.registry.get(tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool not found: {tool_name}")

        # 验证参数
        self._validate_parameters(tool, parameters)

        # 追踪开始
        call_id = self.tracer.start_call(tool_name, parameters)

        try:
            # 执行调用
            result = await self._execute_tool(tool, parameters, timeout)

            # 追踪结束
            self.tracer.finish_call(call_id, "success", result)

            # 记录性能
            duration = (datetime.now() - self.tracer.get_trace(call_id).start_time).total_seconds()
            self.monitor.record_call(tool_name, duration, True)

            return result

        except Exception as e:
            # 追踪错误
            self.tracer.finish_call(call_id, "error", error=str(e))

            # 记录性能
            duration = (datetime.now() - self.tracer.get_trace(call_id).start_time).total_seconds()
            self.monitor.record_call(tool_name, duration, False)

            raise ExecutionFailedError(f"Tool execution failed: {e}")

    async def execute_batch(
        self,
        calls: List[FunctionCall]
    ) -> List[FunctionResult]:
        """批量执行工具调用"""
        # 规划执行
        plan = await self.planner.plan(calls, self.registry)

        # 执行
        results = await self.executor.execute(plan)

        return results

    def _validate_parameters(self, tool: Tool, parameters: dict):
        """验证参数"""
        # 检查必需参数
        required = {p.name for p in tool.parameters if p.required}
        missing = required - set(parameters.keys())
        if missing:
            raise ParameterValidationError(f"Missing required parameters: {missing}")

        # 检查参数类型（可通过 Pydantic 增强）
        # TODO: 添加更详细的类型验证
```

---

## 十二、未来扩展

### 12.1 计划功能

| 功能 | 状态 | 优先级 |
|------|------|--------|
| 流式 Function Calling | 待实现 | 高 |
| 工具链编排 | 待实现 | 中 |
| 动态工具发现 | 待实现 | 中 |
| 工具市场 | 规划中 | 低 |
| 工具版本管理 | 规划中 | 低 |

### 12.2 集成方向

- **与 Agent 深度集成**：Agent 自主决策工具调用
- **与 Skills 联动**：技能组合调用工具
- **MCP 生态对接**：自动发现和注册 MCP 工具
- **多模型支持**：兼容不同 LLM 的 Function Calling 格式

---

## 附录

### A. 工具元数据示例

```python
TOOL_METADATA = {
    "web_search": {
        "version": "1.0.0",
        "author": "Agentic GraphRAG Team",
        "tags": ["search", "web", "real-time"],
        "dependencies": ["httpx"],
        "rate_limit": 10,  # 每分钟最大调用次数
        "cost_per_call": 0.001  # 每次调用成本
    }
}
```

### B. 错误码参考

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| TOOL_NOT_FOUND | 工具不存在 | 404 |
| INVALID_PARAMETERS | 参数验证失败 | 400 |
| EXECUTION_TIMEOUT | 执行超时 | 408 |
| EXECUTION_FAILED | 执行失败 | 500 |
| PERMISSION_DENIED | 权限不足 | 403 |

---

*文档版本：v1.0*
*最后更新：2026-03-11*
