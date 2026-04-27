"""
实体和关系抽取模块

基于 LLM 实现实体提取和关系抽取。
"""
import json
import re
from typing import List, Dict, Any, Optional

from src.rag.models import Entity, Relation, EntityType, RelationType
from src.utils.llm import get_glm_client


class EntityExtractor:
    """实体提取器"""

    def __init__(self):
        self.llm = get_glm_client()

    async def extract_entities(
        self,
        text: str,
        source: str = ""
    ) -> List[Entity]:
        """
        从文本中提取实体

        Args:
            text: 输入文本
            source: 来源标识

        Returns:
            实体列表
        """
        prompt = self._build_extraction_prompt(text)

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )

            entities = self._parse_entities(response)
            return entities

        except Exception as e:
            print(f"Entity extraction error: {e}")
            return []

    def _build_extraction_prompt(self, text: str) -> str:
        """构建提取提示词"""
        return f"""请从以下文本中提取重要的实体。

实体类型包括：
- person: 人物
- organization: 组织/公司
- technology: 技术
- product: 产品
- framework: 框架/库
- language: 编程语言
- concept: 概念
- method: 方法
- date: 日期
- location: 地点

只提取明确提及的实体，不要过度推断。如果没有某个类型的实体，则不返回该类型。

文本：
{text}

请以 JSON 格式返回，格式如下：
{{
    "entities": [
        {{"name": "实体名称", "type": "实体类型", "description": "简短描述"}}
    ]
}}

注意：只返回 JSON，不要添加其他说明文字。"""

    def _parse_entities(self, response: str) -> List[Entity]:
        """解析 LLM 返回的实体"""
        entities = []

        try:
            # 尝试直接解析 JSON
            data = json.loads(response)
            entity_list = data.get("entities", [])
        except json.JSONDecodeError:
            # 尝试从响应中提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    entity_list = data.get("entities", [])
                except json.JSONDecodeError:
                    return []
            else:
                return []

        for item in entity_list:
            try:
                entity_type = self._parse_entity_type(item.get("type", "concept"))
                entity = Entity(
                    name=item["name"],
                    type=entity_type,
                    description=item.get("description", ""),
                )
                entities.append(entity)
            except (KeyError, ValueError) as e:
                print(f"Error parsing entity: {e}")
                continue

        return entities

    def _parse_entity_type(self, type_str: str) -> EntityType:
        """解析实体类型"""
        type_map = {
            "person": EntityType.PERSON,
            "organization": EntityType.ORGANIZATION,
            "technology": EntityType.TECHNOLOGY,
            "product": EntityType.PRODUCT,
            "framework": EntityType.FRAMEWORK,
            "language": EntityType.LANGUAGE,
            "concept": EntityType.CONCEPT,
            "theory": EntityType.THEORY,
            "method": EntityType.METHOD,
            "date": EntityType.DATE,
            "location": EntityType.LOCATION,
            "event": EntityType.EVENT,
            "document": EntityType.DOCUMENT,
        }

        type_lower = type_str.lower()
        return type_map.get(type_lower, EntityType.CONCEPT)


class RelationExtractor:
    """关系抽取器"""

    def __init__(self):
        self.llm = get_glm_client()

    async def extract_relations(
        self,
        text: str,
        entities: List[Entity],
        source: str = ""
    ) -> List[Relation]:
        """
        从文本中抽取实体间的关系

        Args:
            text: 输入文本
            entities: 已提取的实体列表
            source: 来源标识

        Returns:
            关系列表
        """
        if len(entities) < 2:
            return []

        prompt = self._build_extraction_prompt(text, entities)

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )

            relations = self._parse_relations(response, source)
            return relations

        except Exception as e:
            print(f"Relation extraction error: {e}")
            return []

    def _build_extraction_prompt(
        self,
        text: str,
        entities: List[Entity]
    ) -> str:
        """构建提取提示词"""
        entity_list = "\n".join([
            f"- {e.name} ({e.type.value})"
            for e in entities
        ])

        relation_types = """
- is_a: 是一种（上下位关系，如：Python is_a 编程语言）
- part_of: 属于（部分关系，如：轮子 part_of 汽车）
- uses: 使用（如：程序 uses 库）
- implements: 实现（如：类 implements 接口）
- depends_on: 依赖（如：A depends_on B）
- related_to: 相关（通用相关关系）
- causes: 导致（因果关系）
- located_in: 位于（位置关系）
- created_by: 创建于（如：软件 created_by 公司）
- defined_as: 定义为（定义关系）
"""

        return f"""请从以下文本中，分析实体之间的关系。

实体列表：
{entity_list}

关系类型：
{relation_types}

文本：
{text}

请识别实体间的关系，只返回明确存在的关系。如果没有关系，则返回空列表。

请以 JSON 格式返回，格式如下：
{{
    "relations": [
        {{"from": "实体1", "to": "实体2", "type": "关系类型", "description": "关系描述"}}
    ]
}}

注意：只返回 JSON，不要添加其他说明文字。"""

    def _parse_relations(
        self,
        response: str,
        source: str
    ) -> List[Relation]:
        """解析 LLM 返回的关系"""
        relations = []

        try:
            # 尝试直接解析 JSON
            data = json.loads(response)
            relation_list = data.get("relations", [])
        except json.JSONDecodeError:
            # 尝试从响应中提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    relation_list = data.get("relations", [])
                except json.JSONDecodeError:
                    return []
            else:
                return []

        for item in relation_list:
            try:
                relation_type = self._parse_relation_type(
                    item.get("type", "related_to")
                )
                relation = Relation(
                    from_entity=item["from"],
                    to_entity=item["to"],
                    relation_type=relation_type,
                    description=item.get("description", ""),
                    source=source,
                )
                relations.append(relation)
            except (KeyError, ValueError) as e:
                print(f"Error parsing relation: {e}")
                continue

        return relations

    def _parse_relation_type(self, type_str: str) -> RelationType:
        """解析关系类型"""
        type_map = {
            "is_a": RelationType.IS_A,
            "part_of": RelationType.PART_OF,
            "uses": RelationType.USES,
            "implements": RelationType.IMPLEMENTS,
            "depends_on": RelationType.DEPENDS_ON,
            "related_to": RelationType.RELATED_TO,
            "causes": RelationType.CAUSES,
            "caused_by": RelationType.CAUSED_BY,
            "located_in": RelationType.LOCATED_IN,
            "created_by": RelationType.CREATED_BY,
            "defined_as": RelationType.DEFINED_AS,
            "example_of": RelationType.EXAMPLE_OF,
        }

        type_lower = type_str.lower().replace("-", "_")
        return type_map.get(type_lower, RelationType.RELATED_TO)


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()

    async def build_from_chunks(
        self,
        chunks: List[str],
        source: str = ""
    ) -> tuple[List[Entity], List[Relation]]:
        """
        从分片列表构建知识图谱

        Args:
            chunks: 文本分片列表
            source: 来源标识

        Returns:
            (实体列表, 关系列表)
        """
        all_entities: Dict[str, Entity] = {}
        all_relations: List[Relation] = []

        for chunk in chunks:
            # 提取实体
            entities = await self.entity_extractor.extract_entities(chunk, source)

            # 合并实体（去重）
            for entity in entities:
                key = f"{entity.name}_{entity.type.value}"
                if key not in all_entities:
                    all_entities[key] = entity

            # 提取关系
            entity_list = list(all_entities.values())
            relations = await self.relation_extractor.extract_relations(
                chunk,
                entity_list,
                source
            )

            # 添加关系
            all_relations.extend(relations)

        return list(all_entities.values()), all_relations

    async def build_from_text(
        self,
        text: str,
        source: str = ""
    ) -> tuple[List[Entity], List[Relation]]:
        """
        从文本构建知识图谱

        Args:
            text: 输入文本
            source: 来源标识

        Returns:
            (实体列表, 关系列表)
        """
        return await self.build_from_chunks([text], source)


# 全局实例
_global_builder: Optional[KnowledgeGraphBuilder] = None


def get_graph_builder() -> KnowledgeGraphBuilder:
    """获取图谱构建器单例"""
    global _global_builder
    if _global_builder is None:
        _global_builder = KnowledgeGraphBuilder()
    return _global_builder
