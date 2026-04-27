"""
全局配置管理
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """应用配置"""

    # LLM 配置
    zhipuai_api_key: str = Field(..., env="ZHIPUAI_API_KEY")
    zhipuai_model: str = Field(default="glm-4-plus", env="ZHIPUAI_MODEL")
    zhipuai_base_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4/",
        env="ZHIPUAI_BASE_URL"
    )

    # Neo4j 配置
    neo4j_uri: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(default="", env="NEO4J_PASSWORD")

    # Qdrant 配置
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="agentic_graphrag", env="QDRANT_COLLECTION")

    # API 配置
    api_host: str = Field(default="127.0.0.1", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=True, env="API_RELOAD")

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")

    # MCP 配置
    mcp_servers_dir: str = Field(default="./mcp_servers", env="MCP_SERVERS_DIR")

    # 缓存配置（内存缓存）
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# 全局配置实例
settings = Settings()
