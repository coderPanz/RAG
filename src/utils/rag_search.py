from typing import List, Tuple

from langchain_core.documents import Document

from utils.store import similarity_search
from utils.llm import generate_answer


def rag_search(query: str, top_k: int = 10) -> Tuple[List[Document], str]:
    """执行完整 RAG 流程：向量检索 + LLM 生成

    Returns:
        docs: 检索到的文档分片列表
        answer: 基于文档分片由 LLM 生成的答案
    """
    docs = similarity_search(query, top_k=top_k)
    answer = generate_answer(query, docs)
    return docs, answer
