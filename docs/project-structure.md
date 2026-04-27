# 项目目录结构说明

## 目录树

```
agentic-graph-rag/
├── docs/                      # 文档目录
│   ├── requirements.md        # 总体需求文档
│   ├── project-structure.md   # 项目结构说明（本文件）
│   └── *.md                   # 其他设计文档
│
├── src/                       # 源代码目录
│   ├── __init__.py
│   │
│   ├── agent/                 # Agent 核心
│   │   ├── __init__.py
│   │   ├── react_agent.py     # ReAct Agent 实现
│   │   ├── team.py            # Agent Team（队列协作）
│   │   ├── intent.py          # 意图分析
│   │   └── models.py          # 数据模型
│   │
│   ├── tools/                 # Function Calling 工具系统
│   │   ├── __init__.py
│   │   ├── engine.py          # 主引擎
│   │   ├── registry.py        # 工具注册表
│   │   ├── executor.py        # 执行器
│   │   ├── planner.py         # 调用规划器
│   │   ├── models.py          # 数据模型
│   │   ├── errors.py          # 错误定义
│   │   └── builtin/           # 内置工具
│   │       └── __init__.py
│   │
│   ├── skills/                # Skills 技能系统
│   │   ├── __init__.py
│   │   ├── skill.py           # Skill 基类
│   │   └── builtin/           # 内置技能
│   │
│   ├── context/               # 上下文工程
│   │   ├── __init__.py
│   │   ├── manager.py         # 上下文管理器
│   │   └── compressor.py      # 上下文压缩器
│   │
│   ├── observability/         # 可观测性
│   │   ├── __init__.py
│   │   ├── trace.py           # 全链路追踪
│   │   └── metrics.py         # 性能指标
│   │
│   ├── data/                  # 数据层
│   │   ├── __init__.py
│   │   ├── vector.py          # 向量存储
│   │   ├── graph.py           # 图谱存储
│   │   └── document.py        # 文档存储
│   │
│   ├── mcp/                   # MCP 协议支持
│   │   ├── __init__.py
│   │   ├── client.py          # MCP 客户端
│   │   ├── adapter.py         # MCP 适配器
│   │   ├── models.py          # 数据模型
│   │   └── errors.py          # 错误定义
│   │
│   ├── api/                   # API 服务
│   │   ├── __init__.py
│   │   ├── main.py            # 主入口
│   │   ├── app.py             # FastAPI 应用
│   │   ├── routes/            # 路由
│   │   ├── v1/                # v1 API
│   │   │   ├── chat.py        # 聊天接口
│   │   │   ├── tools.py       # 工具接口
│   │   │   ├── health.py      # 健康检查
│   │   │   └── mcp.py         # MCP 接口
│   │   └── middleware/        # 中间件
│   │
│   ├── config/                # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py        # 全局配置
│   │   └── prompts.py         # 提示词模板
│   │
│   └── utils/                 # 工具函数
│       ├── __init__.py
│       └── llm.py             # LLM 客户端
│
├── tests/                     # 测试目录
│   ├── unit/                  # 单元测试
│   └── integration/           # 集成测试
│
├── frontend/                  # 前端项目
│   └── src/
│       ├── main.js
│       ├── api/
│       │   └── chat.js        # 聊天 API
│       └── ...
│
├── logs/                      # 日志目录
├── data/                      # 数据目录
│
├── .env.example               # 环境变量示例
├── .gitignore
├── requirements.txt           # 依赖列表
├── pyproject.toml             # 项目配置
├── run_server.py              # 服务启动脚本
├── README.md                  # 项目说明
└── LICENSE                    # 许可证
```

## 模块依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                        Vue 前端                              │
│  - 聊天界面  -  Trace 可视化  -  工具管理                    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                      FastAPI 后端                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              ReAct Agent Engine                         │ │
│  │   - 意图分析  -  思考-行动循环  -  答案生成              │ │
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
│  │  向量库  │  知识图谱  │  文档存储  │  缓存              │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 模块说明

### agent/ - Agent 核心
- `react_agent.py`: ReAct Agent 实现，多轮推理-行动循环
- `team.py`: Agent Team，基于内存队列的多 Agent 协作
- `intent.py`: 意图分析，支持多意图理解
- `models.py`: Agent 相关数据模型

### tools/ - 工具系统
- `engine.py`: Function Calling 引擎主类
- `registry.py`: 工具注册表，支持动态注册/注销
- `executor.py`: 执行器，支持并行/串行执行
- `planner.py`: 调用规划器，分析依赖关系
- `models.py`: 工具数据模型
- `builtin/`: 内置工具（web_search, code_execute 等）

### skills/ - Skills 系统
- `skill.py`: Skill 基类和数据模型
- `builtin/`: 内置技能（query_analysis, multi_hop_reasoning 等）

### context/ - 上下文工程
- `manager.py`: 上下文管理器，控制窗口大小
- `compressor.py`: 上下文压缩器，工具输出截断、历史摘要

### observability/ - 可观测性
- `trace.py`: 全链路追踪，记录执行过程
- `metrics.py`: 性能指标收集和统计

### data/ - 数据层
- `vector.py`: 向量存储接口（知识图谱作为数据源）
- `graph.py`: 图谱存储接口
- `document.py`: 文档存储接口

### mcp/ - MCP 协议
- `client.py`: MCP 客户端
- `adapter.py`: MCP 适配器，将 MCP 工具转为本地工具
- `models.py`: MCP 数据模型

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 填入配置
```

3. 启动服务：
```bash
python run_server.py
# 或
python -m src.api.main
```

## 开发指南

### 添加新工具

```python
from src.tools import Tool, ToolParameter, ToolCategory

async def my_tool_func(param1: str) -> dict:
    """工具实现"""
    return {"result": "success"}

my_tool = Tool(
    name="my_tool",
    description="我的工具",
    category=ToolCategory.CUSTOM,
    parameters=[
        ToolParameter(
            name="param1",
            type="string",
            description="参数1",
            required=True
        )
    ],
    function=my_tool_func
)

# 注册工具
from src.tools import get_function_calling_engine
engine = get_function_calling_engine()
engine.register_tool(my_tool)
```

### 添加新技能

```python
from src.skills import Skill, SkillCategory, SkillContext, SkillResult

class MySkill(Skill):
    name = "my_skill"
    description = "我的技能"
    category = SkillCategory.ANALYSIS

    async def execute(self, context: SkillContext) -> SkillResult:
        param = context.get_input("param")
        return SkillResult(success=True, outputs={"result": param})
```

### 使用 Agent Team

```python
from src.agent.team import AgentTeam, WorkerConfig, Task, get_agent_team

team = get_agent_team()

# 注册 Worker
async def my_handler(task: Task):
    return await process_task(task)

config = WorkerConfig(
    worker_id="worker_1",
    name="My Worker",
    handler=my_handler
)
team.register_worker(config)

# 启动
await team.start()

# 提交任务
task = await team.submit_task(
    name="my_task",
    input_data={"param": "value"},
    priority=TaskPriority.HIGH
)

# 获取结果
result = await team.get_task_result(task.task_id)
```

## API 接口

### 聊天接口
```
POST /api/v1/chat
{
  "message": "用户消息",
  "history": [...]
}
```

### 获取 Trace
```
GET /api/v1/trace/{execution_id}
```

### 工具管理
```
GET /api/v1/tools/list       # 列出工具
POST /api/v1/tools/register  # 注册工具
```

---

*文档版本：v5.0*
*更新日期：2026-03-12*
*基于新需求文档重新组织*
