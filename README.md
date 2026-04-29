# RAG

# 本地知识库 RAG

基于本地文档构建的检索增强生成（RAG）系统，使用阿里百炼大模型作为生成端。

## 架构

```
离线阶段（建索引）
文档 → 分片 → 向量化 → ChromaDB

在线阶段（问答）
问题 → 向量化 → 召回 → 重排 → LLM → 答案
```

## 项目结构

```
RAG/
├── doc/                        # 知识库文档（.md / .pdf）
├── src/
│   ├── ingestion/loader.py     # 文档加载与分片（LangChain）
│   ├── embedding/vectorizer.py # 文本向量化（BAAI/bge-large-zh-v1.5）
│   ├── indexing/store.py       # 向量存储与召回（ChromaDB）
│   ├── retrieval/reranker.py   # 重排序（BAAI/bge-reranker-base）
│   ├── generation/llm.py       # 大模型生成（DashScope）
│   └── pipeline.py             # RAG 完整流水线
├── tests/                      # 单元测试
├── main.py                     # 程序入口
├── requirements.txt
└── .env.example
```

## 环境准备

> 推荐使用 Python 3.11。系统自带版本过新时（如 3.14），部分依赖可能不兼容，可通过 `brew install python@3.11` 安装后使用 `python3.11`。

### 1. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 下载模型

```bash
modelscope download --model BAAI/bge-large-zh-v1.5
modelscope download --model BAAI/bge-reranker-base
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入 DashScope API Key：

```bash
cp .env.example .env
```

```
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

> 在 [阿里云百炼控制台](https://bailian.console.aliyun.com/) 创建 API Key。

## 使用

将文档放入 `doc/` 目录（支持 `.md` 和 `.pdf`），然后运行：

```bash
python main.py
```

程序会自动完成建索引和问答两个阶段。

## 技术选型

| 模块 | 技术 |
|------|------|
| 文档加载与分片 | LangChain + PyPDF |
| 向量化 | BAAI/bge-large-zh-v1.5 |
| 向量数据库 | ChromaDB |
| 重排序 | BAAI/bge-reranker-base |
| 大模型 | 阿里百炼 qwen-plus（OpenAI 兼容接口） |



# 本地知识库 RAG 方案第一阶段

## RAG 流程

提问前：1. 提供文档； 2. 文档分片；3. 向量化；4. 索引
提问后：1. 问题向量化；2. 召回（相识度检索）；3. 重排（使用性能更高框架进行相识度检索）；4. 生成（将问题和重排结果喂给 llm）；输出答案

## 技术选型：

### llm

llm 使用阿里百炼平台 sdk

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

response = client.responses.create(
    model="qwen3.6-plus",
    input="你能做些什么？"
)

# 获取模型回复
print(response.output_text)
```

### 文档分片：使用 langchain

代码示例：

```py
from langchain_community.document_loaders import PyPDFLoader
loader = PyPDFLoader("example_data/state_of_the_union.pdf")
pages = loader.load()
print(len(pages))
```

### 向量化：

模型：BAAI/bge-large-zh-v1.5
通过 transformers 包，您可以像这样使用模型：首先，将输入传递给变换器模型，然后选择第一个令牌（即，[CLS]）的最后一个隐藏状态作为句子嵌入。

```py
from modelscope import AutoTokenizer, AutoModel
import torch
# Sentences we want sentence embeddings for
sentences = ["样例数据-1", "样例数据-2"]

# Load model from HuggingFace Hub
tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-large-zh-v1.5')
model = AutoModel.from_pretrained('BAAI/bge-large-zh-v1.5')
model.eval()

# Tokenize sentences
encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')
# for s2p(short query to long passage) retrieval task, add an instruction to query (not add instruction for passages)
# encoded_input = tokenizer([instruction + q for q in queries], padding=True, truncation=True, return_tensors='pt')

# Compute token embeddings
with torch.no_grad():
    model_output = model(**encoded_input)
    # Perform pooling. In this case, cls pooling.
    sentence_embeddings = model_output[0][:, 0]
# normalize embeddings
sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
print("Sentence embeddings:", sentence_embeddings)
```

### 索引：chromadb技术

### 召回：使用 chromadb 的相似度检索

### 重排：使用性能更高框架进行相似度检索

模型：BAAI/bge-reranker-base
通过transformers包，您可以像这样使用模型：首先，将输入传递给transformer模型，然后选择第一个令牌（即，[CLS]）的最后一个隐藏状态作为句子嵌入。

```python
from modelscope import AutoTokenizer, AutoModel
import torch
# Sentences we want sentence embeddings for
sentences = ["样例数据-1", "样例数据-2"]

# Load model from HuggingFace Hub
tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-reranker-base')
model = AutoModel.from_pretrained('BAAI/bge-reranker-base')
model.eval()

# Tokenize sentences
encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')
# for s2p(short query to long passage) retrieval task, add an instruction to query (not add instruction for passages)
# encoded_input = tokenizer([instruction + q for q in queries], padding=True, truncation=True, return_tensors='pt')

# Compute token embeddings
with torch.no_grad():
    model_output = model(**encoded_input)
    # Perform pooling. In this case, cls pooling.
    sentence_embeddings = model_output[0][:, 0]
# normalize embeddings
sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
print("Sentence embeddings:", sentence_embeddings)
```

### 生成：将问题和重排结果喂给 llm

### 输出答案



## 模型下载流程
1. 在下载前，请先通过如下命令安装ModelScope
```bash
pip install modelscope
```
2. 通过如下命令下载模型
```bash
modelscope download --model BAAI/bge-reranker-base
modelscope download --model BAAI/bge-large-zh-v1.5
```