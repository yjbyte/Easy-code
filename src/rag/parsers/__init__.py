"""
文档解析模块

支持多种格式的文档解析。
"""
import os
import re
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

from src.rag.models import Document, DocumentType


class DocumentParser(ABC):
    """文档解析器基类"""

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """判断是否能解析该文件"""
        pass

    @abstractmethod
    def parse(self, file_path: str, metadata: Optional[dict] = None) -> Document:
        """解析文档"""
        pass

    def _extract_metadata(self, file_path: str) -> dict:
        """从文件路径提取元数据"""
        path = Path(file_path)
        return {
            "filename": path.name,
            "extension": path.suffix,
            "size": path.stat().st_size if path.exists() else 0,
        }


class TextParser(DocumentParser):
    """纯文本解析器"""

    SUPPORTED_EXTENSIONS = {".txt", ".text", ".log"}

    def can_parse(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: str, metadata: Optional[dict] = None) -> Document:
        path = Path(file_path)

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        doc_metadata = self._extract_metadata(file_path)
        if metadata:
            doc_metadata.update(metadata)

        return Document(
            doc_id=self._generate_doc_id(file_path),
            content=content,
            doc_type=DocumentType.TEXT,
            source=str(path.absolute()),
            metadata=doc_metadata,
        )

    def _generate_doc_id(self, file_path: str) -> str:
        """生成文档 ID"""
        return f"txt_{Path(file_path).stem}"


class MarkdownParser(DocumentParser):
    """Markdown 解析器"""

    SUPPORTED_EXTENSIONS = {".md", ".markdown"}

    def can_parse(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: str, metadata: Optional[dict] = None) -> Document:
        path = Path(file_path)

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # 提取标题作为元数据
        title = self._extract_title(content)

        doc_metadata = self._extract_metadata(file_path)
        if metadata:
            doc_metadata.update(metadata)
        if title:
            doc_metadata["title"] = title

        return Document(
            doc_id=self._generate_doc_id(file_path),
            content=content,
            doc_type=DocumentType.MARKDOWN,
            source=str(path.absolute()),
            metadata=doc_metadata,
        )

    def _extract_title(self, content: str) -> Optional[str]:
        """提取 Markdown 标题"""
        # 匹配第一个 # 标题
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _generate_doc_id(self, file_path: str) -> str:
        return f"md_{Path(file_path).stem}"


class PDFParser(DocumentParser):
    """PDF 解析器（使用 pdfplumber）"""

    SUPPORTED_EXTENSIONS = {".pdf"}

    def can_parse(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: str, metadata: Optional[dict] = None) -> Document:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError(
                "pdfplumber is required for PDF parsing. "
                "Install it with: pip install pdfplumber"
            )

        path = Path(file_path)
        content_parts = []

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    content_parts.append(text)

        content = "\n\n".join(content_parts)

        doc_metadata = self._extract_metadata(file_path)
        if metadata:
            doc_metadata.update(metadata)

        return Document(
            doc_id=self._generate_doc_id(file_path),
            content=content,
            doc_type=DocumentType.PDF,
            source=str(path.absolute()),
            metadata=doc_metadata,
        )

    def _generate_doc_id(self, file_path: str) -> str:
        return f"pdf_{Path(file_path).stem}"


class CodeParser(DocumentParser):
    """代码文件解析器"""

    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".c", ".cpp", ".h", ".hpp",
        ".cs", ".go", ".rs", ".rb", ".php",
        ".sh", ".bash", ".zsh",
        ".json", ".yaml", ".yml", ".toml",
        ".xml", ".html", ".css", ".scss",
    }

    def can_parse(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: str, metadata: Optional[dict] = None) -> Document:
        path = Path(file_path)

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        doc_metadata = self._extract_metadata(file_path)
        doc_metadata["language"] = self._detect_language(path.suffix)
        if metadata:
            doc_metadata.update(metadata)

        return Document(
            doc_id=self._generate_doc_id(file_path),
            content=content,
            doc_type=DocumentType.CODE,
            source=str(path.absolute()),
            metadata=doc_metadata,
        )

    def _detect_language(self, extension: str) -> str:
        """检测编程语言"""
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".sh": "shell",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
        }
        return language_map.get(extension.lower(), extension[1:])

    def _generate_doc_id(self, file_path: str) -> str:
        return f"code_{Path(file_path).stem}"


# ============ 解析器注册表 ============

_PARSERS: List[DocumentParser] = [
    TextParser(),
    MarkdownParser(),
    PDFParser(),
    CodeParser(),
]


def register_parser(parser: DocumentParser) -> None:
    """注册自定义解析器"""
    _PARSERS.insert(0, parser)  # 插入到列表前面，优先匹配


def get_parser(file_path: str) -> Optional[DocumentParser]:
    """
    根据文件路径获取合适的解析器

    Args:
        file_path: 文件路径

    Returns:
        解析器实例，如果不支持则返回 None
    """
    for parser in _PARSERS:
        if parser.can_parse(file_path):
            return parser
    return None


def parse_document(
    file_path: str,
    metadata: Optional[dict] = None
) -> Document:
    """
    解析文档

    Args:
        file_path: 文件路径
        metadata: 额外的元数据

    Returns:
        文档对象

    Raises:
        ValueError: 如果不支持的文件类型
    """
    parser = get_parser(file_path)
    if parser is None:
        ext = Path(file_path).suffix
        raise ValueError(f"Unsupported file type: {ext}")

    return parser.parse(file_path, metadata)


def get_supported_extensions() -> List[str]:
    """获取所有支持的文件扩展名"""
    extensions = set()
    for parser in _PARSERS:
        extensions.update(parser.SUPPORTED_EXTENSIONS)
    return sorted(list(extensions))
