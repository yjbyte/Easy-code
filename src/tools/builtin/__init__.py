"""
内置工具注册
"""
import asyncio
import os
from pathlib import Path
from typing import List, Any, Optional

from src.tools.models import Tool, ToolCategory, ToolParameter
from src.tools.engine import FunctionCallingEngine


# ============ 内置工具实现 ============

async def _web_search_impl(query: str, num_results: int = 5) -> dict:
    """Web 搜索实现（示例）"""
    # TODO: 接入真实的搜索 API
    await asyncio.sleep(0.5)  # 模拟网络延迟

    # 检测是否为天气查询
    if "天气" in query or "weather" in query.lower():
        # 提取城市名
        import re
        city_match = re.search(r'(\w+市|\w+省|\w+国)', query)
        city = city_match.group(1) if city_match else query

        return {
            "query": query,
            "results": [
                {
                    "title": f"{city}今日天气预报",
                    "url": f"https://weather.com/{city}",
                    "snippet": f"{city}今日天气：晴转多云，气温 15-25℃，空气质量良好。东南风 2-3 级。"
                },
                {
                    "title": f"{city}实时天气信息",
                    "url": f"https://weather.cn/{city}",
                    "snippet": f"{city}当前温度：21℃，湿度：65%，风力：东南风 2 级。今日紫外线指数：中等。"
                },
                {
                    "title": f"{city}未来一周天气预报",
                    "url": f"https://weather.cn/{city}/week",
                    "snippet": f"{city}未来三天：今日晴转多云 15-25℃，明日多云 16-24℃，后天阴有小雨 14-22℃。"
                }
            ],
            "total": num_results
        }

    # 默认搜索结果
    return {
        "query": query,
        "results": [
            {"title": f"关于 {query} 的搜索结果 1", "url": f"https://example.com/1", "snippet": f"{query} 的相关信息和内容..."},
            {"title": f"{query} - 详细介绍", "url": f"https://example.com/2", "snippet": f"更多关于 {query} 的详细内容..."},
            {"title": f"{query} 相关资料", "url": f"https://example.com/3", "snippet": f"{query} 的相关资料和参考信息..."}
        ],
        "total": num_results
    }


async def _code_execute_impl(code: str, language: str = "python") -> dict:
    """代码执行实现（示例）"""
    # TODO: 接入真实的代码执行沙箱
    await asyncio.sleep(0.3)

    return {
        "language": language,
        "code": code,
        "output": f"执行结果: {code[:50]}...",
        "success": True
    }


async def _get_current_time_impl(timezone: str = "UTC") -> dict:
    """获取当前时间"""
    from datetime import datetime

    now = datetime.now()

    return {
        "timezone": timezone,
        "datetime": now.isoformat(),
        "timestamp": int(now.timestamp())
    }


async def _calculate_impl(expression: str) -> dict:
    """简单计算器"""
    try:
        # 注意：生产环境应使用更安全的方式
        result = eval(expression, {"__builtins__": {}}, {})
        return {
            "expression": expression,
            "result": result,
            "success": True
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "success": False
        }


async def _get_system_info_impl() -> dict:
    """获取系统信息"""
    return {
        "system_name": "Agentic GraphRAG",
        "version": "1.0.0",
        "description": "基于 ReAct 范式的智能体驱动的图增强检索生成系统",
        "llm_provider": "智谱 AI (Zhipu AI)",
        "llm_model": "GLM-4",
        "architecture": "GraphRAG + ReAct Agent + Function Calling + MCP Protocol",
        "capabilities": [
            "知识图谱检索 - 基于实体和关系的深层语义检索",
            "向量相似度检索 - 文档级语义匹配",
            "多跳推理 - 沿图谱路径进行推理分析",
            "实时数据获取 - 网络搜索获取最新信息",
            "代码执行 - 沙箱环境运行代码",
            "MCP 协议支持 - 可扩展的外部数据源连接"
        ],
        "system_info": {
            "底层 LLM": "智谱 GLM-4",
            "架构模式": "ReAct (Reasoning + Acting) 范式",
            "核心组件": [
                "ReAct Agent - 智能体编排",
                "Skills 系统 - 模块化技能",
                "Function Calling - 工具调用引擎",
                "MCP 协议 - 外部服务集成"
            ]
        }
    }


async def _read_file_impl(file_path: str, encoding: str = "utf-8") -> dict:
    """
    读取文件内容

    Args:
        file_path: 文件路径（绝对路径或相对路径）
        encoding: 文件编码，默认 utf-8

    Returns:
        包含文件内容和元数据的字典
    """
    try:
        path = Path(file_path)

        # 如果是相对路径，尝试从当前工作目录解析
        if not path.is_absolute():
            path = Path.cwd() / file_path

        # 安全检查：确保路径在允许的目录内
        allowed_dirs = [
            Path.cwd(),  # 当前工作目录
            Path.home() / "Documents",  # 用户文档目录
            Path.home() / "Desktop",    # 用户桌面
        ]

        is_allowed = False
        for allowed_dir in allowed_dirs:
            try:
                path.resolve().relative_to(allowed_dir.resolve())
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            return {
                "success": False,
                "error": f"访问被拒绝：路径不在允许的目录内",
                "file_path": str(path)
            }

        # 检查文件是否存在
        if not path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {file_path}",
                "file_path": str(path)
            }

        # 检查是否为文件
        if not path.is_file():
            return {
                "success": False,
                "error": f"路径不是文件: {file_path}",
                "file_path": str(path)
            }

        # 读取文件内容
        content = path.read_text(encoding=encoding)

        # 获取文件信息
        stat = path.stat()

        return {
            "success": True,
            "file_path": str(path.resolve()),
            "file_name": path.name,
            "file_size": stat.st_size,
            "encoding": encoding,
            "content": content,
            "line_count": len(content.splitlines()) if content else 0,
            "message": f"成功读取文件: {path.name}"
        }

    except PermissionError:
        return {
            "success": False,
            "error": f"权限不足: 无法读取文件 {file_path}",
            "file_path": file_path
        }
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"编码错误: 无法使用 {encoding} 编码读取文件: {str(e)}",
            "file_path": file_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"读取文件失败: {str(e)}",
            "file_path": file_path
        }


async def _write_file_impl(file_path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True) -> dict:
    """
    写入文件内容（覆盖现有文件）

    Args:
        file_path: 文件路径
        content: 要写入的内容
        encoding: 文件编码，默认 utf-8
        create_dirs: 是否自动创建目录，默认 True

    Returns:
        包含操作结果的字典
    """
    try:
        path = Path(file_path)

        # 如果是相对路径，从当前工作目录解析
        if not path.is_absolute():
            path = Path.cwd() / file_path

        # 安全检查
        allowed_dirs = [
            Path.cwd(),
            Path.home() / "Documents",
            Path.home() / "Desktop",
        ]

        is_allowed = False
        for allowed_dir in allowed_dirs:
            try:
                path.resolve().relative_to(allowed_dir.resolve())
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            return {
                "success": False,
                "error": f"访问被拒绝：路径不在允许的目录内",
                "file_path": str(path)
            }

        # 创建目录（如果需要）
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        path.write_text(content, encoding=encoding)

        # 获取文件信息
        stat = path.stat()

        return {
            "success": True,
            "file_path": str(path.resolve()),
            "file_name": path.name,
            "file_size": stat.st_size,
            "encoding": encoding,
            "bytes_written": len(content.encode(encoding)),
            "message": f"成功写入文件: {path.name}"
        }

    except PermissionError:
        return {
            "success": False,
            "error": f"权限不足: 无法写入文件 {file_path}",
            "file_path": file_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"写入文件失败: {str(e)}",
            "file_path": file_path
        }


async def _create_file_impl(file_path: str, content: str = "", encoding: str = "utf-8", create_dirs: bool = True, overwrite: bool = False) -> dict:
    """
    创建新文件

    Args:
        file_path: 文件路径
        content: 初始内容，默认为空
        encoding: 文件编码，默认 utf-8
        create_dirs: 是否自动创建目录，默认 True
        overwrite: 是否覆盖已存在的文件，默认 False

    Returns:
        包含操作结果的字典
    """
    try:
        path = Path(file_path)

        # 如果是相对路径，从当前工作目录解析
        if not path.is_absolute():
            path = Path.cwd() / file_path

        # 安全检查
        allowed_dirs = [
            Path.cwd(),
            Path.home() / "Documents",
            Path.home() / "Desktop",
        ]

        is_allowed = False
        for allowed_dir in allowed_dirs:
            try:
                path.resolve().relative_to(allowed_dir.resolve())
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            return {
                "success": False,
                "error": f"访问被拒绝：路径不在允许的目录内",
                "file_path": str(path)
            }

        # 检查文件是否已存在
        if path.exists() and not overwrite:
            return {
                "success": False,
                "error": f"文件已存在: {file_path}（如需覆盖，请设置 overwrite=True）",
                "file_path": str(path)
            }

        # 创建目录（如果需要）
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件
        path.write_text(content, encoding=encoding)

        return {
            "success": True,
            "file_path": str(path.resolve()),
            "file_name": path.name,
            "encoding": encoding,
            "content_length": len(content),
            "message": f"成功创建文件: {path.name}"
        }

    except PermissionError:
        return {
            "success": False,
            "error": f"权限不足: 无法创建文件 {file_path}",
            "file_path": file_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"创建文件失败: {str(e)}",
            "file_path": file_path
        }


# ============ 工具定义 ============

WEB_SEARCH_TOOL = Tool(
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
    async_mode=True
)
WEB_SEARCH_TOOL.set_function(_web_search_impl)


CODE_EXECUTE_TOOL = Tool(
    name="code_execute",
    description="在沙箱环境中执行代码",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="code",
            type="string",
            description="要执行的代码",
            required=True
        ),
        ToolParameter(
            name="language",
            type="string",
            description="编程语言",
            required=False,
            default="python",
            enum=["python", "javascript", "bash"]
        )
    ],
    async_mode=True
)
CODE_EXECUTE_TOOL.set_function(_code_execute_impl)


GET_CURRENT_TIME_TOOL = Tool(
    name="get_current_time",
    description="获取当前时间",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="timezone",
            type="string",
            description="时区",
            required=False,
            default="UTC"
        )
    ],
    async_mode=True
)
GET_CURRENT_TIME_TOOL.set_function(_get_current_time_impl)


CALCULATE_TOOL = Tool(
    name="calculate",
    description="执行数学计算",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="expression",
            type="string",
            description="数学表达式，如: 2 + 3 * 4",
            required=True
        )
    ],
    async_mode=True
)
CALCULATE_TOOL.set_function(_calculate_impl)


GET_SYSTEM_INFO_TOOL = Tool(
    name="get_system_info",
    description="获取系统信息，包括使用的LLM模型、架构、能力等",
    category=ToolCategory.BUILTIN,
    parameters=[],
    async_mode=True
)
GET_SYSTEM_INFO_TOOL.set_function(_get_system_info_impl)


READ_FILE_TOOL = Tool(
    name="read_file",
    description="读取文件内容，支持相对路径和绝对路径",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="文件路径（可以是相对路径或绝对路径）",
            required=True
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="文件编码，默认 utf-8",
            required=False,
            default="utf-8"
        )
    ],
    async_mode=True
)
READ_FILE_TOOL.set_function(_read_file_impl)


WRITE_FILE_TOOL = Tool(
    name="write_file",
    description="写入文件内容（覆盖现有文件），可自动创建目录",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="文件路径（可以是相对路径或绝对路径）",
            required=True
        ),
        ToolParameter(
            name="content",
            type="string",
            description="要写入的内容",
            required=True
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="文件编码，默认 utf-8",
            required=False,
            default="utf-8"
        ),
        ToolParameter(
            name="create_dirs",
            type="boolean",
            description="是否自动创建目录，默认 True",
            required=False,
            default=True
        )
    ],
    async_mode=True
)
WRITE_FILE_TOOL.set_function(_write_file_impl)


CREATE_FILE_TOOL = Tool(
    name="create_file",
    description="创建新文件，如果文件已存在则失败（除非设置 overwrite=True），可自动创建目录",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="文件路径（可以是相对路径或绝对路径）",
            required=True
        ),
        ToolParameter(
            name="content",
            type="string",
            description="初始内容，默认为空字符串",
            required=False,
            default=""
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="文件编码，默认 utf-8",
            required=False,
            default="utf-8"
        ),
        ToolParameter(
            name="create_dirs",
            type="boolean",
            description="是否自动创建目录，默认 True",
            required=False,
            default=True
        ),
        ToolParameter(
            name="overwrite",
            type="boolean",
            description="是否覆盖已存在的文件，默认 False",
            required=False,
            default=False
        )
    ],
    async_mode=True
)
CREATE_FILE_TOOL.set_function(_create_file_impl)


# ============ RAG 工具实现 ============

async def _knowledge_search_impl(
    query: str,
    top_k: int = 5,
    method: str = "hybrid",
    filters: Optional[dict] = None
) -> dict:
    """
    知识库检索工具

    从向量数据库和知识图谱中检索相关文档内容
    """
    try:
        from src.rag.retrievers import get_knowledge_retriever

        print(f"[DEBUG knowledge_search] Starting search: query='{query}', top_k={top_k}, method={method}, filters={filters}")

        retriever = get_knowledge_retriever()

        # 根据不同的检索方法构建参数
        if method == "vector":
            # 向量检索支持 filters
            results = await retriever.search(
                query,
                top_k=top_k,
                method=method,
                filters=filters
            )
        elif method == "graph":
            # 图谱检索支持 entities
            results = await retriever.search(
                query,
                top_k=top_k,
                method=method,
                entities=filters.get("entities") if filters else None
            )
        else:  # hybrid
            # 混合检索暂不支持 filters
            results = await retriever.search(
                query,
                top_k=top_k,
                method=method
            )

        print(f"[DEBUG knowledge_search] Search completed: {len(results)} results found")

        return {
            "query": query,
            "method": method,
            "results": [
                {
                    "content": r.content,
                    "score": round(float(r.score), 4) if r.score is not None else 0,
                    "source": r.source,
                    "metadata": r.metadata
                }
                for r in results
            ],
            "total": len(results),
            "message": f"成功从知识库检索到 {len(results)} 条相关内容" if results else "未检索到相关内容"
        }

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[DEBUG knowledge_search] Error occurred: {str(e)}\n{error_details}")
        return {
            "success": False,
            "error": f"知识库检索失败: {str(e)}",
            "query": query,
            "results": [],
            "total": 0
        }


async def _document_upload_impl(
    file_path: str,
    chunk_size: int = 500,
    process_graph: bool = True
) -> dict:
    """
    文档上传工具

    上传文档到知识库，进行解析、分片、向量化，并可选地构建知识图谱
    """
    try:
        from src.rag.parsers import parse_document
        from src.rag.chunkers import chunk_document
        from src.rag.embeddings import get_embedding_model
        from src.rag.stores import get_vector_store, get_graph_store
        from src.rag.extractors import get_graph_builder
        import uuid

        # 1. 解析文档
        document = parse_document(file_path)

        # 2. 分片处理
        chunks = chunk_document(document, chunker_type="rule")

        # 3. 向量化并存储到 Qdrant
        embedding_model = get_embedding_model()
        embeddings = embedding_model.embed([c.content for c in chunks])

        vector_store = get_vector_store()
        chunk_ids = vector_store.insert_chunks(chunks, embeddings)

        # 4. 可选：构建知识图谱
        graph_info = {}
        if process_graph:
            try:
                graph_builder = get_graph_builder()
                entities, relations = await graph_builder.build_from_chunks(
                    [c.content for c in chunks],
                    source=file_path
                )

                # 存储到 Neo4j
                graph_store = get_graph_store()
                for entity in entities:
                    graph_store.create_entity(entity, source=file_path)

                for relation in relations:
                    graph_store.create_relation(relation)

                graph_info = {
                    "entities_extracted": len(entities),
                    "relations_extracted": len(relations)
                }
            except Exception as e:
                graph_info = {"error": f"知识图谱构建失败: {str(e)}"}

        return {
            "success": True,
            "document_id": document.doc_id,
            "filename": document.metadata.get("filename", ""),
            "chunks_count": len(chunks),
            "file_size": document.metadata.get("size", 0),
            "doc_type": document.doc_type.value,
            "graph_info": graph_info,
            "message": f"成功上传文档 {document.metadata.get('filename', file_path)}，共 {len(chunks)} 个分片"
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"文档上传失败: {str(e)}",
            "details": traceback.format_exc(),
            "message": f"上传失败: {str(e)}"
        }


# ============ RAG 工具定义 ============

KNOWLEDGE_SEARCH_TOOL = Tool(
    name="knowledge_search",
    description="从知识库中检索相关文档内容，支持向量检索、图谱检索和混合检索",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="检索问题或关键词",
            required=True
        ),
        ToolParameter(
            name="top_k",
            type="integer",
            description="返回结果数量，默认 5",
            required=False,
            default=5
        ),
        ToolParameter(
            name="method",
            type="string",
            description="检索方法：vector(向量)、graph(图谱)、hybrid(混合)，默认 hybrid",
            required=False,
            default="hybrid",
            enum=["vector", "graph", "hybrid"]
        ),
        ToolParameter(
            name="filters",
            type="object",
            description="过滤条件，如 {\"doc_id\": \"xxx\"}",
            required=False
        )
    ],
    async_mode=True
)
KNOWLEDGE_SEARCH_TOOL.set_function(_knowledge_search_impl)


DOCUMENT_UPLOAD_TOOL = Tool(
    name="document_upload",
    description="上传文档到知识库，支持 txt、md、pdf 等格式。会自动解析、分片、向量化并构建知识图谱",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="文档文件路径（支持相对路径和绝对路径）",
            required=True
        ),
        ToolParameter(
            name="chunk_size",
            type="integer",
            description="分片大小（字符数），默认 500",
            required=False,
            default=500
        ),
        ToolParameter(
            name="process_graph",
            type="boolean",
            description="是否构建知识图谱，默认 True",
            required=False,
            default=True
        )
    ],
    async_mode=True
)
DOCUMENT_UPLOAD_TOOL.set_function(_document_upload_impl)


# ============ Todo List 工具实现 ============

# 内存存储，用于保存 todo 项
_todo_items: List[dict] = []


def _generate_todo_id() -> str:
    """生成唯一的任务 ID"""
    import uuid
    return str(uuid.uuid4())[:8]


async def _todo_add_impl(task: str, priority: str = "medium", due_date: Optional[str] = None) -> dict:
    """
    添加任务到待办列表
    """
    try:
        todo_id = _generate_todo_id()
        todo_item = {
            "id": todo_id,
            "task": task,
            "priority": priority,  # high, medium, low
            "status": "pending",   # pending, completed
            "due_date": due_date,
            "created_at": str(asyncio.get_event_loop().time())
        }
        _todo_items.append(todo_item)

        return {
            "success": True,
            "todo_id": todo_id,
            "task": task,
            "priority": priority,
            "status": "pending",
            "message": f"已添加任务: {task}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"添加任务失败: {str(e)}"
        }


async def _todo_list_impl(status: Optional[str] = None) -> dict:
    """
    列出所有待办任务
    """
    try:
        items = _todo_items

        # 按状态过滤
        if status:
            items = [item for item in items if item["status"] == status]

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        items = sorted(items, key=lambda x: (priority_order.get(x["priority"], 1), x["status"] == "completed"))

        return {
            "success": True,
            "total": len(items),
            "results": [
                {
                    "id": item["id"],
                    "task": item["task"],
                    "priority": item["priority"],
                    "status": item["status"],
                    "due_date": item.get("due_date")
                }
                for item in items
            ],
            "message": f"找到 {len(items)} 个任务"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"获取任务列表失败: {str(e)}",
            "results": [],
            "total": 0
        }


async def _todo_complete_impl(todo_id: str) -> dict:
    """
    标记任务为已完成
    """
    try:
        for item in _todo_items:
            if item["id"] == todo_id:
                item["status"] = "completed"
                return {
                    "success": True,
                    "todo_id": todo_id,
                    "task": item["task"],
                    "status": "completed",
                    "message": f"已完成任务: {item['task']}"
                }

        return {
            "success": False,
            "error": f"未找到 ID 为 {todo_id} 的任务"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"完成任务失败: {str(e)}"
        }


async def _todo_delete_impl(todo_id: str) -> dict:
    """
    删除任务
    """
    try:
        global _todo_items
        for i, item in enumerate(_todo_items):
            if item["id"] == todo_id:
                deleted_task = _todo_items.pop(i)
                return {
                    "success": True,
                    "todo_id": todo_id,
                    "task": deleted_task["task"],
                    "message": f"已删除任务: {deleted_task['task']}"
                }

        return {
            "success": False,
            "error": f"未找到 ID 为 {todo_id} 的任务"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"删除任务失败: {str(e)}"
        }


async def _todo_clear_impl(completed_only: bool = False) -> dict:
    """
    清空任务列表
    """
    try:
        global _todo_items

        if completed_only:
            # 只清除已完成的任务
            before_count = len(_todo_items)
            _todo_items = [item for item in _todo_items if item["status"] != "completed"]
            cleared_count = before_count - len(_todo_items)
            return {
                "success": True,
                "cleared_count": cleared_count,
                "remaining": len(_todo_items),
                "message": f"已清除 {cleared_count} 个已完成的任务"
            }
        else:
            # 清除所有任务
            count = len(_todo_items)
            _todo_items = []
            return {
                "success": True,
                "cleared_count": count,
                "remaining": 0,
                "message": f"已清除所有 {count} 个任务"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"清除任务失败: {str(e)}"
        }


# ============ Todo List 工具定义 ============

TODO_ADD_TOOL = Tool(
    name="todo_add",
    description="添加一个新的待办任务",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="task",
            type="string",
            description="任务描述",
            required=True
        ),
        ToolParameter(
            name="priority",
            type="string",
            description="优先级：high(高)、medium(中)、low(低)，默认 medium",
            required=False,
            default="medium",
            enum=["high", "medium", "low"]
        ),
        ToolParameter(
            name="due_date",
            type="string",
            description="截止日期，格式如：2024-01-01",
            required=False
        )
    ],
    async_mode=True
)
TODO_ADD_TOOL.set_function(_todo_add_impl)


TODO_LIST_TOOL = Tool(
    name="todo_list",
    description="列出所有待办任务，可按状态筛选",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="status",
            type="string",
            description="筛选状态：pending(未完成)、completed(已完成)，不传则返回所有",
            required=False,
            enum=["pending", "completed"]
        )
    ],
    async_mode=True
)
TODO_LIST_TOOL.set_function(_todo_list_impl)


TODO_COMPLETE_TOOL = Tool(
    name="todo_complete",
    description="标记指定任务为已完成",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="todo_id",
            type="string",
            description="任务 ID",
            required=True
        )
    ],
    async_mode=True
)
TODO_COMPLETE_TOOL.set_function(_todo_complete_impl)


TODO_DELETE_TOOL = Tool(
    name="todo_delete",
    description="删除指定的任务",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="todo_id",
            type="string",
            description="任务 ID",
            required=True
        )
    ],
    async_mode=True
)
TODO_DELETE_TOOL.set_function(_todo_delete_impl)


TODO_CLEAR_TOOL = Tool(
    name="todo_clear",
    description="清空任务列表，可选择性只清除已完成的任务",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="completed_only",
            type="boolean",
            description="是否只清除已完成的任务，默认 False（清除所有）",
            required=False,
            default=False
        )
    ],
    async_mode=True
)
TODO_CLEAR_TOOL.set_function(_todo_clear_impl)


# ============ 内置工具列表 ============

BUILTIN_TOOLS: List[Tool] = [
    WEB_SEARCH_TOOL,
    CODE_EXECUTE_TOOL,
    GET_CURRENT_TIME_TOOL,
    CALCULATE_TOOL,
    GET_SYSTEM_INFO_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    CREATE_FILE_TOOL,
    KNOWLEDGE_SEARCH_TOOL,
    DOCUMENT_UPLOAD_TOOL,
    TODO_ADD_TOOL,
    TODO_LIST_TOOL,
    TODO_COMPLETE_TOOL,
    TODO_DELETE_TOOL,
    TODO_CLEAR_TOOL,
]


# ============ 注册函数 ============

def register_builtin_tools(engine: FunctionCallingEngine) -> None:
    """
    注册所有内置工具到引擎

    Args:
        engine: Function Calling 引擎
    """
    for tool in BUILTIN_TOOLS:
        try:
            engine.register_tool(tool)
        except Exception as e:
            print(f"Warning: Failed to register tool {tool.name}: {e}")


def get_builtin_tools() -> List[Tool]:
    """获取所有内置工具定义"""
    return BUILTIN_TOOLS.copy()
