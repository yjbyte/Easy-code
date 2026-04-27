"""
图谱存储模块

提供知识图谱检索接口（作为工具使用）
"""
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class GraphStore(ABC):
    """图谱存储基类"""

    @abstractmethod
    async def query_entity(
        self,
        entity_name: str,
        relation_type: str = None
    ) -> Dict[str, Any]:
        """
        查询实体

        Args:
            entity_name: 实体名称
            relation_type: 关系类型

        Returns:
            实体信息
        """
        pass

    @abstractmethod
    async def traverse(
        self,
        start_nodes: List[str],
        max_depth: int = 2,
        relation_filter: List[str] = None
    ) -> Dict[str, Any]:
        """
        图谱遍历

        Args:
            start_nodes: 起始节点
            max_depth: 最大深度
            relation_filter: 关系过滤

        Returns:
            遍历结果
        """
        pass


class MockGraphStore(GraphStore):
    """Mock 图谱存储（用于开发测试）"""

    async def query_entity(
        self,
        entity_name: str,
        relation_type: str = None
    ) -> Dict[str, Any]:
        """Mock 查询"""
        return {
            "id": f"entity_{entity_name}",
            "name": entity_name,
            "type": "Entity",
            "description": f"实体 {entity_name} 的信息",
            "relations": [
                {"target": "相关实体A", "relation": "RELATED_TO", "weight": 0.8},
                {"target": "相关实体B", "relation": "DERIVED_FROM", "weight": 0.6}
            ]
        }

    async def traverse(
        self,
        start_nodes: List[str],
        max_depth: int = 2,
        relation_filter: List[str] = None
    ) -> Dict[str, Any]:
        """Mock 遍历"""
        return {
            "paths": [
                {
                    "nodes": [start_nodes[0], "中间节点", "目标节点"],
                    "relations": ["RELATED_TO", "BASED_ON"],
                    "depth": 2
                }
            ],
            "entities": {
                start_nodes[0]: {"name": start_nodes[0], "type": "Entity"},
                "中间节点": {"name": "中间节点", "type": "Concept"},
                "目标节点": {"name": "目标节点", "type": "Technology"}
            }
        }


# 全局实例
_global_store: Optional[GraphStore] = None


def get_graph_store() -> GraphStore:
    """获取全局图谱存储"""
    global _global_store
    if _global_store is None:
        _global_store = MockGraphStore()
    return _global_store


def set_graph_store(store: GraphStore) -> None:
    """设置图谱存储"""
    global _global_store
    _global_store = store
