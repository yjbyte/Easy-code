# RAG 系统设计文档

## 一、概述

本文档描述 Agentic GraphRAG 系统中的检索增强生成（RAG）模块的设计与实现。RAG 模块是系统的核心组件之一，负责：

1. **知识摄入**：处理文档上传、解析、分片
2. **向量化存储**：将文本转换为向量并存储到向量数据库
3. **知识图谱构建**：从文档中提取实体和关系，构建知识图谱
4. **混合检索**：结合向量检索和图谱检索，提供精确的知识获取

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAG Pipeline                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ 文档上传  │───▶│ 文档解析  │───▶│ 文档分片  │───▶│  向量化   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     知识图谱构建                          │  │
│  │            (实体提取 + 关系抽取 + 图谱存储)                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      混合检索引擎                         │  │
│  │         向量检索 + 图谱检索 + 混合重排序                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

| 组件 | 功能描述 | 技术选型 |
|------|---------|---------|
| 文档上传工具 | 支持多种格式的文档上传 | FastAPI Upload |
| 文档解析器 | 解析不同格式的文档内容 | LangChain Loaders |
| 文档分片器 | 将文档切分为合适大小的片段 | LangChain TextSplitter |
| Embedding 模型 | 将文本转换为向量 | BGE-M3 (中文优化) |
| 向量数据库 | 存储和检索向量 | Qdrant |
| 知识图谱 | 存储实体和关系 | Neo4j |
| 图谱构建 | 从文档中提取实体和关系 | GLM-4 + 正则规则 |
| 检索引擎 | 混合检索和重排序 | 自研 |

## 三、文档摄入管道

### 3.1 文档上传工具

#### 3.1.1 支持的文件格式

| 类型 | 格式 | 说明 |
|------|------|------|
| 文本 | .txt, .md | 纯文本和 Markdown |
| 文档 | .pdf, .docx | 需要特殊解析器 |
| 网页 | .html | 网页内容提取 |
| 表格 | .csv, .xlsx | 结构化数据 |
| 代码 | .py, .js, .java | 代码文件 |

#### 3.1.2 API 设计

```python
class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    file: UploadFile
    metadata: Optional[Dict[str, Any]] = None  # 用户自定义元数据
    chunk_size: Optional[int] = 500  # 分片大小
    chunk_overlap: Optional[int] = 50  # 分片重叠

class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str
    filename: str
    status: str  # success, error
    chunks_count: int
    message: str
```

#### 3.1.3 实现要点

```python
async def upload_document(
    file: UploadFile,
    metadata: Optional[Dict] = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> DocumentUploadResponse:
    """
    文档上传处理流程：

    1. 文件验证（格式、大小）
    2. 保存到临时目录
    3. 解析文档内容
    4. 文档分片
    5. 向量化并存储
    6. 构建知识图谱
    7. 清理临时文件
    """
```

### 3.2 文档解析器

#### 3.2.1 解析器架构

```python
class DocumentParser(ABC):
    """文档解析器基类"""

    @abstractmethod
    async def parse(self, file_path: str) -> List[Document]:
        """解析文档，返回文档对象列表"""
        pass

class TextParser(DocumentParser):
    """纯文本解析器"""

class PDFParser(DocumentParser):
    """PDF 解析器（使用 pdfplumber）"""

class MarkdownParser(DocumentParser):
    """Markdown 解析器"""

class CodeParser(DocumentParser):
    """代码文件解析器"""
```

#### 3.2.2 支持的解析器

```python
PARSERS = {
    '.txt': TextParser,
    '.md': MarkdownParser,
    '.pdf': PDFParser,
    '.docx': DocxParser,
    '.html': HTMLParser,
    '.py': CodeParser,
    '.js': CodeParser,
    '.java': CodeParser,
}
```

### 3.3 文档分片

#### 3.3.1 分片策略

**基于语义的分片**

```python
class SemanticChunker:
    """
    语义感知分片器

    策略：
    1. 按段落分割
    2. 计算段落之间的语义相似度
    3. 相似度高的段落合并，相似度低的边界作为分片点
    """

    def chunk(
        self,
        text: str,
        max_chunk_size: int = 500,
        min_chunk_size: int = 100,
        similarity_threshold: float = 0.7
    ) -> List[str]:
        pass
```

**基于规则的分片**

```python
class RuleBasedChunker:
    """
    基于规则的分片器

    策略：
    1. 按句子分割
    2. 按字符数限制合并句子
    3. 保持语义完整性（尽量不在句子中间切断）
    """

    def chunk(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[str]:
        pass
```

#### 3.3.2 分片配置

```python
CHUNK_CONFIG = {
    # 默认配置
    "default": {
        "chunk_size": 500,
        "chunk_overlap": 50,
        "separator": "\n\n",
    },

    # Markdown 配置（保留结构）
    "markdown": {
        "chunk_size": 800,
        "chunk_overlap": 100,
        "separators": ["\n## ", "\n### ", "\n\n", "\n"],
    },

    # 代码配置（保留函数/类完整性）
    "code": {
        "chunk_size": 1000,
        "chunk_overlap": 0,
        "keep_structure": True,
    },
}
```

#### 3.3.3 分片元数据

每个分片需要携带以下元数据：

```python
class ChunkMetadata(BaseModel):
    """分片元数据"""
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    source: str  # 文档名称/路径
    page: Optional[int] = None  # 页码
    start_char: int
    end_char: int
    embedding: Optional[List[float]] = None
    entities: List[str] = []  # 提取的实体
    created_at: datetime
```

## 四、向量化与向量存储

### 4.1 Embedding 模型选型

#### 4.1.1 中文 Embedding 模型对比

| 模型 | 维度 | 性能 | 速度 | 推荐场景 |
|------|------|------|------|---------|
| BGE-M3 | 1024 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 通用（推荐） |
| BGE-Large | 1024 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 长文本 |
| text2vec | 768 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 快速检索 |
| m3e-base | 768 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 中文问答 |
| jina-embeddings | 768 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 多语言 |

#### 4.1.2 最终选型：BGE-M3

**选择理由：**

1. **多语言支持**：对中文优化良好，支持多语言
2. **多粒度**：支持短文本、长文本、多语言
3. **高性能**：在 MTEB 中文榜单上表现优异
4. **开源可用**：可私有部署
5. **稳定性**：经过大规模验证

```python
class EmbeddingModel:
    """Embedding 模型封装"""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model = SentenceTransformer(model_name)
        self.dimension = 1024

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量"""
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        """单个文本向量化"""
        return self.embed([text])[0]
```

#### 4.1.3 使用方式

```python
# 使用 HuggingFace 模型
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-m3')
embeddings = model.encode(['你的文本'], normalize_embeddings=True)

# 或者使用 FlagEmbedding
from FlagEmbedding import BGEM3FlagModel
model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)
embeddings = model.encode(['你的文本'])['dense_vecs']
```

### 4.2 向量数据库：Qdrant

#### 4.2.1 为什么选择 Qdrant

| 特性 | Qdrant | Pinecone | Milvus | Weaviate |
|------|--------|----------|--------|----------|
| 开源 | ✅ | ❌ | ✅ | ✅ |
| 性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 过滤器 | ✅ | ✅ | ✅ | ✅ |
| 混合检索 | ✅ | ❌ | ✅ | ✅ |
| 部署 | Docker | 云服务 | Docker/云 | Docker |
| 中文支持 | ✅ | ✅ | ✅ | ✅ |

**选择 Qdrant 的理由：**

1. **高性能**：Rust 实现，性能优异
2. **易部署**：单 Docker 部署，无需复杂依赖
3. **丰富功能**：支持过滤、混合检索、Payload 索引
4. **API 友好**：RESTful API + Python SDK
5. **过滤能力强**：支持复杂的元数据过滤

#### 4.2.2 Collection 设计

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantVectorStore:
    """Qdrant 向量存储"""

    def __init__(self, url: str = "http://localhost:6333"):
        self.client = QdrantClient(url=url)
        self.collection_name = "knowledge_base"
        self.vector_size = 1024  # BGE-M3 维度

    def create_collection(self):
        """创建 Collection"""
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
            # 创建 Payload 索引以支持过滤
            payload_schema={
                "document_id": "keyword",
                "source": "keyword",
                "created_at": "integer",
            }
        )

    def insert_chunks(self, chunks: List[ChunkMetadata]) -> List[str]:
        """插入分片"""
        points = []
        for chunk in chunks:
            point = PointStruct(
                id=chunk.chunk_id,
                vector=chunk.embedding,
                payload={
                    "content": chunk.content,
                    "document_id": chunk.document_id,
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "entities": chunk.entities,
                    "created_at": chunk.created_at.timestamp(),
                }
            )
            points.append(point)

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """向量检索"""
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=self._build_filter(filters) if filters else None,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
```

#### 4.2.3 部署方式

```bash
# Docker 部署
docker run -p 6333:6333 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant

# 带持久化的部署
docker run -d -p 6333:6333 \
    -v /path/to/storage:/qdrant/storage \
    --name qdrant \
    qdrant/qdrant
```

## 五、知识图谱构建

### 5.1 Neo4j 图数据库

#### 5.1.1 为什么选择 Neo4j

| 特性 | Neo4j | ArangoDB | Amazon Neptune |
|------|-------|----------|----------------|
| 图查询语言 | Cypher (强大) | AQL | Gremlin/SPARQL |
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 社区 | 活跃 | 中等 | 中等 |
| 可视化 | ✅ 内置 | ❌ | ❌ |
| 中文支持 | ✅ | ✅ | ✅ |

#### 5.1.2 部署方式

```bash
# Docker 部署
docker run -d \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    -v $(pwd)/neo4j/data:/data \
    neo4j:latest
```

### 5.2 图谱构建流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      知识图谱构建流程                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  文档分片                                                         │
│     │                                                           │
│     ▼                                                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              实体提取 (NER)                             │    │
│  │  - 人物、组织、地点、时间、技术术语等                   │    │
│  └────────────────────────────────────────────────────────┘    │
│     │                                                           │
│     ▼                                                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              关系抽取                                   │    │
│  │  - 实体间关系 (is-a, part-of, caused-by, etc.)         │    │
│  └────────────────────────────────────────────────────────┘    │
│     │                                                           │
│     ▼                                                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              实体消歧与链接                             │    │
│  │  - 同一实体的不同指称合并                               │    │
│  └────────────────────────────────────────────────────────┘    │
│     │                                                           │
│     ▼                                                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              存储到 Neo4j                               │    │
│  │  - 创建节点和关系                                       │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 实体提取

#### 5.3.1 基于 LLM 的实体提取

```python
class EntityExtractor:
    """基于 LLM 的实体提取器"""

    def __init__(self):
        self.llm = get_glm_client()

    async def extract_entities(self, text: str) -> List[Entity]:
        """
        从文本中提取实体

        提示词模板：

        请从以下文本中提取重要的实体，包括：
        1. 人物/组织
        2. 技术/产品名称
        3. 概念/术语
        4. 时间/地点

        返回 JSON 格式：
        {
            "entities": [
                {"name": "实体名", "type": "类型", "description": "描述"}
            ]
        }
        """

        prompt = f"""
请从以下文本中提取重要的实体，包括：
1. 人物/组织
2. 技术/产品名称
3. 概念/术语
4. 时间/地点

文本：
{text}

请以 JSON 格式返回，包含实体的名称、类型和描述。
"""

        response = await self.llm.chat(prompt)
        return self._parse_entities(response)
```

#### 5.3.2 预定义实体类型

```python
ENTITY_TYPES = {
    # 人物类
    "PERSON": "人物",
    "ORGANIZATION": "组织/公司",

    # 技术类
    "TECHNOLOGY": "技术",
    "PRODUCT": "产品",
    "FRAMEWORK": "框架/库",
    "LANGUAGE": "编程语言",

    # 概念类
    "CONCEPT": "概念",
    "THEORY": "理论",
    "METHOD": "方法",

    # 时空类
    "DATE": "日期",
    "LOCATION": "地点",

    # 其他
    "EVENT": "事件",
    "DOCUMENT": "文档",
}
```

### 5.4 关系抽取

```python
class RelationExtractor:
    """关系抽取器"""

    async def extract_relations(
        self,
        text: str,
        entities: List[Entity]
    ) -> List[Relation]:
        """
        从文本中抽取实体间的关系

        预定义关系类型：
        - IS_A: 是一种（上下位关系）
        - PART_OF: 属于（部分关系）
        - USES: 使用
        - IMPLEMENTS: 实现
        - DEPENDS_ON: 依赖
        - RELATED_TO: 相关
        - CAUSES: 导致
        - LOCATED_IN: 位于
        - CREATED_BY: 创建于
        """

        entity_list = "\n".join([
            f"- {e.name} ({e.type})"
            for e in entities
        ])

        prompt = f"""
从以下文本中，分析实体之间的关系：

实体列表：
{entity_list}

文本：
{text}

请识别实体间的关系，返回 JSON：
{{
    "relations": [
        {{"from": "实体1", "to": "实体2", "type": "关系类型", "description": "描述"}}
    ]
}}
"""

        response = await self.llm.chat(prompt)
        return self._parse_relations(response)
```

### 5.5 Neo4j 存储

```python
from neo4j import GraphDatabase

class Neo4jGraphStore:
    """Neo4j 图谱存储"""

    def __init__(self, uri: str = "bolt://localhost:7687"):
        self.driver = GraphDatabase.driver(
            uri,
            auth=("neo4j", "password")
        )

    def create_entity(self, entity: Entity, source: str):
        """创建实体节点"""
        query = """
        MERGE (e:Entity {name: $name})
        SET e.type = $type,
            e.description = $description,
            e.source = $source,
            e.updated_at = datetime()
        RETURN e
        """
        with self.driver.session() as session:
            session.run(
                query,
                name=entity.name,
                type=entity.type,
                description=entity.description,
                source=source
            )

    def create_relation(self, relation: Relation):
        """创建关系"""
        query = """
        MATCH (a:Entity {name: $from})
        MATCH (b:Entity {name: $to})
        MERGE (a)-[r:RELATES {type: $type}]->(b)
        SET r.description = $description,
            r.source = $source,
            r.updated_at = datetime()
        RETURN r
        """
        with self.driver.session() as session:
            session.run(
                query,
                from=relation.from_entity,
                to=relation.to_entity,
                type=relation.relation_type,
                description=relation.description,
                source=relation.source
            )
```

## 六、混合检索

### 6.1 检索架构

```
用户查询
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    查询理解与扩展                            │
│  - 意图识别                                                  │
│  - 查询重写                                                  │
│  - 关键词提取                                                │
└─────────────────────────────────────────────────────────────┘
    │
    ├─────────────────┬─────────────────┐
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────┐    ┌─────────┐
│ 向量检索 │    │ 图谱检索 │    │ 关键词   │
│(Qdrant) │    │ (Neo4j) │    │  检索    │
└─────────┘    └─────────┘    └─────────┘
    │              │              │
    └──────────────┴──────────────┘
                   │
                   ▼
         ┌───────────────────┐
         │    结果融合       │
         │  - 去重          │
         │  - 排序          │
         │  - 重排序        │
         └───────────────────┘
                   │
                   ▼
              最终结果
```

### 6.2 向量检索

```python
class VectorRetriever:
    """向量检索器"""

    def __init__(self, vector_store: QdrantVectorStore):
        self.store = vector_store
        self.embedding_model = EmbeddingModel()

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[RetrievalResult]:
        # 生成查询向量
        query_vector = self.embedding_model.embed_single(query)

        # 向量检索
        results = self.store.search(
            query_vector=query_vector,
            limit=top_k,
            filters=filters
        )

        return [
            RetrievalResult(
                content=r.payload['content'],
                score=r.score,
                source=r.payload['source'],
                metadata=r.payload
            )
            for r in results
        ]
```

### 6.3 图谱检索

```python
class GraphRetriever:
    """图谱检索器"""

    def __init__(self, graph_store: Neo4jGraphStore):
        self.store = graph_store

    async def retrieve(
        self,
        query: str,
        entities: List[str],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        图谱检索策略：

        1. 实体邻居检索：获取实体的直接邻居
        2. 多跳推理：沿着关系路径进行推理
        3. 社区发现：获取相关实体群
        """

        results = []

        # 策略1: 实体邻居
        neighbors = await self._get_neighbors(entities, depth=1)
        results.extend(neighbors)

        # 策略2: 多跳路径
        paths = await self._find_paths(entities, max_depth=2)
        results.extend(paths)

        # 策略3: 相关实体群
        communities = await self._get_communities(entities)
        results.extend(communities)

        # 去重并排序
        return self._deduplicate_and_rank(results, top_k)

    async def _get_neighbors(
        self,
        entities: List[str],
        depth: int = 1
    ) -> List[Dict]:
        """获取实体邻居"""
        query = """
        MATCH (e:Entity)
        WHERE e.name IN $entities
        CALL apoc.path.subgraphAll(e, {
            maxLevel: $depth,
            relationshipFilter: "RELATES>"
        }) YIELD nodes, relationships
        RETURN nodes, relationships
        LIMIT 100
        """
        # 执行查询并返回结果
        pass
```

### 6.4 混合检索融合

```python
class HybridRetriever:
    """混合检索器"""

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        graph_retriever: GraphRetriever
    ):
        self.vector_retriever = vector_retriever
        self.graph_retriever = graph_retriever

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.7  # 向量检索权重
    ) -> List[RetrievalResult]:
        """
        混合检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            alpha: 向量检索权重 (0-1)，图谱检索权重为 1-alpha
        """

        # 并行执行检索
        vector_results, graph_results = await asyncio.gather(
            self.vector_retriever.retrieve(query, top_k=top_k*2),
            self.graph_retriever.retrieve(query, top_k=top_k*2)
        )

        # 融合结果
        fused_results = self._reciprocal_rank_fusion(
            vector_results,
            graph_results,
            alpha=alpha
        )

        # 重排序
        reranked_results = await self._rerank(query, fused_results)

        return reranked_results[:top_k]

    def _reciprocal_rank_fusion(
        self,
        results_list: List[List[RetrievalResult]],
        k: int = 60,
        alpha: float = 0.7
    ) -> List[RetrievalResult]:
        """
        RRF 融合算法

        score(d) = sum(weight_i / (k + rank_i(d)))
        """
        scores = {}

        for i, results in enumerate(results_list):
            weight = alpha if i == 0 else (1 - alpha)
            for rank, result in enumerate(results, 1):
                doc_id = result.content  # 使用内容作为唯一标识
                if doc_id not in scores:
                    scores[doc_id] = {
                        'result': result,
                        'score': 0
                    }
                scores[doc_id]['score'] += weight / (k + rank)

        # 按融合分数排序
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )

        return [r['result'] for r in sorted_results]

    async def _rerank(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        使用 LLM 进行重排序

        或者使用轻量级的 Cross-Encoder 模型
        """
        # 简化实现：直接返回原排序
        # 实际可以使用 BGE-Reranker 等
        return results
```

### 6.5 查询重写

```python
class QueryRewriter:
    """查询重写器"""

    async def rewrite(
        self,
        query: str,
        history: Optional[List[str]] = None
    ) -> List[str]:
        """
        查询重写策略：

        1. 同义词扩展
        2. 上下文补全
        3. 多意图分解
        """

        rewritten_queries = [query]  # 原始查询

        # 使用 LLM 生成查询变体
        prompt = f"""
请对以下用户查询进行改写和扩展，生成 3 个不同的查询变体：
- 使用同义词替换
- 补充可能的上下文
- 改变查询角度

原始查询：{query}

请返回 3 个改写后的查询，每行一个。
"""

        response = await self.llm.chat(prompt)
        variants = self._parse_variants(response)
        rewritten_queries.extend(variants)

        return rewritten_queries
```

## 七、工具集成

### 7.1 RAG 工具列表

```python
RAG_TOOLS = [
    # 文档上传工具（已有）
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    CREATE_FILE_TOOL,

    # 新增 RAG 工具
    KNOWLEDGE_SEARCH_TOOL,      # 知识库检索
    GRAPH_SEARCH_TOOL,          # 图谱检索
    HYBRID_SEARCH_TOOL,         # 混合检索
    DOCUMENT_UPLOAD_TOOL,       # 文档上传
]
```

### 7.2 知识库检索工具

```python
async def _knowledge_search_impl(
    query: str,
    top_k: int = 5,
    filters: Optional[Dict] = None
) -> dict:
    """
    知识库检索工具

    从向量数据库中检索相关文档片段
    """
    retriever = get_hybrid_retriever()

    results = await retriever.retrieve(
        query=query,
        top_k=top_k
    )

    return {
        "query": query,
        "results": [
            {
                "content": r.content,
                "score": r.score,
                "source": r.source,
                "metadata": r.metadata
            }
            for r in results
        ],
        "total": len(results)
    }

KNOWLEDGE_SEARCH_TOOL = Tool(
    name="knowledge_search",
    description="从知识库中检索相关文档内容，适用于需要查询已有知识的问题",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="检索问题或关键词",
            required=True
        ),
        ToolParameter(
            name="top_k",
            type="integer",
            description="返回结果数量，默认 5",
            required=False,
            default=5
        ),
        ToolParameter(
            name="filters",
            type="object",
            description="过滤条件，如 {\"document_id\": \"xxx\"}",
            required=False
        )
    ],
    async_mode=True
)
KNOWLEDGE_SEARCH_TOOL.set_function(_knowledge_search_impl)
```

### 7.3 文档上传工具

```python
async def _document_upload_impl(
    file_content: str,
    filename: str,
    chunk_size: int = 500
) -> dict:
    """
    文档上传工具

    接收文档内容，进行解析、分片、向量化，并存储到知识库
    """
    # 1. 保存临时文件
    # 2. 解析文档
    # 3. 分片处理
    # 4. 向量化
    # 5. 存储到 Qdrant
    # 6. 构建知识图谱

    return {
        "success": True,
        "document_id": doc_id,
        "chunks_count": len(chunks),
        "message": f"成功上传文档 {filename}，共 {len(chunks)} 个分片"
    }

DOCUMENT_UPLOAD_TOOL = Tool(
    name="document_upload",
    description="上传文档到知识库，支持 txt、md、pdf 等格式",
    category=ToolCategory.BUILTIN,
    parameters=[
        ToolParameter(
            name="file_content",
            type="string",
            description="文档内容（Base64 编码）",
            required=True
        ),
        ToolParameter(
            name="filename",
            type="string",
            description="文件名",
            required=True
        ),
        ToolParameter(
            name="chunk_size",
            type="integer",
            description="分片大小，默认 500",
            required=False,
            default=500
        )
    ],
    async_mode=True
)
DOCUMENT_UPLOAD_TOOL.set_function(_document_upload_impl)
```

## 八、数据流

### 8.1 文档摄入流程

```
用户上传文档
    │
    ▼
验证文件格式和大小
    │
    ▼
保存到临时目录
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    并行处理                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │  文档解析    │         │  元数据提取  │                  │
│  └──────────────┘         └──────────────┘                  │
│         │                         │                           │
│         └────────────┬────────────┘                         │
│                      ▼                                       │
│              ┌──────────────┐                                │
│              │  文档分片    │                                │
│              └──────────────┘                                │
│                      │                                       │
│         ┌────────────┴────────────┐                          │
│         ▼                         ▼                          │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │  Embedding   │         │  实体提取    │                  │
│  └──────────────┘         └──────────────┘                  │
│         │                         │                           │
│         ▼                         ▼                          │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │  存储到      │         │  关系抽取    │                  │
│  │  Qdrant      │         └──────────────┘                  │
│  └──────────────┘                │                           │
│                                    ▼                          │
│                           ┌──────────────┐                   │
│                           │  存储到      │                   │
│                           │  Neo4j      │                   │
│                           └──────────────┘                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
            返回文档 ID 和统计信息
```

### 8.2 检索流程

```
用户查询
    │
    ▼
查询理解（意图识别、实体提取）
    │
    ▼
查询重写（生成多个查询变体）
    │
    ├─────────────────┬─────────────────┐
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────┐    ┌─────────┐
│ 向量检索 │    │ 图谱检索 │    │ 关键词   │
│(Qdrant) │    │ (Neo4j) │    │  匹配    │
└─────────┘    └─────────┘    └─────────┘
    │              │              │
    └──────────────┴──────────────┘
                   │
                   ▼
            结果融合 (RRF)
                   │
                   ▼
            LLM 重排序
                   │
                   ▼
            返回 Top-K 结果
```

## 九、配置管理

### 9.1 环境变量

```bash
# Qdrant 配置
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Embedding 模型配置
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=cuda  # cpu 或 cuda
EMBEDDING_BATCH_SIZE=32

# RAG 配置
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RETRIEVAL=5
HYBRID_ALPHA=0.7  # 向量检索权重

# 文档上传配置
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=.txt,.md,.pdf,.docx
```

### 9.2 配置类

```python
from pydantic_settings import BaseSettings

class RAGConfig(BaseSettings):
    """RAG 配置"""

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "knowledge_base"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Embedding
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Retrieval
    top_k_retrieval: int = 5
    hybrid_alpha: float = 0.7
    score_threshold: float = 0.5

    # Upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = [
        ".txt", ".md", ".pdf", ".docx", ".html"
    ]

    class Config:
        env_file = ".env"
```

## 十、性能优化

### 10.1 批处理

```python
class BatchEmbedder:
    """批量 Embedding 处理"""

    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        self.model = EmbeddingModel()

    async def embed_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """批量向量化"""
        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.model.embed(batch)
            embeddings.extend(batch_embeddings)
        return embeddings
```

### 10.2 缓存策略

```python
from functools import lru_cache

class CachedEmbedder:
    """带缓存的 Embedding"""

    def __init__(self, cache_size: int = 1000):
        self.cache_size = cache_size
        self.model = EmbeddingModel()

    @lru_cache(maxsize=1000)
    def embed(self, text: str) -> List[float]:
        """带缓存的向量化"""
        return self.model.embed_single(text)
```

### 10.3 异步处理

```python
async def process_document_async(
    file_path: str,
    chunk_size: int = 500
) -> str:
    """异步处理文档"""

    # 解析文档
    documents = await parser.parse_async(file_path)

    # 并行分片和向量化
    chunks_tasks = [
        chunker.chunk_async(doc.content, chunk_size)
        for doc in documents
    ]
    all_chunks = await asyncio.gather(*chunks_tasks)

    # 批量向量化
    embeddings = await embedder.embed_batch([
        c.content for c in all_chunks
    ])

    # 批量存储
    await vector_store.insert_batch(all_chunks, embeddings)
```

## 十一、错误处理

### 11.1 错误类型

```python
class RAGError(Exception):
    """RAG 基础错误"""
    pass

class DocumentParseError(RAGError):
    """文档解析错误"""
    pass

class EmbeddingError(RAGError):
    """向量化错误"""
    pass

class StorageError(RAGError):
    """存储错误"""
    pass

class RetrievalError(RAGError):
    """检索错误"""
    pass
```

### 11.2 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def embed_with_retry(text: str) -> List[float]:
    """带重试的向量化"""
    return await embedder.embed_async(text)
```

## 十二、监控与日志

### 12.1 性能指标

```python
from prometheus_client import Counter, Histogram

# 向量化计数
embedding_counter = Counter(
    'rag_embedding_total',
    'Total embedding operations',
    ['status']
)

# 检索延迟
retrieval_histogram = Histogram(
    'rag_retrieval_duration_seconds',
    'Retrieval duration',
    ['method']  # vector, graph, hybrid
)

# 文档处理计数
document_counter = Counter(
    'rag_document_processed_total',
    'Total documents processed',
    ['status', 'file_type']
)
```

### 12.2 日志记录

```python
import logging

logger = logging.getLogger(__name__)

async def process_document(file_path: str):
    """文档处理（带日志）"""
    logger.info(f"Processing document: {file_path}")

    try:
        chunks = await parse_and_chunk(file_path)
        logger.info(f"Document chunked into {len(chunks)} parts")

        embeddings = await embed_chunks(chunks)
        logger.info(f"Generated {len(embeddings)} embeddings")

        await store_embeddings(chunks, embeddings)
        logger.info("Document processed successfully")

    except Exception as e:
        logger.error(f"Document processing failed: {e}", exc_info=True)
        raise
```

## 十三、扩展性

### 13.1 插件化解析器

```python
class ParserRegistry:
    """解析器注册表"""

    def __init__(self):
        self._parsers = {}

    def register(self, extension: str, parser: DocumentParser):
        """注册解析器"""
        self._parsers[extension] = parser

    def get_parser(self, extension: str) -> DocumentParser:
        """获取解析器"""
        if extension not in self._parsers:
            raise ValueError(f"No parser for {extension}")
        return self._parsers[extension]
```

### 13.2 自定义分片器

```python
class CustomChunker:
    """自定义分片器接口"""

    def chunk(self, text: str, **kwargs) -> List[str]:
        """分片方法"""
        raise NotImplementedError
```

## 十四、总结

本设计文档描述了 Agentic GraphRAG 系统中 RAG 模块的完整设计，包括：

1. **文档摄入**：支持多种格式的文档上传、解析和分片
2. **向量化存储**：使用 BGE-M3 模型和 Qdrant 向量数据库
3. **知识图谱**：使用 Neo4j 构建实体和关系图谱
4. **混合检索**：结合向量检索和图谱检索，提供精确的知识获取

该设计具有以下特点：

- **高性能**：异步处理、批量操作、缓存优化
- **可扩展**：插件化架构，易于添加新的解析器和检索策略
- **易部署**：使用 Docker 部署 Qdrant 和 Neo4j
- **中文优化**：选择对中文友好的 Embedding 模型
- **混合检索**：结合语义检索和知识图谱，提升检索质量
