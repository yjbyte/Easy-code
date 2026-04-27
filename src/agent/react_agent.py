"""
ReAct Agent - 基于 Reasoning + Acting 范式的智能体

核心思想：
1. Thought: LLM 分析问题，决定需要什么行动
2. Action: 执行行动（调用工具）
3. Observation: 获取工具执行结果
4. 重复或生成最终答案
"""
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from src.utils.llm import get_glm_client
from src.tools.engine import get_function_calling_engine
from src.tools.builtin import register_builtin_tools


@dataclass
class ReActStep:
    """ReAct 执行步骤"""
    step_type: str  # "user", "thought", "action", "observation", "answer", "partial_answer", "error"
    content: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class ReActResult:
    """ReAct 执行结果"""
    answer: str
    steps: List[ReActStep]
    success: bool
    error: Optional[str] = None

    # 性能指标
    llm_calls: int = 0
    tool_calls: int = 0
    tokens_used: int = 0
    duration: Optional[float] = None
    iterations: int = 0


# ReAct 系统提示词
REACT_SYSTEM_PROMPT = """你是 Agentic GraphRAG 智能助手，基于 ReAct 范式工作。

你的核心能力：
- 知识库检索：从上传的文档中检索相关知识（使用 knowledge_search 工具）
- 文档上传：上传文档到知识库，支持 txt、md、pdf 等格式（使用 document_upload 工具）
- 实时搜索：通过网络搜索获取最新信息
- 系统信息：回答关于系统本身的问题
- 代码执行：执行代码解决问题
- 文件操作：读取、写入、创建文件
- 待办管理：管理用户的待办事项列表（使用 todo_add、todo_list、todo_complete、todo_delete、todo_clear 工具）

## 工作方式 (ReAct 范式)

对于用户问题，你必须严格按照以下流程：

1. **Thought**: 分析问题，思考需要什么信息
2. **Action**: 如果需要外部信息，必须调用工具
3. **Observation**: (系统返回) 获取工具执行结果
4. **Thought**: 分析观察结果
5. **Answer**: 基于观察结果给出最终答案

## 可用工具

{tools_description}

## 回答格式（严格遵守）

你的回答必须严格按照以下格式之一：

**格式1 - 需要调用工具：**

**Thought:** [你的思考过程，分析需要什么工具]

**Action:** [工具名称]
```json
{{"参数名": "参数值"}}
```

**格式2 - 收到 Observation 后：**

**Thought:** [分析观察到的具体数据]

**Answer:** [基于观察结果给用户的具体答案，必须引用观察到的数据]

**格式3 - 可以直接回答（仅限系统问题）：**

**Answer:** [直接回答]

## 重要规则（必须遵守）

1. **除非是可以直接回答的系统问题（如"你使用什么模型"），否则必须使用 Action 调用工具**
2. **对于实时数据（天气、新闻、股票等），必须使用 web_search 工具**
3. **对于需要查询已有知识库的问题，系统会自动进行预检索，请基于提供的预检索结果回答**
4. **如果预检索结果不足，可以继续使用 knowledge_search 工具进行更精确的检索**
5. **对于文件操作（读取、写入、创建），必须使用对应的文件工具**
6. **上传文档时使用 document_upload 工具，上传后可用 knowledge_search 检索**
7. **对于待办事项管理，必须使用对应的 todo_* 工具（todo_add、todo_list、todo_complete、todo_delete、todo_clear）**
8. **Action 后必须等待 Observation，不能直接跳到 Answer**
9. **收到 Observation 后，必须先用 Thought 分析，然后用 Answer**
10. **Answer 必须基于 Observation 的具体内容，不能编造数据**
11. **每次只能输出一个 Action 或 Answer，不能同时输出多个**
12. **多问题处理**: 如果用户问了多个问题，必须逐一调用工具获取每个问题的答案**

## 系统信息

- 底层 LLM: 智谱 AI GLM-4
- 架构: Agentic GraphRAG + ReAct 范式

## 示例

用户: "无锡市今天的天气如何？"

**Thought:** 用户询问无锡市今天的天气，这是实时数据查询，我需要使用 web_search 工具获取最新天气信息。

**Action:** web_search
```json
{{"query": "无锡市今天天气", "num_results": 3}}
```

[系统会返回 Observation]

**Thought:** 观察结果显示：无锡市今日天气晴转多云，气温15-25℃，空气质量良好，东南风2-3级。

**Answer:** 根据搜索结果，无锡市今天的天气是晴转多云，气温15-25℃，空气质量良好，东南风2-3级。

---

用户: "读取 README.md 文件的内容"

**Thought:** 用户要求读取文件内容，我需要使用 read_file 工具来读取文件。

**Action:** read_file
```json
{{"file_path": "README.md"}}
```

[系统会返回 Observation]

**Thought:** 文件读取成功，内容已获取。

**Answer:** README.md 文件内容如下：[展示文件内容]

---

用户: "创建一个名为 hello.txt 的文件，内容是 'Hello World'"

**Thought:** 用户要求创建一个新文件，我需要使用 create_file 工具。

**Action:** create_file
```json
{{"file_path": "hello.txt", "content": "Hello World"}}
```

[系统会返回 Observation]

**Thought:** 文件创建成功。

**Answer:** 已成功创建文件 hello.txt，内容为 "Hello World"。

---

用户: "从知识库中检索关于 GraphRAG 的相关信息"

**Thought:** 用户询问知识库中的内容，我需要使用 knowledge_search 工具检索相关知识。

**Action:** knowledge_search
```json
{{"query": "GraphRAG", "top_k": 5, "method": "hybrid"}}
```

[系统会返回 Observation]

**Thought:** 知识库检索成功，获得了相关文档内容。

**Answer:** 根据知识库检索结果，GraphRAG 是...[展示检索到的内容]

---

用户: "上传这个文档到知识库：data/technical_doc.pdf"

**Thought:** 用户要上传文档到知识库，我需要使用 document_upload 工具。

**Action:** document_upload
```json
{{"file_path": "data/technical_doc.pdf", "chunk_size": 500, "process_graph": true}}
```

[系统会返回 Observation]

**Thought:** 文档上传成功。

**Answer:** 已成功上传文档，共处理 X 个分片并构建了知识图谱。

---

用户: "帮我添加一个待办事项：明天下午3点开会"

**Thought:** 用户要添加待办任务，我需要使用 todo_add 工具。

**Action:** todo_add
```json
{{"task": "明天下午3点开会", "priority": "high"}}
```

[系统会返回 Observation]

**Thought:** 任务添加成功。

**Answer:** 已成功添加任务："明天下午3点开会"，优先级设为高。

---

用户: "我的待办事项有哪些？"

**Thought:** 用户查看待办列表，我需要使用 todo_list 工具。

**Action:** todo_list
```json
{{}}
```

[系统会返回 Observation]

**Thought:** 获取到待办列表。

**Answer:** 您当前有以下待办事项：[展示任务列表]

---

用户: "标记任务 abc123 为已完成"

**Thought:** 用户要完成指定任务，我需要使用 todo_complete 工具。

**Action:** todo_complete
```json
{{"todo_id": "abc123"}}
```

[系统会返回 Observation]

**Thought:** 任务已完成。

**Answer:** 已将任务标记为完成。

请严格遵守以上格式和规则。
"""


class ReActAgent:
    """ReAct 智能体"""

    # 多意图连接词
    MULTI_INTENT_KEYWORDS = ["以及", "还有", "另外", "同时", "，然后", "并且"]

    # 知识库查询意图关键词
    KNOWLEDGE_QUERY_KEYWORDS = [
        "查询", "检索", "搜索", "知识库", "文档", "资料",
        "什么是", "如何", "怎么", "怎样", "介绍一下",
        "关于", "相关", "技术", "架构", "设计", "实现"
    ]

    # 需要知识库查询的模式
    KNOWLEDGE_QUERY_PATTERNS = [
        r".*[查找搜]询.*知识库",
        r"从.*文档.*查找",
        r"在.*中.*检索",
        r"知识库.*有.*",
        r".*文档.*介绍",
    ]

    def __init__(self):
        self.llm_client = get_glm_client()
        self.tool_engine = get_function_calling_engine()
        self.max_iterations = 10  # 增加到10轮，支持多意图处理
        self._init_tools()

    def _detect_multi_intent(self, query: str) -> bool:
        """检测是否为多意图查询"""
        return any(keyword in query for keyword in self.MULTI_INTENT_KEYWORDS)

    def _detect_knowledge_query(self, query: str) -> bool:
        """
        检测是否为知识库查询意图

        判断条件：
        1. 明确提到知识库、文档、检索等关键词
        2. 属于专业性或概念性问题（什么是、如何、架构等）
        """
        import re

        query_lower = query.lower()

        # 检查关键词
        if any(keyword in query_lower for keyword in self.KNOWLEDGE_QUERY_KEYWORDS):
            return True

        # 检查模式匹配
        for pattern in self.KNOWLEDGE_QUERY_PATTERNS:
            if re.search(pattern, query_lower):
                return True

        return False

    def _check_answer_coverage(self, query: str, answer: str, processed_steps: List[str]) -> bool:
        """
        检查答案是否覆盖了查询的所有部分

        Args:
            query: 原始查询
            answer: LLM给出的答案
            processed_steps: 已处理的步骤（已调用的工具等）

        Returns:
            True 如果答案覆盖了所有意图，False 如果还有未处理的意图
        """
        # 如果不是多意图查询，直接返回True
        if not self._detect_multi_intent(query):
            return True

        # 简单检查：如果答案太短，可能没有覆盖所有意图
        # 这只是一个启发式方法，实际情况可能更复杂
        if len(answer) < 50 and "以及" in query:
            return False

        return True

    def _init_tools(self):
        """初始化工具"""
        register_builtin_tools(self.tool_engine)

    def _get_tools_description(self) -> str:
        """获取工具描述"""
        tools = self.tool_engine.list_tools()
        desc = []
        for tool in tools:
            params = ", ".join([f"{p.name}: {p.type}" for p in tool.parameters])
            tool_desc = f"- {tool.name}: {tool.description}\n  参数: {params}"
            desc.append(tool_desc)
        return "\n".join(desc)

    async def run(self, query: str, history: Optional[List[Dict]] = None) -> ReActResult:
        """
        运行 ReAct Agent

        Args:
            query: 用户查询
            history: 对话历史

        Returns:
            ReActResult: 执行结果
        """
        # 开始计时
        start_time = time.time()

        steps: List[ReActStep] = []
        messages = []

        # 性能指标
        llm_calls = 0
        tool_calls = 0
        tokens_used = 0

        # 检测是否为多意图查询
        is_multi_intent = self._detect_multi_intent(query)

        # 检测是否为知识库查询
        is_knowledge_query = self._detect_knowledge_query(query)

        # 添加系统提示词
        system_prompt = REACT_SYSTEM_PROMPT.format(
            tools_description=self._get_tools_description()
        )
        messages.append({"role": "system", "content": system_prompt})

        # 添加历史消息
        if history:
            for msg in history[-3:]:  # 只保留最近3条
                messages.append({"role": msg["role"], "content": msg["content"]})

        # 如果是知识库查询，先进行预检索获取上下文
        if is_knowledge_query:
            steps.append(ReActStep("thought", "检测到知识库查询意图，先检索相关知识"))
            try:
                tool_start = time.time()
                print(f"[DEBUG] Pre-fetching knowledge for: {query}")
                tool_result = await self.tool_engine.call(
                    tool_name="knowledge_search",
                    parameters={"query": query, "top_k": 5, "method": "hybrid"},
                    timeout=30
                )
                tool_calls += 1
                tool_duration = time.time() - tool_start

                observation = self._format_observation(tool_result)
                steps.append(ReActStep("observation", observation, data=tool_result))
                print(f"[DEBUG] Pre-fetch result: {observation[:200]}...")

                # 将检索结果注入到系统消息中作为上下文
                knowledge_context = (
                    f"[知识库预检索结果]\n"
                    f"以下是检索到的相关知识内容，请基于这些内容回答用户问题：\n\n"
                    f"{observation}\n\n"
                    f"如果检索结果不足以回答用户问题，可以继续使用其他工具获取信息。"
                )
                # 在系统提示词后插入知识库上下文
                messages.append({"role": "system", "content": knowledge_context})

            except Exception as e:
                error_msg = f"知识库预检索失败: {str(e)}"
                steps.append(ReActStep("error", error_msg))
                print(f"[DEBUG] Pre-fetch error: {error_msg}")
                # 预检索失败时继续正常流程，不中断

        # 添加当前查询
        messages.append({"role": "user", "content": query})
        steps.append(ReActStep("user", query))

        # 用于记录已处理的意图部分
        processed_actions = []

        # ReAct 循环
        for iteration in range(self.max_iterations):
            try:
                # 获取 LLM 响应（带 token 统计）
                llm_start = time.time()
                response = self.llm_client.chat_with_usage(messages=messages, temperature=0.1)
                llm_calls += 1
                tokens_used += response.tokens_used
                llm_duration = time.time() - llm_start

                # 调试：打印 LLM 原始响应和性能
                print(f"[DEBUG] Iteration {iteration + 1}, LLM Response:\n{response.content}\n{'='*50}")
                print(f"[DEBUG] LLM call: {llm_duration:.2f}s, tokens: {response.tokens_used}")

                # 解析响应
                thought, action, action_params, answer = self._parse_response(response.content)

                # 调试：打印解析结果
                print(f"[DEBUG] Parsed: thought={bool(thought)}, action={action}, answer={bool(answer)}")
                if answer:
                    print(f"[DEBUG] Answer content: {answer[:200]}...")

                # 记录思考
                if thought:
                    steps.append(ReActStep("thought", thought))
                    messages.append({"role": "assistant", "content": f"Thought: {thought}"})

                # 如果是最终答案
                if answer:
                    # 对于多意图查询，检查答案是否覆盖了所有部分
                    if is_multi_intent and not self._check_answer_coverage(query, answer, processed_actions):
                        # 答案不完整，继续循环
                        print(f"[DEBUG] Partial answer detected, continuing...")
                        steps.append(ReActStep("partial_answer", answer))
                        messages.append({
                            "role": "user",
                            "content": f"你只回答了问题的一部分。原始问题是：{query}\n\n你的答案：{answer}\n\n请继续处理问题的其他部分。"
                        })
                        continue

                    print(f"[DEBUG] Final answer received, returning...")
                    steps.append(ReActStep("answer", answer))

                    # 计算总耗时
                    duration = time.time() - start_time

                    return ReActResult(
                        answer=answer,
                        steps=steps,
                        success=True,
                        llm_calls=llm_calls,
                        tool_calls=tool_calls,
                        tokens_used=tokens_used,
                        duration=duration,
                        iterations=iteration + 1
                    )

                # 如果是工具调用
                if action:
                    steps.append(ReActStep("action", f"{action}: {json.dumps(action_params, ensure_ascii=False)}"))
                    processed_actions.append(action)  # 记录已执行的操作

                    # 执行工具
                    try:
                        tool_start = time.time()
                        print(f"[DEBUG] Calling tool: {action} with params: {action_params}")
                        tool_result = await self.tool_engine.call(
                            tool_name=action,
                            parameters=action_params,
                            timeout=30
                        )
                        tool_calls += 1
                        tool_duration = time.time() - tool_start

                        print(f"[DEBUG] Tool result type: {type(tool_result)}, result preview: {str(tool_result)[:500]}...")
                        print(f"[DEBUG] Tool call: {tool_duration:.2f}s")

                        # 格式化观察结果
                        observation = self._format_observation(tool_result)
                        steps.append(ReActStep("observation", observation, data=tool_result))
                        print(f"[DEBUG] Formatted observation: {observation[:500]}...")

                        # 将观察结果添加到对话（使用更清晰的格式）
                        messages.append({
                            "role": "assistant",
                            "content": f"**Action:** {action}\n```json\n{json.dumps(action_params, ensure_ascii=False)}\n```"
                        })
                        messages.append({
                            "role": "user",
                            "content": f"**Observation:**\n{observation}\n\n请基于以上观察结果继续思考，然后给出最终答案。"
                        })

                    except Exception as e:
                        error_msg = f"工具执行失败: {str(e)}"
                        steps.append(ReActStep("error", error_msg))
                        messages.append({
                            "role": "user",
                            "content": f"Error: {error_msg}\n\n请尝试其他方法或直接回答。"
                        })

            except Exception as e:
                # 计算总耗时
                duration = time.time() - start_time
                return ReActResult(
                    answer=f"处理过程中发生错误: {str(e)}",
                    steps=steps,
                    success=False,
                    error=str(e),
                    llm_calls=llm_calls,
                    tool_calls=tool_calls,
                    tokens_used=tokens_used,
                    duration=duration,
                    iterations=iteration + 1
                )

        # 计算总耗时
        duration = time.time() - start_time

        # 达到最大迭代次数
        return ReActResult(
            answer="抱歉，我无法在有限的步骤内完成这个任务。",
            steps=steps,
            success=False,
            error="达到最大迭代次数",
            llm_calls=llm_calls,
            tool_calls=tool_calls,
            tokens_used=tokens_used,
            duration=duration,
            iterations=self.max_iterations
        )

    def _parse_response(self, response: str) -> Tuple[Optional[str], Optional[str], Dict, Optional[str]]:
        """
        解析 LLM 响应

        Returns:
            (thought, action, action_params, answer)
        """
        thought = None
        action = None
        action_params = {}
        answer = None

        # 提取 Thought
        if "**Thought:**" in response or "Thought:" in response:
            thought_match = self._extract_section(response, ["**Thought:**", "Thought:", "思考："])
            if thought_match:
                thought = thought_match.strip()

        # 先提取 Action（优先执行 Action）
        if "**Action:**" in response or "Action:" in response or "行动：":
            # 先提取 action 名称
            action_section = self._extract_section(response, ["**Action:**", "Action:", "行动："])
            if action_section:
                action_section = action_section.strip()

                # 解析工具名称和参数
                lines = action_section.split('\n')
                if lines:
                    # 第一行是工具名
                    action = lines[0].strip()
                    # 剩余的是 JSON 参数
                    json_str = '\n'.join(lines[1:]).strip()

                    # 清理可能的 markdown 代码块标记
                    json_str = json_str.strip('`').strip()
                    if json_str.startswith('json'):
                        json_str = json_str[4:].strip()

                    try:
                        action_params = json.loads(json_str) if json_str else {}
                    except json.JSONDecodeError:
                        # 尝试从整个响应中提取 JSON
                        json_match = self._extract_json(response)
                        if json_match:
                            action_params = json_match
                        else:
                            action_params = {}

                # 如果有 Action，不返回 Answer（需要先执行）
                return thought, action, action_params, None

        # 只有在没有 Action 的情况下才提取 Answer
        if "**Answer:**" in response or "Answer:" in response or "答案：":
            answer_match = self._extract_section(response, ["**Answer:**", "Answer:", "答案："])
            if answer_match:
                answer = answer_match.strip()
                # 过滤掉"我会帮你查询"之类的中间回复
                # 只有当 Answer 内容足够长（超过50字符）且不包含明确的行动意向关键词时才认为是有效 Answer
                action_keywords = ["我会帮你查询", "让我帮你查询", "我需要查询", "我应该查询", "我必须查询",
                                  "我会使用", "让我使用", "我需要使用"]
                if (len(answer) > 50 and not any(keyword in answer for keyword in action_keywords)) or len(answer) > 100:
                    return thought, None, {}, answer

        return thought, action, action_params, answer

    def _extract_section(self, text: str, markers: List[str]) -> Optional[str]:
        """提取章节内容"""
        for marker in markers:
            if marker in text:
                idx = text.index(marker)
                content = text[idx + len(marker):].strip()

                # 对于 Answer，返回所有剩余内容（不截断）
                if marker in ["**Answer:**", "Answer:", "答案："]:
                    return content

                # 找到下一个标记的结束位置
                for next_marker in ["**", "\n\n", "Thought:", "Action:", "Answer:", "Observation:"]:
                    if next_marker in content and next_marker not in ["**Thought:**", "**Action:**", "**Answer:**"]:
                        end_idx = content.index(next_marker)
                        return content[:end_idx].strip()

                return content
        return None

    def _extract_json(self, text: str) -> Optional[Dict]:
        """从文本中提取 JSON"""
        # 尝试找到 { } 包裹的内容
        start = text.find('{')
        if start == -1:
            return None

        # 找匹配的 }
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    json_str = text[start:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass

        return None

    def _format_observation(self, result: Any) -> str:
        """格式化观察结果"""
        if isinstance(result, dict):
            # 如果有 results 字段（如 web_search、knowledge_search）
            if "results" in result:
                items = result["results"][:3]  # 只取前3个
                formatted = []

                for i, item in enumerate(items, 1):
                    # 检查是否是知识库检索结果（有 content 字段）
                    if "content" in item:
                        content = item.get("content", "")
                        score = item.get("score", 0)
                        source = item.get("source", "unknown")
                        # 限制内容长度
                        content_preview = content[:200] + "..." if len(content) > 200 else content
                        formatted.append(f"{i}. [相关度: {score:.2f}] {content_preview}\n   来源: {source}")
                    else:
                        # 网络搜索结果（有 title 和 snippet）
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')
                        formatted.append(f"{i}. {title}\n   {snippet}")

                return "\n".join(formatted) if formatted else "未找到相关结果"

            # 如果有 output 字段（如 code_execute）
            if "output" in result:
                return f"执行输出:\n{result['output']}"

            # 如果有 datetime 字段（如 get_current_time）
            if "datetime" in result:
                return f"当前时间: {result['datetime']}"

            # 其他情况，转换为 JSON
            return json.dumps(result, ensure_ascii=False, indent=2)

        return str(result)


# 全局实例
_global_agent: Optional[ReActAgent] = None


def get_react_agent() -> ReActAgent:
    """获取全局 ReAct Agent"""
    global _global_agent
    if _global_agent is None:
        _global_agent = ReActAgent()
    return _global_agent
