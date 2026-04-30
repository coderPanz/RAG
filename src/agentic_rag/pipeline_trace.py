import time
from dataclasses import dataclass, field
from typing import List

from langchain_core.documents import Document

from utils.llm import generate_answer, get_llm_client, get_model
from utils.store import similarity_search
from utils.reranker import rerank_with_scores

MAX_RETRIES = 2


@dataclass
class StageTimings:
    router_s:   float = 0.0
    retrieve_s: float = 0.0
    rerank_s:   float = 0.0
    llm_s:      float = 0.0

    @property
    def total_s(self) -> float:
        return self.router_s + self.retrieve_s + self.rerank_s + self.llm_s


@dataclass
class CandidatePreview:
    index: int
    source: str
    preview: str


@dataclass
class RerankRow:
    rank: int
    score: float
    original_index: int
    source: str
    preview: str


@dataclass
class TraceResult:
    question:          str
    answer:            str
    candidate_count:   int
    candidates:        List[CandidatePreview]
    rerank_rows:       List[RerankRow]
    context_documents: List[Document]
    timings:           StageTimings = field(default_factory=StageTimings)
    router_decision:   str          = "retrieve"
    query_rewrites:    List[str]    = field(default_factory=list)
    iterations:        int          = 1


def _llm_yes_no(prompt: str) -> bool:
    client = get_llm_client()
    response = client.chat.completions.create(
        model=get_model(),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=5,
    )
    return response.choices[0].message.content.strip().lower().startswith("yes")


def _agent_router(question: str) -> bool:
    return _llm_yes_no(
        "判断下面的问题是否需要查阅文档或知识库才能回答。\n"
        "如果是闲聊、问候、常识类问题，不需要检索，回答 no。\n"
        "如果问题涉及专业知识、具体事实或文档内容，需要检索，回答 yes。\n"
        "只回答 yes 或 no，不要有其他内容。\n\n"
        f"问题：{question}"
    )


def _evaluate_relevance(question: str, docs: List[Document]) -> bool:
    if not docs:
        return False
    snippets = "\n\n".join(
        f"[{i+1}] {doc.page_content[:200]}" for i, doc in enumerate(docs)
    )
    return _llm_yes_no(
        "判断以下文档片段是否足以回答给定问题。\n"
        "如果文档包含足够的相关信息，回答 yes；否则回答 no。\n"
        "只回答 yes 或 no，不要有其他内容。\n\n"
        f"问题：{question}\n\n文档片段：\n{snippets}"
    )


def _rewrite_query(original: str, current: str) -> str:
    client = get_llm_client()
    response = client.chat.completions.create(
        model=get_model(),
        messages=[{
            "role": "user",
            "content": (
                "当前检索词未能找到足够相关的文档，请重写检索词以获取更好的结果。\n"
                "可以扩展关键词、换个角度表述或拆分为更具体的短语。\n"
                "只输出新的检索词，不要有其他内容。\n\n"
                f"原始问题：{original}\n当前检索词：{current}"
            ),
        }],
        max_tokens=100,
    )
    return response.choices[0].message.content.strip()


def query_with_trace(
    question: str,
    retrieve_top_k: int = 10,
    rerank_top_k: int = 3,
) -> TraceResult:
    timings = StageTimings()
    router_decision = "retrieve"
    query_rewrites: List[str] = []
    current_query = question

    # 最终轮次的状态（每轮覆盖更新）
    candidates: list = []
    candidate_previews: list = []
    rerank_rows: list = []
    context_documents: list = []
    iterations = 0

    for attempt in range(MAX_RETRIES + 1):
        iterations = attempt + 1

        # ── 智能路由 ───────────────────────────────────────────────
        t0 = time.perf_counter()
        needs_retrieval = _agent_router(current_query)
        timings.router_s += time.perf_counter() - t0

        if not needs_retrieval:
            router_decision = "direct"
            t0 = time.perf_counter()
            client = get_llm_client()
            response = client.chat.completions.create(
                model=get_model(),
                messages=[{"role": "user", "content": question}],
            )
            answer = response.choices[0].message.content
            timings.llm_s = time.perf_counter() - t0
            return TraceResult(
                question=question,
                answer=answer,
                candidate_count=0,
                candidates=[],
                rerank_rows=[],
                context_documents=[],
                timings=timings,
                router_decision=router_decision,
                query_rewrites=query_rewrites,
                iterations=iterations,
            )

        # ── 向量检索 ───────────────────────────────────────────────
        t0 = time.perf_counter()
        candidates = similarity_search(current_query, top_k=retrieve_top_k)
        timings.retrieve_s += time.perf_counter() - t0

        candidate_previews = [
            CandidatePreview(
                index=i,
                source=doc.metadata.get("source", "unknown"),
                preview=doc.page_content[:120].replace("\n", " "),
            )
            for i, doc in enumerate(candidates)
        ]

        # ── 精排重排 ───────────────────────────────────────────────
        t0 = time.perf_counter()
        ranked = rerank_with_scores(question, candidates, top_k=rerank_top_k)
        timings.rerank_s += time.perf_counter() - t0

        rerank_rows = [
            RerankRow(
                rank=rank,
                score=r.score,
                original_index=r.original_index,
                source=r.document.metadata.get("source", "unknown"),
                preview=r.document.page_content[:120].replace("\n", " "),
            )
            for rank, r in enumerate(ranked, start=1)
        ]
        context_documents = [r.document for r in ranked]

        # ── 文档相关性评估 ─────────────────────────────────────────
        t0 = time.perf_counter()
        is_relevant = _evaluate_relevance(question, context_documents)
        timings.router_s += time.perf_counter() - t0

        if is_relevant or attempt == MAX_RETRIES:
            break

        # ── Query 重写 ─────────────────────────────────────────────
        t0 = time.perf_counter()
        current_query = _rewrite_query(question, current_query)
        timings.router_s += time.perf_counter() - t0
        query_rewrites.append(current_query)

    # ── LLM 生成答案 ──────────────────────────────────────────────
    t0 = time.perf_counter()
    answer = generate_answer(question, context_documents)
    timings.llm_s = time.perf_counter() - t0

    return TraceResult(
        question=question,
        answer=answer,
        candidate_count=len(candidates),
        candidates=candidate_previews,
        rerank_rows=rerank_rows,
        context_documents=context_documents,
        timings=timings,
        router_decision=router_decision,
        query_rewrites=query_rewrites,
        iterations=iterations,
    )
