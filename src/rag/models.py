"""
RAG 数据模型
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """文档类型"""
    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    CODE = "code"


class EntityType(str, Enum):
    """实体类型"""
    PERSON = "person"
    ORGANIZATION = "organization"
    TECHNOLOGY = "technology"
    PRODUCT = "product"
    FRAMEWORK = "framework"
    LANGUAGE = "language"
    CONCEPT = "concept"
    THEORY = "theory"
    METHOD = "method"
    DATE = "date"
    LOCATION = "location"
    EVENT = "event"
    DOCUMENT = "document"


class RelationType(str, Enum):
    """关系类型"""
    IS_A = "is_a"                    # 是一种（上下位）
    PART_OF = "part_of"              # 属于（部分关系）
    USES = "uses"                    # 使用
    IMPLEMENTS = "implements"        # 实现
    DEPENDS_ON = "depends_on"        # 依赖
    RELATED_TO = "related_to"        # 相关
    CAUSES = "causes"                # 导致
    CAUSED_BY = "caused_by"          # 由...导致
    LOCATED_IN = "located_in"        # 位于
    CREATED_BY = "created_by"        # 创建于
    DEFINED_AS = "defined_as"        # 定义为
    EXAMPLE_OF = "example_of"        # ...的例子


@dataclass
class Document:
    """文档对象"""
    doc_id: str
    content: str
    doc_type: DocumentType
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Chunk:
    """文档分片"""
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    source: str
    start_char: int
    end_char: int
    embedding: Optional[List[float]] = None
    entities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "source": self.source,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "entities": self.entities,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Entity:
    """实体"""
    name: str
    type: EntityType
    description: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.name, self.type))

    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.name == other.name and self.type == other.type


@dataclass
class Relation:
    """关系"""
    from_entity: str
    to_entity: str
    relation_type: RelationType
    description: Optional[str] = None
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""  # 来源文档


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    score: float
    source: str
    chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "chunk_id": self.chunk_id,
            "metadata": self.metadata,
        }


@dataclass
class HybridRetrievalResult:
    """混合检索结果"""
    query: str
    results: List[RetrievalResult]
    vector_results: List[RetrievalResult]
    graph_results: List[RetrievalResult]
    fused_scores: List[float]
    total: int
    duration: float
