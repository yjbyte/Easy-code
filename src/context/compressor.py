"""
上下文压缩模块

实现各种上下文压缩策略
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CompressionResult:
    """压缩结果"""
    compressed_content: str
    original_length: int
    compressed_length: int
    compression_ratio: float
    method: str


class ContextCompressor:
    """
    上下文压缩器

    提供多种压缩策略：
    1. 工具输出截断
    2. 多个 Observation 合并
    3. 历史消息摘要
    """

    def __init__(self):
        pass

    def compress_tool_output(
        self,
        content: str,
        limit: int = 5000
    ) -> CompressionResult:
        """
        压缩工具输出

        Args:
            content: 工具输出内容
            limit: 最大长度

        Returns:
            CompressionResult: 压缩结果
        """
        original_length = len(content)

        if original_length <= limit:
            return CompressionResult(
                compressed_content=content,
                original_length=original_length,
                compressed_length=original_length,
                compression_ratio=1.0,
                method="none"
            )

        # 保留开头和结尾
        head_size = limit // 2
        tail_size = limit - head_size - 30

        compressed = (
            content[:head_size] +
            "\n\n... (内容过长，已截断，省略 " +
            str(original_length - limit) +
            " 字符) ...\n\n" +
            content[-tail_size:]
        )

        return CompressionResult(
            compressed_content=compressed,
            original_length=original_length,
            compressed_length=len(compressed),
            compression_ratio=len(compressed) / original_length,
            method="truncate"
        )

    def merge_observations(
        self,
        observations: List[str]
    ) -> CompressionResult:
        """
        合并多个 Observation

        Args:
            observations: Observation 列表

        Returns:
            CompressionResult: 压缩结果
        """
        original_length = sum(len(obs) for obs in observations)

        if len(observations) <= 1:
            return CompressionResult(
                compressed_content=observations[0] if observations else "",
                original_length=original_length,
                compressed_length=original_length,
                compression_ratio=1.0,
                method="none"
            )

        # 合并为一个列表
        merged = "工具执行结果：\n\n"
        for i, obs in enumerate(observations, 1):
            # 每个 Observation 限制在 500 字符
            if len(obs) > 500:
                obs = obs[:250] + "\n\n... (截断) ...\n\n" + obs[-240:]
            merged += f"{i}. {obs}\n\n"

        return CompressionResult(
            compressed_content=merged,
            original_length=original_length,
            compressed_length=len(merged),
            compression_ratio=len(merged) / original_length if original_length > 0 else 1.0,
            method="merge"
        )

    def summarize_history(
        self,
        messages: List[Dict[str, str]],
        preserve_recent: int = 3
    ) -> CompressionResult:
        """
        摘要历史消息

        Args:
            messages: 消息列表
            preserve_recent: 保留最近多少条不压缩

        Returns:
            CompressionResult: 压缩结果
        """
        if len(messages) <= preserve_recent:
            return CompressionResult(
                compressed_content=str(messages),
                original_length=len(str(messages)),
                compressed_length=len(str(messages)),
                compression_ratio=1.0,
                method="none"
            )

        # 保留最近的消息
        recent = messages[-preserve_recent:]

        # 摘要更早的消息
        older = messages[:-preserve_recent]

        summary_parts = []
        for msg in older:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:100]
            if len(msg["content"]) > 100:
                content += "..."
            summary_parts.append(f"{role}: {content}")

        summary = "历史对话摘要：\n" + "\n".join(summary_parts)

        # 合并结果
        result = {
            "summary": summary,
            "recent_messages": recent
        }

        return CompressionResult(
            compressed_content=str(result),
            original_length=len(str(messages)),
            compressed_length=len(str(result)),
            compression_ratio=len(str(result)) / len(str(messages)),
            method="summary"
        )

    def compress_observation_text(self, text: str) -> str:
        """
        压缩 Observation 文本（内部方法）

        Args:
            text: Observation 文本

        Returns:
            压缩后的文本
        """
        # 如果包含搜索结果，只保留前 3 个
        if "**Observation:**" in text:
            lines = text.split('\n')
            result_lines = []
            count = 0
            max_results = 3

            for line in lines:
                if line.strip().startswith(f"{max_results + 1}."):
                    # 达到限制，添加省略标记
                    result_lines.append("... (后续结果已省略) ...")
                    break
                result_lines.append(line)
                if line.strip().endswith(('。', '.', '.')) and count < max_results:
                    count += 1

            return '\n'.join(result_lines)

        return text


# 全局实例
_global_compressor: Optional[ContextCompressor] = None


def get_context_compressor() -> ContextCompressor:
    """获取全局上下文压缩器"""
    global _global_compressor
    if _global_compressor is None:
        _global_compressor = ContextCompressor()
    return _global_compressor
