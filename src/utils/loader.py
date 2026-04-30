from pathlib import Path
from typing import List

from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from logger import setup_logger

PROJECT_ROOT = Path(__file__).resolve().parents[1]
logger = setup_logger("ingestion")

def load_documents(file_path: str | Path | None = None) -> List[Document]:
    """从目录加载所有 markdown 文件"""
    doc_path = file_path or PROJECT_ROOT / "doc"
    logger.debug(f"从目录加载文档：{doc_path}")

    loader = DirectoryLoader(
        path=str(doc_path),
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader
    )
    documents = loader.load()
    logger.debug(f"加载完成，共 {len(documents)} 篇文档")
    return documents


def split_documents(documents: List[Document], chunk_size: int = 500, chunk_overlap: int = 50) -> List[Document]:
    """递归分片文档（保持上下文连贯性）"""
    logger.debug(f"开始分片，块大小={chunk_size}, 重叠长度={chunk_overlap}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_documents(documents)
    logger.debug(f"分片完成，共生成 {len(chunks)} 个块")
    return chunks
