"""
存储模块

提供向量存储和图谱存储。
"""
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient, models

from src.rag.config import get_rag_config
from src.rag.models import Chunk, RetrievalResult
# 导出图谱存储
from src.rag.stores.graph import Neo4jGraphStore, get_graph_store


class QdrantVectorStore:
    """Qdrant 向量存储"""

    def __init__(self, config=None):
        self.config = config or get_rag_config()
        self.client: Optional[QdrantClient] = None
        self._connect()

    def _connect(self):
        """连接 Qdrant"""
        if self.client is None:
            self.client = QdrantClient(
                url=self.config.qdrant_url,
                api_key=self.config.qdrant_api_key,
            )

    def ensure_collection(self):
        """确保 Collection 存在"""
        # 检查是否存在
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.config.qdrant_collection not in collection_names:
            print(f"[DEBUG Qdrant] Creating collection '{self.config.qdrant_collection}'...")
            # 创建 Collection
            self.client.create_collection(
                collection_name=self.config.qdrant_collection,
                vectors_config=models.VectorParams(
                    size=self.config.qdrant_vector_size,
                    distance=models.Distance.COSINE,
                )
            )
            print(f"[DEBUG Qdrant] Collection created successfully")

            # 创建索引（可选，提升查询性能）
            try:
                # 使用新的 PayloadSchemaType
                from qdrant_client.models import PayloadSchemaType

                indices_to_create = [
                    ("doc_id", PayloadSchemaType.KEYWORD),
                    ("source", PayloadSchemaType.KEYWORD),
                    ("created_at", PayloadSchemaType.INTEGER),
                ]

                for field_name, field_type in indices_to_create:
                    try:
                        self.client.create_payload_index(
                            collection_name=self.config.qdrant_collection,
                            field_name=field_name,
                            field_schema=field_type,
                        )
                        print(f"[DEBUG Qdrant] Payload index created for field: {field_name}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            print(f"[DEBUG Qdrant] Index for {field_name} already exists")
                        else:
                            print(f"[DEBUG Qdrant] Warning creating index for {field_name}: {e}")
            except ImportError:
                # PayloadSchemaType 不可用，跳过索引创建
                print(f"[DEBUG Qdrant] PayloadSchemaType not available, skipping index creation")
        else:
            print(f"[DEBUG Qdrant] Collection '{self.config.qdrant_collection}' already exists")

    def insert_chunks(
        self,
        chunks: List[Chunk],
        embeddings: Optional[List[List[float]]] = None
    ) -> List[str]:
        """
        插入分片

        Args:
            chunks: 分片列表
            embeddings: 向量列表（如果为 None，需要先生成）

        Returns:
            分片 ID 列表
        """
        self.ensure_collection()

        from src.rag.embeddings import get_embedding_model

        if embeddings is None:
            embedding_model = get_embedding_model()
            embeddings = embedding_model.embed([c.content for c in chunks])

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            point = models.PointStruct(
                id=chunk.chunk_id,
                vector=embedding,
                payload={
                    "content": chunk.content,
                    "doc_id": chunk.doc_id,
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "entities": chunk.entities,
                    "created_at": int(chunk.created_at.timestamp()),
                    **chunk.metadata,
                },
            )
            points.append(point)

        self.client.upsert(
            collection_name=self.config.qdrant_collection,
            points=points,
        )

        return [chunk.chunk_id for chunk in chunks]

    def insert_batch(
        self,
        chunks: List[Chunk],
        embeddings: List[List[float]]
    ) -> List[str]:
        """批量插入分片"""
        return self.insert_chunks(chunks, embeddings)

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        向量检索

        Args:
            query_vector: 查询向量
            limit: 返回数量
            score_threshold: 分数阈值
            filters: 过滤条件

        Returns:
            检索结果列表
        """
        self.ensure_collection()

        # 获取集合信息用于调试
        try:
            collection_info = self.client.get_collection(self.config.qdrant_collection)
            points_count = collection_info.points_count or 0
            print(f"[DEBUG Qdrant] Collection '{self.config.qdrant_collection}' has {points_count} points")
        except Exception as e:
            print(f"[DEBUG Qdrant] Error getting collection info: {e}")

        # 构建过滤条件
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                )
            if conditions:
                query_filter = models.Filter(must=conditions)

        print(f"[DEBUG Qdrant] Searching with params: limit={limit}, score_threshold={score_threshold}, filters={filters}")

        # 直接使用 query_points 方法（Qdrant 1.10+）
        # 直接传递向量列表，更兼容
        response = self.client.query_points(
            collection_name=self.config.qdrant_collection,
            query=query_vector,  # 直接使用向量列表
            limit=limit,
            with_payload=True,
            query_filter=query_filter,
            score_threshold=score_threshold,
        )
        results = response.points

        print(f"[DEBUG Qdrant] Search returned {len(results)} results")
        for i, r in enumerate(results[:3]):
            print(f"[DEBUG Qdrant] Result {i+1}: id={r.id}, score={r.score:.4f}, source={r.payload.get('source', 'N/A')}")

        return [
            RetrievalResult(
                content=r.payload.get("content", ""),
                score=r.score,
                source=r.payload.get("source", ""),
                chunk_id=str(r.id),
                metadata=r.payload,
            )
            for r in results
        ]

    def delete_by_doc(self, doc_id: str) -> int:
        """
        删除文档的所有分片

        Args:
            doc_id: 文档 ID

        Returns:
            删除的数量
        """
        self.client.delete(
            collection_name=self.config.qdrant_collection,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="doc_id",
                        match=models.MatchValue(value=doc_id),
                    )
                ]
            ),
        )
        # 返回删除数量（需要通过 count 查询）
        return 0

    def get_chunk(self, chunk_id: str) -> Optional[Dict]:
        """
        获取分片详情

        Args:
            chunk_id: 分片 ID

        Returns:
            分片数据
        """
        results = self.client.retrieve(
            collection_name=self.config.qdrant_collection,
            ids=[chunk_id],
            with_payload=True,
        )

        if results:
            r = results[0]
            return {
                "chunk_id": r.id,
                "content": r.payload.get("content", ""),
                "doc_id": r.payload.get("doc_id", ""),
                "source": r.payload.get("source", ""),
                "metadata": r.payload,
            }
        return None

    def count_docs(self) -> int:
        """获取文档总数"""
        collection_info = self.client.get_collection(
            self.config.qdrant_collection
        )
        return collection_info.points_count or 0

    def clear_collection(self):
        """清空 Collection"""
        self.client.delete_collection(
            collection_name=self.config.qdrant_collection
        )
        self.ensure_collection()

    def delete_collection(self):
        """删除 Collection"""
        self.client.delete_collection(
            collection_name=self.config.qdrant_collection
        )


# 全局实例
_global_store: Optional[QdrantVectorStore] = None


def get_vector_store() -> QdrantVectorStore:
    """获取向量存储单例"""
    global _global_store
    if _global_store is None:
        _global_store = QdrantVectorStore()
    return _global_store


__all__ = [
    "QdrantVectorStore",
    "Neo4jGraphStore",
    "get_vector_store",
    "get_graph_store",
]
