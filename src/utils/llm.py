"""
GLM-4 LLM 客户端
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from zhipuai import ZhipuAI
from src.config.settings import settings


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class GLMClient:
    """智谱 GLM 客户端"""

    def __init__(self):
        self.client = ZhipuAI(
            api_key=settings.zhipuai_api_key,
            base_url=settings.zhipuai_base_url
        )
        self.model = settings.zhipuai_model

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        发起聊天对话（兼容旧接口）

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            模型回复文本
        """
        response = self._chat_with_usage(messages, temperature, max_tokens)
        return response.content

    def chat_with_usage(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        发起聊天对话（带 token 使用信息）

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            LLMResponse: 包含内容和 token 使用信息
        """
        return self._chat_with_usage(messages, temperature, max_tokens)

    def _chat_with_usage(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """内部方法：执行聊天并返回使用信息"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 提取 token 使用信息
        usage = response.usage
        tokens_used = usage.total_tokens if usage else 0
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        return LLMResponse(
            content=response.choices[0].message.content,
            tokens_used=tokens_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

    def chat_simple(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """
        简单对话（单轮）

        Args:
            user_message: 用户消息
            system_prompt: 系统提示词（可选）

        Returns:
            模型回复
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        return self.chat(messages)


# 全局单例
_glm_client: Optional[GLMClient] = None


def get_glm_client() -> GLMClient:
    """获取 GLM 客户端单例"""
    global _glm_client
    if _glm_client is None:
        _glm_client = GLMClient()
    return _glm_client
