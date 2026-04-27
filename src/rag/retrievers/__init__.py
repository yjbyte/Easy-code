"""
检索模块

提供向量检索、图谱检索和混合检索功能。
"""
import asyncio
import time
from typing import List, Dict, Any, Optional

from src.rag.models import RetrievalResult, HybridRetrievalResult
from src.rag.config import get_rag_config
from src.rag.stores import get_vector_store, get_graph_store
from src.rag.embeddings import get_embedding_model


class VectorRetriever:
    """向量检索器"""

    def __init__(self):
        self.store = get_vector_store()
        self.embedding_model = get_embedding_model()
        self.config = get_rag_config()

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None,
    ) -> List[RetrievalResult]:
        """
        向量检索

        Args:
            query: 查询文本
            top_k: 返回数量
            filters: 过滤条件

        Returns:
            检索结果列表
        """
        # 生成查询向量
        query_vector = self.embedding_model.embed_single(query)
        print(f"[DEBUG VectorRetriever] Query: {query}, vector dimension: {len(query_vector)}")

        # 向量检索
        results = self.store.search(
            query_vector=query_vector,
            limit=top_k,
            score_threshold=None,  # 不设置阈值，先看所有结果
            filters=filters,
        )

        print(f"[DEBUG VectorRetriever] Found {len(results)} results, score_threshold config: {self.config.score_threshold}")
        for i, r in enumerate(results[:3]):
            print(f"[DEBUG VectorRetriever] Result {i+1}: score={r.score:.4f}, source={r.source}, content={r.content[:50]}...")

        # 如果设置了阈值且结果为空，打印警告
        if not results and self.config.score_threshold > 0:
            print(f"[WARN VectorRetriever] No results found with score_threshold={self.config.score_threshold}, trying without threshold...")
            results = self.store.search(
                query_vector=query_vector,
                limit=top_k,
                score_threshold=None,
                filters=filters,
            )
            print(f"[DEBUG VectorRetriever] Without threshold: {len(results)} results")

        return results


class GraphRetriever:
    """图谱检索器"""

    def __init__(self):
        self.store = get_graph_store()
        self.config = get_rag_config()

    async def retrieve(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """
        图谱检索

        Args:
            query: 查询文本
            entities: 实体列表
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        results = []

        # 如果提供了实体，进行实体邻居检索
        if entities:
            for entity in entities[:5]:  # 限制数量
                neighbors = self.store.get_entity_neighbors(
                    entity_name=entity,
                    depth=self.config.graph_depth,
                    limit=self.config.graph_max_nodes,
                )

                # 转换为检索结果
                for neighbor in neighbors:
                    results.append(
                        RetrievalResult(
                            content=f"实体: {neighbor}",
                            score=0.8,
                            source="knowledge_graph",
                            metadata={"type": "graph_neighbor"},
                        )
                    )

        # 如果没有提供实体，尝试从查询中提取关键词进行搜索
        if not entities:
            # 简单实现：使用查询词搜索实体
            keywords = self._extract_keywords(query)
            for keyword in keywords:
                entities = self.store.search_entities(
                    keyword=keyword,
                    limit=top_k,
                )

                for entity in entities:
                    results.append(
                        RetrievalResult(
                            content=f"实体: {entity.get('name')} ({entity.get('type')}) - {entity.get('description', '')}",
                            score=0.7,
                            source="knowledge_graph",
                            metadata=entity,
                        )
                    )

        return results[:top_k]

    def _extract_keywords(self, query: str) -> List[str]:
        """从查询中提取关键词"""
        # 简单实现：按空格分割，过滤停用词
        stopwords = {"的", "是", "在", "和", "与", "或", "什么", "怎么", "如何", "为什么"}
        words = query.split()
        return [w for w in words if len(w) > 1 and w not in stopwords]


class HybridRetriever:
    """混合检索器"""

    def __init__(self):
        self.vector_retriever = VectorRetriever()
        self.graph_retriever = GraphRetriever()
        self.config = get_rag_config()

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        alpha: Optional[float] = None,
    ) -> List[RetrievalResult]:
        """
        混合检索

        Args:
            query: 查询文本
            top_k: 返回数量
            alpha: 向量检索权重 (0-1)，默认使用配置值

        Returns:
            融合后的检索结果列表
        """
        start_time = time.time()

        # 使用配置的权重
        if alpha is None:
            alpha = self.config.hybrid_alpha

        print(f"[DEBUG HybridRetriever] Starting hybrid retrieval for query: '{query}', top_k: {top_k}, alpha: {alpha}")

        # 并行执行检索
        vector_results, graph_results = await asyncio.gather(
            self.vector_retriever.retrieve(query, top_k=top_k * 2),
            self.graph_retriever.retrieve(query, top_k=top_k * 2),
        )

        print(f"[DEBUG HybridRetriever] After parallel retrieval - vector: {len(vector_results)}, graph: {len(graph_results)}")

        # RRF 融合
        fused_results = self._reciprocal_rank_fusion(
            vector_results,
            graph_results,
            alpha=alpha,
            k=self.config.rrf_k,
        )

        duration = time.time() - start_time
        print(f"[DEBUG HybridRetriever] Hybrid retrieval completed in {duration:.2f}s, returning {len(fused_results[:top_k])} results")

        return fused_results[:top_k]

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[RetrievalResult],
        graph_results: List[RetrievalResult],
        k: int = 60,
        alpha: float = 0.7,
    ) -> List[RetrievalResult]:
        """
        RRF (Reciprocal Rank Fusion) 融合算法

        score(d) = sum(weight_i / (k + rank_i(d)))

        Args:
            vector_results: 向量检索结果列表
            graph_results: 图谱检索结果列表
            k: RRF 参数
            alpha: 向量检索权重

        Returns:
            融合后的结果列表
        """
        print(f"[DEBUG RRF] vector_results: {len(vector_results)}, graph_results: {len(graph_results)}, alpha: {alpha}, k: {k}")

        scores: Dict[str, Dict] = {}

        # 处理向量检索结果
        for rank, result in enumerate(vector_results, 1):
            # 使用内容作为唯一标识
            doc_id = result.chunk_id or result.content[:100]

            if doc_id not in scores:
                scores[doc_id] = {
                    "result": result,
                    "score": 0.0,
                }

            scores[doc_id]["score"] += alpha / (k + rank)

        # 处理图谱检索结果
        for rank, result in enumerate(graph_results, 1):
            doc_id = result.chunk_id or result.content[:100]

            if doc_id not in scores:
                scores[doc_id] = {
                    "result": result,
                    "score": 0.0,
                }

            scores[doc_id]["score"] += (1 - alpha) / (k + rank)

        print(f"[DEBUG RRF] After fusion: {len(scores)} unique documents")

        # 按融合分数排序
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        # 更新分数
        for item in sorted_results:
            item["result"].score = item["score"]

        print(f"[DEBUG RRF] Top 3 scores: {[round(r['score'], 4) for r in sorted_results[:3]]}")

        return [item["result"] for item in sorted_results]

    async def retrieve_with_details(
        self,
        query: str,
        top_k: int = 10,
        alpha: Optional[float] = None,
    ) -> HybridRetrievalResult:
        """
        混合检索（返回详细信息）

        Args:
            query: 查询文本
            top_k: 返回数量
            alpha: 向量检索权重

        Returns:
            混合检索结果（包含各分量的详细信息）
        """
        start_time = time.time()

        if alpha is None:
            alpha = self.config.hybrid_alpha

        # 并行执行检索
        vector_results, graph_results = await asyncio.gather(
            self.vector_retriever.retrieve(query, top_k=top_k * 2),
            self.graph_retriever.retrieve(query, top_k=top_k * 2),
        )

        # RRF 融合
        fused_results = self._reciprocal_rank_fusion(
            vector_results,
            graph_results,
            alpha=alpha,
            k=self.config.rrf_k,
        )

        duration = time.time() - start_time

        return HybridRetrievalResult(
            query=query,
            results=fused_results[:top_k],
            vector_results=vector_results,
            graph_results=graph_results,
            fused_scores=[r.score for r in fused_results[:top_k]],
            total=len(fused_results[:top_k]),
            duration=duration,
        )


class KnowledgeRetriever:
    """知识库检索器（对外的统一接口）"""

    def __init__(self):
        self.hybrid_retriever = HybridRetriever()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        method: str = "hybrid",
        **kwargs
    ) -> List[RetrievalResult]:
        """
        知识库检索

        Args:
            query: 查询文本
            top_k: 返回数量
            method: 检索方法 ("vector", "graph", "hybrid")
            **kwargs: 其他参数

        Returns:
            检索结果列表
        """
        if method == "vector":
            return await self.hybrid_retriever.vector_retriever.retrieve(
                query,
                top_k=top_k,
                filters=kwargs.get("filters"),
            )
        elif method == "graph":
            return await self.hybrid_retriever.graph_retriever.retrieve(
                query,
                entities=kwargs.get("entities"),
                top_k=top_k,
            )
        else:  # hybrid
            return await self.hybrid_retriever.retrieve(
                query,
                top_k=top_k,
                alpha=kwargs.get("alpha"),
            )


# 全局实例
_global_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    """获取混合检索器单例"""
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = HybridRetriever()
    return _global_retriever


def get_knowledge_retriever() -> KnowledgeRetriever:
    """获取知识库检索器单例"""
    return KnowledgeRetriever()


__all__ = [
    "VectorRetriever",
    "GraphRetriever",
    "HybridRetriever",
    "KnowledgeRetriever",
    "get_hybrid_retriever",
    "get_knowledge_retriever",
]
