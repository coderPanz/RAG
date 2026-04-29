# RAG

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

## 开发规划

### 第一阶段（已完成）
基础 RAG 系统：文档索引 → 静态流程 → 单轮问答

**特点：**
- 用户提问 → 向量召回 → 重排 → LLM 生成
- 流程固定，每个环节不可跳过

### 第二阶段（Agentic RAG）
智能 Agent 驱动的 RAG 系统：LLM 自主决策检索策略

**核心特性：**
1. **智能判断** — Agent 根据问题决定是否需要检索
2. **多步骤推理** — 支持多轮检索与推理，逐步逼近答案
3. **工具调用** — 集成外部工具（搜索、计算、API 等）
4. **反思与修正** — Agent 验证答案准确性，必要时重新检索
5. **对话记忆** — 支持多轮对话的上下文维护

**可能实现方向：**
- 使用 LangChain AgentExecutor / ReAct 框架
- 定义 Retrieval、Rerank、Answer Verify 等工具
- 实现 Tool Calling 让 LLM 自主调用 RAG 管道
- 支持 Function Calling 扩展外部能力（Web Search、Database Query 等）

**示例流程：**
```
用户: "如何配置系统的数据库连接？"

Agent 思考: 需要先检索相关文档，再基于检索结果判断是否需要补充搜索

步骤 1: 调用 retrieve_documents("数据库配置")
步骤 2: 检查召回结果，若不满足则调用 web_search()
步骤 3: 综合多个信息源生成答案
步骤 4: 反思答案质量，若不确定则继续检索
```




