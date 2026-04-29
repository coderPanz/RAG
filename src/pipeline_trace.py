import time
from dataclasses import dataclass, field
from typing import List

from langchain_core.documents import Document

from src.generation.llm import generate_answer
from src.indexing.store import similarity_search
from src.retrieval.reranker import rerank_with_scores


@dataclass
class StageTimings:
    retrieve_s: float = 0.0
    rerank_s: float = 0.0
    llm_s: float = 0.0

    @property
    def total_s(self) -> float:
        return self.retrieve_s + self.rerank_s + self.llm_s


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
    question: str
    answer: str
    candidate_count: int
    candidates: List[CandidatePreview]
    rerank_rows: List[RerankRow]
    context_documents: List[Document]
    timings: StageTimings = field(default_factory=StageTimings)


def query_with_trace(
    question: str,
    retrieve_top_k: int = 10,
    rerank_top_k: int = 3,
) -> TraceResult:
    timings = StageTimings()

    t0 = time.perf_counter()
    candidates = similarity_search(question, top_k=retrieve_top_k)
    timings.retrieve_s = time.perf_counter() - t0

    candidate_previews = [
        CandidatePreview(
            index=i,
            source=doc.metadata.get("source", "unknown"),
            preview=doc.page_content[:120].replace("\n", " "),
        )
        for i, doc in enumerate(candidates)
    ]

    t0 = time.perf_counter()
    ranked = rerank_with_scores(question, candidates, top_k=rerank_top_k)
    timings.rerank_s = time.perf_counter() - t0

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
    )
