"""
知识图谱存储模块

基于 Neo4j 实现知识图谱的存储和查询。
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from src.rag.models import Entity, Relation, EntityType, RelationType
from src.rag.config import get_rag_config


class Neo4jGraphStore:
    """Neo4j 图谱存储"""

    def __init__(self, config=None):
        self.config = config or get_rag_config()
        self.driver: Optional[GraphDatabase.driver] = None
        self._connect()

    def _connect(self):
        """连接 Neo4j"""
        if self.driver is None:
            self.driver = GraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password),
            )

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.driver = None

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            with self.driver.session(database=self.config.neo4j_database) as session:
                session.run("RETURN 1")
            return True
        except ServiceUnavailable:
            return False

    def create_entity(self, entity: Entity, source: str = "") -> str:
        """
        创建实体节点

        Args:
            entity: 实体对象
            source: 来源文档

        Returns:
            实体 ID
        """
        with self.driver.session(database=self.config.neo4j_database) as session:
            query = """
            MERGE (e:Entity {name: $name})
            ON CREATE SET
                e.type = $type,
                e.description = $description,
                e.created_at = datetime(),
                e.sources = [$source]
            ON MATCH SET
                e.description = COALESCE(e.description, $description),
                e.sources = CASE WHEN $source IN e.sources THEN e.sources ELSE e.sources + $source END,
                e.updated_at = datetime()
            RETURN e.name as id
            """
            result = session.run(
                query,
                name=entity.name,
                type=entity.type.value,
                description=entity.description or "",
                source=source,
            )
            record = result.single()
            return record["id"] if record else entity.name

    def create_entities_batch(
        self,
        entities: List[Entity],
        source: str = ""
    ) -> List[str]:
        """批量创建实体"""
        return [self.create_entity(e, source) for e in entities]

    def create_relation(self, relation: Relation) -> str:
        """
        创建关系

        Args:
            relation: 关系对象

        Returns:
            关系 ID
        """
        with self.driver.session(database=self.config.neo4j_database) as session:
            query = """
            MATCH (from_entity:Entity {name: $from_entity})
            MATCH (to_entity:Entity {name: $to_entity})
            MERGE (from_entity)-[r:RELATES {type: $rel_type}]->(to_entity)
            ON CREATE SET
                r.description = $description,
                r.weight = $weight,
                r.source = $source,
                r.created_at = datetime()
            ON MATCH SET
                r.weight = CASE WHEN r.weight < $weight THEN $weight ELSE r.weight END,
                r.updated_at = datetime()
            RETURN id(r) as id
            """
            result = session.run(
                query,
                from_entity=relation.from_entity,
                to_entity=relation.to_entity,
                rel_type=relation.relation_type.value,
                description=relation.description or "",
                weight=relation.weight,
                source=relation.source,
            )
            record = result.single()
            return str(record["id"]) if record else ""

    def create_relations_batch(
        self,
        relations: List[Relation]
    ) -> List[str]:
        """批量创建关系"""
        return [self.create_relation(r) for r in relations]

    def get_entity_neighbors(
        self,
        entity_name: str,
        depth: int = 1,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取实体的邻居节点

        Args:
            entity_name: 实体名称
            depth: 深度
            limit: 最大返回数量

        Returns:
            邻居节点列表
        """
        with self.driver.session(database=self.config.neo4j_database) as session:
            query = f"""
            MATCH (e:Entity {{name: $name}})
            CALL apoc.path.subgraphAll(e, {{
                maxLevel: $depth,
                relationshipFilter: "RELATES>",
                limit: $limit
            }})
            YIELD nodes, relationships
            RETURN nodes, relationships
            """

            try:
                result = session.run(
                    query,
                    name=entity_name,
                    depth=depth,
                    limit=limit,
                )
                return [dict(record) for record in result]
            except Exception:
                # 如果 apoc 不可用，使用标准 Cypher
                query = """
                MATCH (e:Entity {name: $name})
                MATCH (e)-[r:RELATES*1..{depth}]-(neighbor:Entity)
                RETURN DISTINCT neighbor, r
                LIMIT $limit
                """
                result = session.run(query, name=entity_name, limit=limit)
                return [dict(record) for record in result]

    def find_path(
        self,
        from_entity: str,
        to_entity: str,
        max_depth: int = 3
    ) -> List[Dict]:
        """
        查找两个实体之间的路径

        Args:
            from_entity: 起始实体
            to_entity: 目标实体
            max_depth: 最大深度

        Returns:
            路径列表
        """
        with self.driver.session(database=self.config.neo4j_database) as session:
            query = f"""
            MATCH (from:Entity {{name: $from}}), (to:Entity {{name: $to}})
            MATCH path = shortestPath((from)-[:RELATES*1..{max_depth}]-(to))
            RETURN path
            LIMIT 10
            """
            result = session.run(
                query,
                **{"from": from_entity, "to": to_entity}
            )
            return [dict(record) for record in result]

    def search_entities(
        self,
        keyword: str,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        搜索实体

        Args:
            keyword: 关键词
            entity_type: 实体类型过滤
            limit: 返回数量

        Returns:
            实体列表
        """
        with self.driver.session(database=self.config.neo4j_database) as session:
            if entity_type:
                query = """
                MATCH (e:Entity)
                WHERE e.name CONTAINS $keyword AND e.type = $type
                RETURN e.name as name, e.type as type, e.description as description
                LIMIT $limit
                """
                result = session.run(
                    query,
                    keyword=keyword,
                    type=entity_type,
                    limit=limit,
                )
            else:
                query = """
                MATCH (e:Entity)
                WHERE e.name CONTAINS $keyword
                RETURN e.name as name, e.type as type, e.description as description
                LIMIT $limit
                """
                result = session.run(
                    query,
                    keyword=keyword,
                    limit=limit,
                )

            return [dict(record) for record in result]

    def get_entity_relations(
        self,
        entity_name: str
    ) -> List[Dict]:
        """
        获取实体的所有关系

        Args:
            entity_name: 实体名称

        Returns:
            关系列表
        """
        with self.driver.session(database=self.config.neo4j_database) as session:
            query = """
            MATCH (e:Entity {name: $name})-[r:RELATES]-(other:Entity)
            RETURN
                e.name as from_entity,
                other.name as to_entity,
                r.type as relation_type,
                r.description as description,
                r.weight as weight
            """
            result = session.run(query, name=entity_name)
            return [dict(record) for record in result]

    def get_statistics(self) -> Dict:
        """获取图谱统计信息"""
        with self.driver.session(database=self.config.neo4j_database) as session:
            stats = {}

            # 节点数量
            result = session.run("MATCH (e:Entity) RETURN count(e) as count")
            stats["entity_count"] = result.single()["count"]

            # 关系数量
            result = session.run("MATCH ()-[r:RELATES]->() RETURN count(r) as count")
            stats["relation_count"] = result.single()["count"]

            # 实体类型分布
            result = session.run("""
                MATCH (e:Entity)
                RETURN e.type as type, count(e) as count
                ORDER BY count DESC
            """)
            stats["entity_types"] = [dict(r) for r in result]

            return stats

    def delete_entity(self, entity_name: str) -> bool:
        """删除实体"""
        with self.driver.session(database=self.config.neo4j_database) as session:
            query = "MATCH (e:Entity {name: $name}) DETACH DELETE e"
            session.run(query, name=entity_name)
            return True

    def clear_graph(self):
        """清空图谱"""
        with self.driver.session(database=self.config.neo4j_database) as session:
            session.run("MATCH (n) DETACH DELETE n")


# 全局实例
_global_graph_store: Optional[Neo4jGraphStore] = None


def get_graph_store() -> Neo4jGraphStore:
    """获取图谱存储单例"""
    global _global_graph_store
    if _global_graph_store is None:
        _global_graph_store = Neo4jGraphStore()
    return _global_graph_store
