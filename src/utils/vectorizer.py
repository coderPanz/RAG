import os
from pathlib import Path
from typing import List

import torch
from transformers import AutoModel, AutoTokenizer

from utils.logger import setup_logger

_MODEL_NAME = "BAAI/bge-large-zh-v1.5"
_DEFAULT_MODEL_DIR = Path.home() / ".cache/modelscope/hub/models/BAAI/bge-large-zh-v1___5"
logger = setup_logger("embedding")

def load_embedding_model():
    """加载 BGE 向量化模型（单例）"""
    model_dir = Path(os.getenv("BGE_MODEL_DIR") or _DEFAULT_MODEL_DIR)
    logger.debug(f"模型目录：{model_dir}")

    if not model_dir.exists():
        raise FileNotFoundError(f"模型目录不存在，请设置 BGE_MODEL_DIR：{model_dir}")
    if not any((model_dir / name).exists() for name in ("pytorch_model.bin", "model.safetensors")):
        raise FileNotFoundError(f"模型目录缺少权重文件：{model_dir}")

    logger.debug("加载分词器...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    logger.debug("加载模型...")
    model = AutoModel.from_pretrained(model_dir)
    model.eval()
    logger.debug("模型已加载并设置为评估模式")

    return tokenizer, model


def embed_texts(texts: List[str]) -> torch.Tensor:
    """向量化文本列表（CLS pooling + L2 归一化）"""
    tokenizer, model = load_embedding_model()

    logger.debug(f"向量化 {len(texts)} 条文本...")
    encoded_input = tokenizer(texts, padding=True, truncation=True, return_tensors='pt')

    with torch.no_grad():
        model_output = model(**encoded_input)
        sentence_embeddings = model_output[0][:, 0]

    embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
    logger.debug(f"✓ 向量化完成，维度 = {embeddings.shape[1]}")
    return embeddings
