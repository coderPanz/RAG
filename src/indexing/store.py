from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_chroma import Chroma

from src.embedding.vectorizer import embed_texts
from src.logger import setup_logger

_DEFAULT_PERSIST_DIR = Path(__file__).resolve().parent / "chroma_db"
_vector_store = None
logger = setup_logger("indexing")


class LocalBGEEmbeddings:
    """将本地 BGE 向量模型适配为 LangChain Chroma 所需的 embedding 接口"""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return embed_texts(texts).tolist()

    def embed_query(self, text: str) -> List[float]:
        return embed_texts([text])[0].tolist()


def get_chroma_client(persist_dir: str | Path | None = None) -> Chroma:
    """初始化并返回 ChromaDB 客户端（单例）"""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    db_path = persist_dir or _DEFAULT_PERSIST_DIR
    logger.debug(f"初始化 ChromaDB，持久化目录：{db_path}")

    embeddings = LocalBGEEmbeddings()
    _vector_store = Chroma(
        collection_name="knowledge_base",
        embedding_function=embeddings,
        persist_directory=str(db_path),
    )
    logger.debug("ChromaDB 已初始化")
    return _vector_store


def add_documents(documents: List[Document]) -> None:
    """将文档分片向量化后存入 ChromaDB"""
    logger.debug(f"写入 {len(documents)} 个文档分片到 ChromaDB...")
    get_chroma_client().add_documents(documents)
    logger.debug("✓ 文档分片写入完成")


def similarity_search(query: str, top_k: int = 10) -> List[Document]:
    """向量召回：检索与 query 最相似的 top_k 个文档分片"""
    logger.debug(f"执行相似度检索：query='{query[:50]}...' top_k={top_k}")
    results = get_chroma_client().similarity_search(query, k=top_k)
    logger.debug(f"✓ 检索完成，返回 {len(results)} 个结果")
    return results