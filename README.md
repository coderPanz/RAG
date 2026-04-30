# RAG

基于本地文档构建的检索增强生成（RAG）系统，使用阿里百炼大模型作为生成端。

## 架构

**普通模式（common）**
```
离线阶段：文档 → 分片 → 向量化 → ChromaDB
在线阶段：问题 → 向量召回 → 重排 → LLM → 答案
```

**Agentic 模式（agentic）**
```
离线阶段：同上
在线阶段：问题 → LLM 路由（单次调用）
             ├─ knowledge_qa → 向量召回 → 重排 → LLM → 相关性评分
             │                    └─ reject → query 重写 → 重走 RAG
             └─ 直接回答（路由器在同一次调用中输出答案）
```

## 项目结构

```
RAG/
├── doc/                                   # 知识库文档（.md / .pdf）
├── src/
│   ├── common_rag/
│   │   ├── pipeline.py                    # 普通 RAG 流水线
│   │   └── pipeline_trace.py              # 带结构化追踪的查询接口（Web UI 用）
│   ├── agentic_rag/
│   │   ├── agent_router.py                # LLM 路由器（knowledge_qa / 直接回答 / 相关性评分）
│   │   ├── pipeline.py                    # Agentic 流水线（路由 → RAG → 评分 → 重写）
│   │   └── pipeline_trace.py              # Agentic 带追踪查询接口
│   └── utils/
│       ├── logger.py                      # 日志配置（共享）
│       ├── loader.py                      # 文档加载与分片（LangChain）
│       ├── vectorizer.py                  # 文本向量化（BAAI/bge-large-zh-v1.5）
│       ├── store.py                       # 向量存储与召回（ChromaDB）
│       ├── reranker.py                    # 重排序（BAAI/bge-reranker-base）
│       ├── llm.py                         # 大模型生成（DashScope）
│       ├── rag_search.py                  # RAG 检索封装
│       ├── prompt_manage.py               # Prompt 模板管理
│       ├── get_llm_client.py              # LLM 客户端工厂
│       └── metrics/store.py               # SQLite 查询指标持久化
├── app.py                                 # Streamlit Web UI 入口
├── main.py                                # CLI 入口
├── metrics.db                             # 查询指标数据库（运行时生成，已 gitignore）
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

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并填入 DashScope API Key：

```bash
cp .env.example .env
```

```
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

> 在 [阿里云百炼控制台](https://bailian.console.aliyun.com/) 创建 API Key。

## 使用

将文档放入 `doc/` 目录（支持 `.md` 和 `.pdf`）。

### CLI 模式

```bash
# 普通模式（默认）
python main.py --model=common

# Agentic 模式（LLM 路由 + 按需 RAG）
python main.py --model=agentic
```

### Web UI 模式

**启动**

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

**首次使用流程**

1. 切换到 **「索引状态」** Tab，点击「构建索引」按钮——系统会加载 `doc/` 下的所有文档，完成分片、向量化并写入 ChromaDB（约需数十秒）。
2. 看到「索引已就绪」提示后，切换到 **「问答」** Tab。
3. 在左侧侧边栏选择检索模式：
   - **普通模式** — 向量召回 → 精排 → LLM 生成
   - **Agentic 模式** — LLM 路由 → 按需检索 → 相关性评分 → 结果输出
4. 输入问题，点击「提交」，查看答案及 Pipeline 执行追踪。

> 索引只需构建一次，数据持久化在 `src/utils/chroma_db/`，重启后无需重建。

**页面功能**

| 页面 | 功能 |
|------|------|
| **问答** | 输入问题，查看答案；内嵌 Pipeline 执行追踪面板（候选文档、Rerank 分数、Context 内容、各阶段耗时） |
| **性能监控** | 历史查询耗时趋势图、各阶段占比、Rerank 分数分布直方图、最近查询记录表 |
| **索引状态** | 查看 ChromaDB 分片数量，支持一键构建索引 |

## 技术选型

| 模块 | 技术 |
|------|------|
| 文档加载与分片 | LangChain + PyPDF |
| 向量化 | BAAI/bge-large-zh-v1.5 |
| 向量数据库 | ChromaDB |
| 重排序 | BAAI/bge-reranker-base |
| 大模型 | 阿里百炼 qwen-plus（OpenAI 兼容接口） |
| Web UI | Streamlit |
| 可视化图表 | Plotly |
| 指标持久化 | SQLite（stdlib） |

## 开发规划

### 第一阶段（已完成）
基础 RAG 系统：文档索引 → 静态流程 → 单轮问答

**特点：**
- 用户提问 → 向量召回 → 重排 → LLM 生成
- 流程固定，每个环节不可跳过

### 可视化层（已完成）
Streamlit Web UI + Pipeline 追踪面板 + 性能监控 Dashboard

**新增文件：**
- `app.py` — Streamlit 三 Tab 应用入口
- `src/common_rag/pipeline_trace.py` — `query_with_trace()` 返回结构化 `TraceResult`（候选列表、Rerank 分数、各阶段耗时），供 UI 展示
- `src/utils/metrics/store.py` — SQLite 读写，记录每次查询的耗时、分数、候选数等指标
- `src/utils/reranker.py` 新增 `rerank_with_scores()` — 暴露 cross-encoder 分数，原 `rerank()` 不变

### 目录重构（已完成）
将原扁平 `src/` 重构为 `src/common_rag/`、`src/agentic_rag/`、`src/utils/` 三个 Python 包，共享工具层（向量化、存储、重排、LLM）。

**设计决策：**
- `src/utils/` 作为公共工具包，两种模式共享，避免代码重复
- `main.py` 通过 `--model` 参数选择加载 `common_rag` 或 `agentic_rag` 的 pipeline
- ChromaDB 索引统一存放，两种模式共享同一向量索引

### 第二阶段（Agentic RAG）
当前已实现基于 **LLM 路由器** 的 Agentic 流水线。

**已实现：**
- `src/agentic_rag/agent_router.py` — LLM 路由器，含三个核心节点：
  - `llm_router`：路由决策入口；路由提示词合并路由与回答为**单次 LLM 调用**——若输出 `knowledge_qa` 则进入 RAG，否则直接返回路由器的输出作为答案
  - `rag_depend_reason`：文档相关性评分，决定是否接受当前检索结果或重写 query 重走 RAG
  - `action_match`：解析 LLM 输出，提取路由指令（knowledge_qa / score resolve/reject）
- `src/agentic_rag/pipeline.py` — 带自适应路由的 Agentic 查询接口
- `src/agentic_rag/pipeline_trace.py` — 带结构化追踪的 Agentic 查询接口，供 Web UI 展示
- 各节点接入结构化日志（`agentic.router` logger），记录路由决策、检索数量、评分结果等关键信息

**后续扩展方向：**
- 使用 LangChain AgentExecutor / ReAct 框架实现多轮工具调用
- 定义 Retrieval、Rerank、Answer Verify 等 Tool
- 支持多轮对话记忆




