"""
数据层模块

提供数据访问接口，包括向量库、图数据库等
"""
from src.data.vector import VectorStore, get_vector_store
from src.data.graph import GraphStore, get_graph_store
from src.data.document import DocumentStore, get_document_store

__all__ = [
    "VectorStore",
    "get_vector_store",
    "GraphStore",
    "get_graph_store",
    "DocumentStore",
    "get_document_store",
]
