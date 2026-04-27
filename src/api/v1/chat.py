"""
聊天接口 - 基于 ReAct 范式的智能对话
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from src.agent import get_react_agent

router = APIRouter()


class Message(BaseModel):
    """消息"""
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    history: Optional[List[Message]] = Field(default=None, description="历史消息")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词（保留兼容）")


class StepInfo(BaseModel):
    """ReAct 步骤信息"""
    step_type: str = Field(..., description="步骤类型: thought/action/observation/answer")
    content: str = Field(..., description="步骤内容")


class IntentInfo(BaseModel):
    """意图信息（兼容前端）"""
    query_type: str = Field(default="unknown", description="查询类型")
    entities: List[str] = Field(default_factory=list, description="提取的实体")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    complexity: str = Field(default="medium", description="复杂度")
    requires: List[str] = Field(default_factory=list, description="所需能力")
    preferred_tools: List[str] = Field(default_factory=list, description="推荐工具")
    confidence: float = Field(default=0.8, description="置信度")
    reasoning: Optional[str] = Field(default=None, description="分析推理")
    suggested_strategy: Optional[str] = Field(default=None, description="建议策略")


class PerformanceMetrics(BaseModel):
    """性能指标"""
    llm_calls: int = Field(default=0, description="LLM 调用次数")
    tool_calls: int = Field(default=0, description="工具调用次数")
    tokens_used: int = Field(default=0, description="消耗的 token 数")
    duration: Optional[float] = Field(default=None, description="总耗时（秒）")
    iterations: int = Field(default=0, description="迭代次数")


class ChatResponse(BaseModel):
    """聊天响应"""
    message: str = Field(..., description="助手回复")
    intent: Optional[IntentInfo] = Field(default=None, description="意图分析结果（兼容前端）")
    steps: Optional[List[StepInfo]] = Field(default=None, description="ReAct推理步骤")
    metrics: Optional[PerformanceMetrics] = Field(default=None, description="性能指标")
    success: bool = Field(default=True, description="是否成功")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天对话接口 - 基于 ReAct 范式

    工作流程：
    1. LLM 分析问题，思考需要什么信息 (Thought)
    2. 决定是否需要调用工具 (Action)
    3. 获取工具执行结果 (Observation)
    4. 基于结果生成最终答案 (Answer)

    示例:
    ```json
    {
        "message": "你底层使用的什么LLM名字，以及无锡市今天的天气",
        "history": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮你的？"}
        ]
    }
    ```
    """
    try:
        # 获取 ReAct Agent
        agent = get_react_agent()

        # 转换历史消息格式
        history = None
        if request.history:
            history = [{"role": msg.role, "content": msg.content} for msg in request.history]

        # 运行 ReAct Agent
        result = await agent.run(request.message, history=history)

        # 转换步骤信息
        steps_info = []
        intent_info = None

        if result.steps:
            # 分析步骤，生成意图信息（兼容前端）
            query_type = "open_ended"
            complexity = "medium"
            requires = []
            keywords = []
            reasoning = None

            for step in result.steps:
                # 添加步骤信息
                steps_info.append(
                    StepInfo(step_type=step.step_type, content=step.content)
                )

                # 分析意图（从thought步骤中提取）
                if step.step_type == "thought" and step.content:
                    reasoning = step.content

                    # 检测查询类型
                    if "系统" in step.content or "LLM" in step.content or "模型" in step.content:
                        query_type = "system"
                    elif "实时" in step.content or "天气" in step.content or "搜索" in step.content:
                        query_type = "realtime"
                        requires.append("realtime_data")
                    elif "知识" in step.content or "检索" in step.content:
                        query_type = "fact"
                        requires.append("vector_search")

                    # 提取关键词
                    if "web_search" in step.content:
                        requires.append("realtime_data")
                        keywords.append("web_search")

            # 生成意图信息
            intent_info = IntentInfo(
                query_type=query_type,
                keywords=keywords if keywords else ["react_agent"],
                complexity=complexity,
                requires=list(set(requires)) if requires else [],
                confidence=0.9,
                reasoning=reasoning,
                suggested_strategy="react"
            )

        return ChatResponse(
            message=result.answer,
            intent=intent_info,
            steps=steps_info if steps_info else None,
            metrics=PerformanceMetrics(
                llm_calls=result.llm_calls,
                tool_calls=result.tool_calls,
                tokens_used=result.tokens_used,
                duration=result.duration,
                iterations=result.iterations
            ),
            success=result.success
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天（TODO）

    返回 Server-Sent Events 流式响应
    """
    raise HTTPException(status_code=501, detail="流式接口待实现")
