"""
向量存储模块

提供向量检索接口（作为工具使用）
"""
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class VectorStore(ABC):
    """向量存储基类"""

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        向量检索

        Args:
            query: 查询文本
            top_k: 返回数量
            filter: 过滤条件

        Returns:
            检索结果列表
        """
        pass

    @abstractmethod
    async def add_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        添加文档

        Args:
            documents: 文档列表

        Returns:
            文档 ID 列表
        """
        pass


class MockVectorStore(VectorStore):
    """Mock 向量存储（用于开发测试）"""

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Mock 检索"""
        return [
            {
                "id": "doc_1",
                "content": f"关于 {query} 的相关内容...",
                "score": 0.9,
                "metadata": {}
            }
        ]

    async def add_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """Mock 添加"""
        return [f"doc_{i}" for i in range(len(documents))]


# 全局实例
_global_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取全局向量存储"""
    global _global_store
    if _global_store is None:
        _global_store = MockVectorStore()
    return _global_store


def set_vector_store(store: VectorStore) -> None:
    """设置向量存储"""
    global _global_store
    _global_store = store
