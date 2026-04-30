import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

import torch
from langchain_core.documents import Document
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from utils.logger import setup_logger


@dataclass
class RankedDocument:
    document: Document
    score: float
    original_index: int

_DEFAULT_RERANKER_MODEL_DIR = Path.home() / ".cache/modelscope/hub/models/BAAI/bge-reranker-base"
_reranker_model = None
_reranker_tokenizer = None
logger = setup_logger("retrieval")


def load_reranker_model():
    """加载重排序模型（单例）"""
    global _reranker_model, _reranker_tokenizer

    if _reranker_model is not None and _reranker_tokenizer is not None:
        return _reranker_tokenizer, _reranker_model

    model_dir = Path(os.getenv("RERANKER_MODEL_DIR") or _DEFAULT_RERANKER_MODEL_DIR)
    logger.debug(f"模型目录：{model_dir}")

    if not model_dir.exists():
        raise FileNotFoundError(f"重排序模型目录不存在：{model_dir}")
    if not any((model_dir / name).exists() for name in ("pytorch_model.bin", "model.safetensors")):
        raise FileNotFoundError(f"权重文件缺失：{model_dir}")

    logger.debug("加载 cross-encoder 分词器...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    logger.debug("加载 cross-encoder 模型...")
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    logger.debug("✓ 重排序模型已加载")

    _reranker_tokenizer = tokenizer
    _reranker_model = model
    return tokenizer, model


def rerank(query: str, documents: List[Document], top_k: int = 3) -> List[Document]:
    """Cross-encoder 精排：对候选文档按相关性重排，返回 top_k 个。"""
    if not documents:
        logger.debug("没有候选文档，跳过重排")
        return []

    logger.debug(f"对 {len(documents)} 个候选文档进行重排...")
    tokenizer, model = load_reranker_model()

    pairs = [[query, doc.page_content] for doc in documents]
    encoded_input = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt")

    with torch.no_grad():
        scores = model(**encoded_input).logits.view(-1).float()

    top_indices = scores.argsort(descending=True)[:top_k].tolist()
    ranked_docs = [documents[i] for i in top_indices]

    logger.debug(f"✓ 重排完成，选出 top-{top_k} 文档")
    for i, (idx, score) in enumerate(zip(top_indices, scores[top_indices].tolist()), 1):
        logger.debug(f"   [{i}] 分数={score:.3f} | {documents[idx].metadata.get('source', 'unknown')}")

    return ranked_docs


def rerank_with_scores(query: str, documents: List[Document], top_k: int = 3) -> List[RankedDocument]:
    """与 rerank() 逻辑相同，但返回含分数和原始索引的 RankedDocument 列表。"""
    if not documents:
        return []

    tokenizer, model = load_reranker_model()
    pairs = [[query, doc.page_content] for doc in documents]
    encoded_input = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt")

    with torch.no_grad():
        scores = model(**encoded_input).logits.view(-1).float()

    top_indices = scores.argsort(descending=True)[:top_k].tolist()
    return [
        RankedDocument(
            document=documents[i],
            score=float(scores[i]),
            original_index=i,
        )
        for i in top_indices
    ]
