"""
文档存储模块

提供文档管理接口
"""
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class DocumentStore(ABC):
    """文档存储基类"""

    @abstractmethod
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取文档"""
        pass

    @abstractmethod
    async def list_documents(
        self,
        filter: Dict[str, Any] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """列出文档"""
        pass

    @abstractmethod
    async def add_document(self, document: Dict[str, Any]) -> str:
        """添加文档"""
        pass


class MockDocumentStore(DocumentStore):
    """Mock 文档存储（用于开发测试）"""

    def __init__(self):
        self._documents: Dict[str, Dict[str, Any]] = {}

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Mock 获取"""
        return self._documents.get(doc_id)

    async def list_documents(
        self,
        filter: Dict[str, Any] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Mock 列出"""
        docs = list(self._documents.values())

        if filter:
            docs = [d for d in docs if all(
                d.get(k) == v for k, v in filter.items()
            )]

        return docs[:limit]

    async def add_document(self, document: Dict[str, Any]) -> str:
        """Mock 添加"""
        doc_id = document.get("id", f"doc_{len(self._documents)}")
        document["id"] = doc_id
        self._documents[doc_id] = document
        return doc_id


# 全局实例
_global_store: Optional[DocumentStore] = None


def get_document_store() -> DocumentStore:
    """获取全局文档存储"""
    global _global_store
    if _global_store is None:
        _global_store = MockDocumentStore()
    return _global_store


def set_document_store(store: DocumentStore) -> None:
    """设置文档存储"""
    global _global_store
    _global_store = store
