"""
RAG 配置管理
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGConfig(BaseSettings):
    """RAG 配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RAG_",
        case_sensitive=False,
        extra="ignore",
    )

    # ============ Qdrant 配置 ============
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant 服务地址")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API 密钥")
    qdrant_collection: str = Field(default="agentic_graphrag", description="Collection 名称")
    qdrant_vector_size: int = Field(default=1024, description="向量维度")

    # ============ Neo4j 配置 ============
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j 连接地址")
    neo4j_user: str = Field(default="neo4j", description="Neo4j 用户名")
    neo4j_password: str = Field(default="password", description="Neo4j 密码")
    neo4j_database: str = Field(default="neo4j", description="数据库名称")

    # ============ Embedding 配置 ============
    embedding_model: str = Field(default="BAAI/bge-m3", description="Embedding 模型名称")
    embedding_device: str = Field(default="cpu", description="设备类型: cpu 或 cuda")
    embedding_batch_size: int = Field(default=32, description="批处理大小")
    embedding_dimension: int = Field(default=1024, description="向量维度")

    # ============ 分片配置 ============
    chunk_size: int = Field(default=500, description="分片大小（字符数）")
    chunk_overlap: int = Field(default=50, description="分片重叠大小")
    min_chunk_size: int = Field(default=100, description="最小分片大小")
    semantic_threshold: float = Field(default=0.7, description="语义分片相似度阈值")

    # ============ 检索配置 ============
    top_k_retrieval: int = Field(default=5, description="检索返回数量")
    hybrid_alpha: float = Field(default=0.7, description="向量检索权重（0-1）")
    score_threshold: float = Field(default=0.5, description="检索分数阈值")
    rrf_k: int = Field(default=60, description="RRF 融合参数 k")

    # ============ 图谱配置 ============
    graph_depth: int = Field(default=2, description="图谱检索深度")
    graph_max_nodes: int = Field(default=100, description="最大返回节点数")

    # ============ 文档上传配置 ============
    max_file_size: int = Field(default=10 * 1024 * 1024, description="最大文件大小（10MB）")
    upload_dir: str = Field(default="uploads", description="上传目录")
    temp_dir: str = Field(default="temp", description="临时文件目录")

    # ============ 支持的文件格式 ============
    allowed_extensions: List[str] = Field(
        default=[
            ".txt",
            ".md",
            ".pdf",
            ".docx",
            ".html",
            ".htm",
            ".py",
            ".js",
            ".java",
            ".json",
            ".csv",
        ],
        description="允许的文件扩展名"
    )

    # ============ 缓存配置 ============
    enable_cache: bool = Field(default=True, description="启用 Embedding 缓存")
    cache_size: int = Field(default=1000, description="缓存大小")

    def debug_env_vars(self) -> dict:
        """调试：显示环境变量读取情况"""
        return {
            "env_file_exists": Path(".env").exists(),
            "RAG_QDRANT_URL_env": os.getenv("RAG_QDRANT_URL"),
            "RAG_NEO4J_URI_env": os.getenv("RAG_NEO4J_URI"),
            "current_qdrant_url": self.qdrant_url,
            "current_neo4j_uri": self.neo4j_uri,
        }


# 全局配置实例
_config: Optional[RAGConfig] = None


def get_rag_config() -> RAGConfig:
    """获取 RAG 配置单例"""
    global _config
    if _config is None:
        _config = RAGConfig()
    return _config


def set_rag_config(config: RAGConfig) -> None:
    """设置 RAG 配置"""
    global _config
    _config = config
