import time
from typing import List

from langchain_core.documents import Document

from utils.loader import load_documents, split_documents
from utils.store import add_documents, similarity_search, get_chroma_client
from utils.reranker import rerank
from utils.llm import generate_answer, get_llm_client, get_model
from logger import setup_logger
from agentic_rag.agent_router import llm_router

logger = setup_logger("agentic.pipeline")

MAX_RETRIES = 2
  

def build_index(file_paths: List[str] | None = None) -> None:
    """离线阶段：文档加载 → 分片 → 向量化 → 写入 ChromaDB 索引。
    向量化由 LocalBGEEmbeddings（store.py）在写入时自动完成。
    如果集合中已有数据则跳过，避免重复写入。
    """
    logger.info("=" * 60)
    logger.info("启动索引构建流程")

    store = get_chroma_client()
    existing = store._collection.count()
    if existing > 0:
        logger.info(f"索引已存在（{existing} 个分片），跳过构建。")
        return

    start_time = time.time()

    logger.info("[1/4] 加载文档...")
    documents = load_documents()
    logger.info(f"✓ 加载完成，共 {len(documents)} 篇文档")

    logger.info("[2/4] 文档分片...")
    chunks = split_documents(documents)
    logger.info(f"✓ 分片完成，共 {len(chunks)} 个分片（块大小=500, 重叠=50）")

    logger.info("[3/4] 向量化并写入 ChromaDB...")
    add_documents(chunks)
    logger.info(f"✓ 向量化完成，已写入索引")

    elapsed = time.time() - start_time
    logger.info(f"[4/4] 索引构建完成（耗时 {elapsed:.2f}s）")
    logger.info("=" * 60)


def query(question: str) -> str:
    """agentic-rag"""
    logger.info("=" * 60)
    logger.info(f"用户提问：{question}")
    start_time = time.time()
    answer = llm_router(question)
    return answer
