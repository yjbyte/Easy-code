"""
上下文管理模块

处理上下文窗口、消息历史管理
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ContextWindow:
    """上下文窗口配置"""
    max_tokens: int = 16000
    preserve_recent: int = 10
    tool_output_limit: int = 5000
    enable_compression: bool = True


@dataclass
class Message:
    """消息"""
    role: str  # user/assistant/system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    compressed: bool = False


class ContextManager:
    """
    上下文管理器

    负责管理对话历史、上下文压缩、窗口控制
    """

    def __init__(self, config: Optional[ContextWindow] = None):
        self.config = config or ContextWindow()
        self._messages: List[Message] = []
        self._token_count = 0

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """添加消息"""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self._messages.append(message)
        self._update_token_count()

    def get_messages(
        self,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        获取消息列表（用于发送给 LLM）

        Args:
            max_tokens: 最大 token 数

        Returns:
            消息字典列表
        """
        limit = max_tokens or self.config.max_tokens

        # 必须保留最近 N 条消息
        preserve_count = self.config.preserve_recent
        recent_messages = self._messages[-preserve_count:] if len(self._messages) > preserve_count else self._messages[:]

        # 计算最近消息的 token 数
        recent_tokens = sum(self._estimate_tokens(msg.content) for msg in recent_messages)

        # 如果最近消息就超了，压缩工具输出
        if recent_tokens > limit:
            return self._compress_messages(recent_messages, limit)

        # 如果还有空间，添加更早的消息
        available_tokens = limit - recent_tokens
        older_messages = self._messages[:-preserve_count] or []

        result = []
        for msg in reversed(older_messages):
            msg_tokens = self._estimate_tokens(msg.content)

            if msg_tokens <= available_tokens:
                result.insert(0, {
                    "role": msg.role,
                    "content": msg.content
                })
                available_tokens -= msg_tokens
            else:
                break

        # 添加最近消息
        result.extend([{"role": m.role, "content": m.content} for m in recent_messages])

        return result

    def _compress_messages(
        self,
        messages: List[Message],
        limit: int
    ) -> List[Dict[str, str]]:
        """压缩消息"""
        result = []
        current_tokens = 0

        for msg in reversed(messages):
            # 如果是工具输出，截断
            if msg.role == "user" and "Observation:" in msg.content:
                compressed_content = self._truncate_tool_output(
                    msg.content,
                    self.config.tool_output_limit
                )
            else:
                compressed_content = msg.content

            msg_tokens = self._estimate_tokens(compressed_content)

            if current_tokens + msg_tokens <= limit:
                result.insert(0, {
                    "role": msg.role,
                    "content": compressed_content
                })
                current_tokens += msg_tokens
            else:
                # 空间不足，丢弃更早的消息
                break

        return result

    def _truncate_tool_output(self, content: str, limit: int) -> str:
        """截断工具输出"""
        if len(content) <= limit:
            return content

        # 保留开头和结尾
        head = limit // 2
        tail = limit - head - 20

        return (
            content[:head] +
            "\n\n... (内容过长，已截断) ...\n\n" +
            content[-tail:]
        )

    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数（简单方法：字符数 / 2）"""
        return len(text) // 2

    def _update_token_count(self) -> None:
        """更新 token 计数"""
        self._token_count = sum(
            self._estimate_tokens(msg.content)
            for msg in self._messages
        )

    def clear(self) -> None:
        """清空消息历史"""
        self._messages.clear()
        self._token_count = 0

    def get_message_count(self) -> int:
        """获取消息数量"""
        return len(self._messages)

    def get_token_count(self) -> int:
        """获取当前 token 数"""
        return self._token_count

    def get_history_summary(self) -> str:
        """获取历史摘要（用于压缩时）"""
        if not self._messages:
            return "无历史对话"

        summary_parts = []

        for i, msg in enumerate(self._messages[-10:], 1):
            role = "用户" if msg.role == "user" else "助手"
            content = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            summary_parts.append(f"{i}. {role}: {content}")

        return "\n".join(summary_parts)


# 全局实例
_global_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """获取全局上下文管理器"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ContextManager()
    return _global_manager
