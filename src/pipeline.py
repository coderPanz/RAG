import time
from typing import List

from src.ingestion.loader import load_documents, split_documents
from src.indexing.store import add_documents, similarity_search, get_chroma_client
from src.retrieval.reranker import rerank
from src.generation.llm import generate_answer
from src.logger import setup_logger

logger = setup_logger("pipeline")


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
    """在线阶段：向量召回 → 重排 → LLM 生成答案。

    1. similarity_search：用 BGE bi-encoder 快速召回 top-10 候选分片
    2. rerank：用 BGE cross-encoder 精排，取 top-3
    3. generate_answer：将问题 + top-3 分片作为上下文喂给 LLM
    """
    logger.info("=" * 60)
    logger.info(f"用户提问：{question}")

    start_time = time.time()

    logger.info("[1/4] 向量召回（BGE bi-encoder）...")
    candidates = similarity_search(question, top_k=10)
    logger.info(f"✓ 召回完成，得到 {len(candidates)} 个候选分片")

    logger.info("[2/4] 精排重排（BGE cross-encoder）...")
    ranked = rerank(question, candidates, top_k=3)
    logger.info(f"✓ 精排完成，得到 {len(ranked)} 个分片")
    for i, doc in enumerate(ranked, 1):
        source = doc.metadata.get("source", "unknown")
        content_preview = doc.page_content[:50].replace("\n", " ")
        logger.info(f"   [{i}] 来源：{source} | 预览：{content_preview}...")

    logger.info("[3/4] LLM 生成答案...")
    answer = generate_answer(question, ranked)
    logger.info(f"✓ 生成完成，答案长度：{len(answer)} 字符")

    elapsed = time.time() - start_time
    logger.info(f"[4/4] 完整查询耗时 {elapsed:.2f}s")
    logger.info("=" * 60)

    return answer
