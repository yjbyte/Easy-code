"""
Embedding 模块

提供文本向量化功能，使用 BGE-M3 模型。
"""
import os
from typing import List, Optional, Dict
from functools import lru_cache
import hashlib

from sentence_transformers import SentenceTransformer
import numpy as np

from src.rag.config import get_rag_config


class EmbeddingModel:
    """Embedding 模型封装"""

    def __init__(self, config=None):
        self.config = config or get_rag_config()
        self.model = None
        self.dimension = self.config.embedding_dimension
        # 设置 Hugging Face 镜像（如果配置了）
        self._setup_mirror()
        self._load_model()

    def _setup_mirror(self):
        """设置 Hugging Face 镜像"""
        # 如果配置了镜像地址，使用环境变量
        mirror_url = os.getenv("HF_ENDPOINT") or os.getenv("HUGGINGFACE_HUB_URL")
        if mirror_url:
            os.environ["HF_ENDPOINT"] = mirror_url

    def _load_model(self):
        """加载模型"""
        if self.model is None:
            device = self.config.embedding_device
            try:
                self.model = SentenceTransformer(
                    self.config.embedding_model,
                    device=device
                )
            except Exception as e:
                # 如果加载失败，尝试使用镜像
                if os.getenv("HF_ENDPOINT") is None:
                    # 设置默认镜像（ hf-mirror）
                    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                    print(f"使用 Hugging Face 镜像: {os.environ['HF_ENDPOINT']}")
                    self.model = SentenceTransformer(
                        self.config.embedding_model,
                        device=device
                    )
                else:
                    raise e

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成向量

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        self._load_model()

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=self.config.embedding_batch_size
        )

        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        """
        单个文本向量化

        Args:
            text: 文本

        Returns:
            向量
        """
        result = self.embed([text])
        return result[0]

    async def embed_async(self, texts: List[str]) -> List[List[float]]:
        """异步批量向量化"""
        # 对于 CPU 操作，直接使用同步方法
        # 对于 GPU，可以考虑使用线程池
        return self.embed(texts)


class CachedEmbeddingModel(EmbeddingModel):
    """带缓存的 Embedding 模型"""

    def __init__(self, config=None):
        super().__init__(config)
        self._cache: Dict[str, List[float]] = {}

    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def embed_single(self, text: str) -> List[float]:
        """带缓存的单个文本向量化"""
        cache_key = self._get_cache_key(text)

        if cache_key in self._cache:
            return self._cache[cache_key]

        embedding = super().embed_single(text)
        self._cache[cache_key] = embedding

        # 限制缓存大小
        if len(self._cache) > self.config.cache_size:
            # 删除最早的缓存
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        return embedding

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()


# 全局实例
_global_model: Optional[EmbeddingModel] = None


def get_embedding_model(use_cache: bool = True) -> EmbeddingModel:
    """
    获取 Embedding 模型单例

    Args:
        use_cache: 是否使用缓存

    Returns:
        Embedding 模型实例
    """
    global _global_model
    if _global_model is None:
        if use_cache:
            _global_model = CachedEmbeddingModel()
        else:
            _global_model = EmbeddingModel()
    return _global_model


def create_embedding_model(
    model_name: str = "BAAI/bge-m3",
    device: str = "cpu"
) -> EmbeddingModel:
    """
    创建新的 Embedding 模型实例

    Args:
        model_name: 模型名称
        device: 设备类型

    Returns:
        Embedding 模型实例
    """
    class Config:
        embedding_model = model_name
        embedding_device = device
        embedding_dimension = 1024
        embedding_batch_size = 32

    config = Config()
    return EmbeddingModel(config)
