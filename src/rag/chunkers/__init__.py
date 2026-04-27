"""
文档分片模块

提供多种分片策略。
"""
import re
import uuid
from typing import List, Optional
from abc import ABC, abstractmethod

from src.rag.models import Chunk, Document, DocumentType
from src.rag.config import get_rag_config


class Chunker(ABC):
    """分片器基类"""

    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        """
        对文档进行分片

        Args:
            document: 文档对象

        Returns:
            分片列表
        """
        pass


class RuleBasedChunker(Chunker):
    """基于规则的分片器"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]

    def chunk(self, document: Document) -> List[Chunk]:
        """
        基于规则的分片

        策略：
        1. 按分隔符分割
        2. 合并小片段直到达到 chunk_size
        3. 保持 overlap 重叠
        """
        content = document.content
        chunks = []

        # 按分隔符分割
        pieces = self._split_by_separators(content)

        # 合并片段
        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for piece in pieces:
            if len(current_chunk) + len(piece) <= self.chunk_size:
                current_chunk += piece
            else:
                # 保存当前分片
                if current_chunk:
                    chunks.append(self._create_chunk(
                        document=document,
                        content=current_chunk.strip(),
                        index=chunk_index,
                        start=current_start
                    ))
                    chunk_index += 1

                # 开始新分片，保留重叠部分
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + piece
                current_start = len(content) - len(pieces[pieces.index(piece):]) + len(overlap_text)

        # 添加最后一个分片
        if current_chunk.strip():
            chunks.append(self._create_chunk(
                document=document,
                content=current_chunk.strip(),
                index=chunk_index,
                start=current_start
            ))

        return chunks

    def _split_by_separators(self, text: str) -> List[str]:
        """按分隔符分割文本"""
        if not text:
            return []

        # 尝试每个分隔符
        for sep in self.separators:
            if sep in text:
                parts = text.split(sep)
                # 确保分隔符保留在片段末尾
                return [p + sep for p in parts[:-1]] + [parts[-1]]

        # 如果没有找到分隔符，返回整个文本
        return [text]

    def _get_overlap_text(self, text: str) -> str:
        """获取重叠文本"""
        if len(text) <= self.chunk_overlap:
            return text
        return text[-self.chunk_overlap:]

    def _create_chunk(
        self,
        document: Document,
        content: str,
        index: int,
        start: int
    ) -> Chunk:
        """创建分片对象"""
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id=document.doc_id,
            content=content,
            chunk_index=index,
            source=document.source,
            start_char=start,
            end_char=start + len(content),
            metadata=document.metadata.copy()
        )


class SemanticChunker(Chunker):
    """语义感知分片器"""

    def __init__(
        self,
        chunk_size: int = 500,
        min_chunk_size: int = 100,
        similarity_threshold: float = 0.7
    ):
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.similarity_threshold = similarity_threshold
        self._embedding_model = None

    def chunk(self, document: Document) -> List[Chunk]:
        """
        语义感知分片

        策略：
        1. 按段落分割
        2. 计算相邻段落的语义相似度
        3. 相似度高的合并，相似度低的作为分片边界
        """
        from src.rag.embeddings import get_embedding_model

        # 延迟加载 embedding 模型
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()

        content = document.content
        paragraphs = self._split_into_paragraphs(content)

        if not paragraphs:
            return []

        # 计算段落向量
        embeddings = self._embedding_model.embed(paragraphs)

        # 基于语义相似度分片
        chunks = self._chunk_by_similarity(
            document=document,
            paragraphs=paragraphs,
            embeddings=embeddings
        )

        return chunks

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """分割为段落"""
        # 按双换行符分割
        paragraphs = re.split(r'\n\n+', text.strip())
        return [p.strip() for p in paragraphs if p.strip()]

    def _chunk_by_similarity(
        self,
        document: Document,
        paragraphs: List[str],
        embeddings: List[List[float]]
    ) -> List[Chunk]:
        """基于相似度分片"""
        chunks = []
        current_chunk_parts = [paragraphs[0]]
        current_length = len(paragraphs[0])
        chunk_index = 0
        start_pos = 0

        for i in range(1, len(paragraphs)):
            # 计算与当前分片的相似度
            similarity = self._cosine_similarity(
                embeddings[i-1],
                embeddings[i]
            )

            # 如果相似度高且长度未超限，合并
            if (similarity >= self.similarity_threshold and
                current_length + len(paragraphs[i]) <= self.chunk_size):
                current_chunk_parts.append(paragraphs[i])
                current_length += len(paragraphs[i])
            else:
                # 创建分片
                content = "\n\n".join(current_chunk_parts)
                chunks.append(self._create_chunk(
                    document=document,
                    content=content,
                    index=chunk_index,
                    start=start_pos
                ))
                chunk_index += 1
                start_pos += current_length

                # 开始新分片
                current_chunk_parts = [paragraphs[i]]
                current_length = len(paragraphs[i])

        # 添加最后一个分片
        if current_chunk_parts:
            content = "\n\n".join(current_chunk_parts)
            chunks.append(self._create_chunk(
                document=document,
                content=content,
                index=chunk_index,
                start=start_pos
            ))

        return chunks

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """计算余弦相似度"""
        import numpy as np
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    def _create_chunk(
        self,
        document: Document,
        content: str,
        index: int,
        start: int
    ) -> Chunk:
        """创建分片对象"""
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id=document.doc_id,
            content=content,
            chunk_index=index,
            source=document.source,
            start_char=start,
            end_char=start + len(content),
            metadata=document.metadata.copy()
        )


class MarkdownChunker(RuleBasedChunker):
    """Markdown 专用分片器，保留结构"""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 100
    ):
        # Markdown 特定的分隔符，优先保留标题结构
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n"]
        )

    def chunk(self, document: Document) -> List[Chunk]:
        """Markdown 分片，保留标题信息"""
        chunks = super().chunk(document)

        # 为每个分片添加所在章节标题
        current_section = ""
        for chunk in chunks:
            # 提取标题
            lines = chunk.content.split('\n')
            for line in lines:
                if line.startswith('#'):
                    current_section = line.strip()
                    break

            if current_section:
                chunk.metadata["section"] = current_section

        return chunks


class CodeChunker(Chunker):
    """代码文件分片器，保持函数/类完整性"""

    def chunk(self, document: Document) -> List[Chunk]:
        """
        代码分片

        策略：尽量保持函数/类的完整性
        """
        content = document.content
        language = document.metadata.get("language", "")

        # 根据语言使用不同的分割策略
        if language in ["python", "python3"]:
            return self._chunk_python(document)
        elif language in ["javascript", "typescript", "java", "c", "cpp"]:
            return self._chunk_brace_language(document)
        else:
            # 默认使用规则分片
            return RuleBasedChunker(
                chunk_size=1000,
                chunk_overlap=0
            ).chunk(document)

    def _chunk_python(self, document: Document) -> List[Chunk]:
        """Python 代码分片"""
        chunks = []
        content = document.content

        # 按类和函数定义分割
        pattern = r'^(class |def |async def )'
        parts = re.split(pattern, content, flags=re.MULTILINE)

        current_chunk = ""
        chunk_index = 0
        start_pos = 0

        for i, part in enumerate(parts):
            if i % 2 == 0:
                # 普通代码
                current_chunk += part
            else:
                # 类/函数定义
                if current_chunk and len(current_chunk) > 100:
                    chunks.append(self._create_chunk(
                        document=document,
                        content=current_chunk,
                        index=chunk_index,
                        start=start_pos
                    ))
                    chunk_index += 1
                    start_pos += len(current_chunk)
                    current_chunk = ""

                current_chunk += part + parts[i+1] if i+1 < len(parts) else part

        # 添加剩余内容
        if current_chunk.strip():
            chunks.append(self._create_chunk(
                document=document,
                content=current_chunk,
                index=chunk_index,
                start=start_pos
            ))

        return chunks

    def _chunk_brace_language(self, document: Document) -> List[Chunk]:
        """基于花括号的语言分片（C、Java、JavaScript 等）"""
        # 简化实现：按花括号层级分割
        chunks = []
        content = document.content

        # 找到顶层函数/类定义
        lines = content.split('\n')
        current_chunk = []
        chunk_index = 0
        brace_count = 0
        start_pos = 0

        for line in lines:
            current_chunk.append(line)
            brace_count += line.count('{') - line.count('}')

            # 当花括号闭合且内容足够长时，创建分片
            if brace_count == 0 and len('\n'.join(current_chunk)) > 200:
                chunk_content = '\n'.join(current_chunk)
                chunks.append(self._create_chunk(
                    document=document,
                    content=chunk_content,
                    index=chunk_index,
                    start=start_pos
                ))
                chunk_index += 1
                start_pos += len(chunk_content)
                current_chunk = []

        # 添加剩余内容
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            chunks.append(self._create_chunk(
                document=document,
                content=chunk_content,
                index=chunk_index,
                start=start_pos
            ))

        return chunks

    def _create_chunk(
        self,
        document: Document,
        content: str,
        index: int,
        start: int
    ) -> Chunk:
        """创建分片对象"""
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id=document.doc_id,
            content=content,
            chunk_index=index,
            source=document.source,
            start_char=start,
            end_char=start + len(content),
            metadata=document.metadata.copy()
        )


# ============ 工厂函数 ============

def get_chunker(chunker_type: str = "rule", **kwargs) -> Chunker:
    """
    获取分片器实例

    Args:
        chunker_type: 分片器类型 ("rule", "semantic", "markdown", "code")
        **kwargs: 分片器参数

    Returns:
        分片器实例
    """
    config = get_rag_config()

    if chunker_type == "rule":
        return RuleBasedChunker(
            chunk_size=kwargs.get("chunk_size", config.chunk_size),
            chunk_overlap=kwargs.get("chunk_overlap", config.chunk_overlap),
        )
    elif chunker_type == "semantic":
        return SemanticChunker(
            chunk_size=kwargs.get("chunk_size", config.chunk_size),
            min_chunk_size=kwargs.get("min_chunk_size", config.min_chunk_size),
            similarity_threshold=kwargs.get("similarity_threshold", config.semantic_threshold),
        )
    elif chunker_type == "markdown":
        return MarkdownChunker(
            chunk_size=kwargs.get("chunk_size", 800),
            chunk_overlap=kwargs.get("chunk_overlap", 100),
        )
    elif chunker_type == "code":
        return CodeChunker()
    else:
        raise ValueError(f"Unknown chunker type: {chunker_type}")


def chunk_document(
    document: Document,
    chunker_type: str = "rule",
    **kwargs
) -> List[Chunk]:
    """
    对文档进行分片

    Args:
        document: 文档对象
        chunker_type: 分片器类型
        **kwargs: 分片器参数

    Returns:
        分片列表
    """
    chunker = get_chunker(chunker_type, **kwargs)

    # 根据文档类型自动选择分片器
    if document.doc_type == DocumentType.MARKDOWN:
        chunker = MarkdownChunker()
    elif document.doc_type == DocumentType.CODE:
        chunker = CodeChunker()

    return chunker.chunk(document)
