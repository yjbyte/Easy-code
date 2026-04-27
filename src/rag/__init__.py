"""
RAG 模块 - 检索增强生成

提供文档摄入、向量化存储、知识图谱构建和混合检索功能。
"""
from src.rag.models import (
    Document,
    Chunk,
    Entity,
    Relation,
    RetrievalResult,
)

from src.rag.embeddings import get_embedding_model
from src.rag.parsers import get_parser
from src.rag.chunkers import get_chunker
from src.rag.stores import get_vector_store, get_graph_store
from src.rag.retrievers import get_hybrid_retriever

__all__ = [
    # Models
    "Document",
    "Chunk",
    "Entity",
    "Relation",
    "RetrievalResult",
    # Factories
    "get_embedding_model",
    "get_parser",
    "get_chunker",
    "get_vector_store",
    "get_graph_store",
    "get_hybrid_retriever",
]
