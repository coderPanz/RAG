import importlib.util
import sys
from dataclasses import asdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "src" / "common-rag"))

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from utils.metrics import (
    fetch_latency_series,
    fetch_recent_queries,
    fetch_rerank_score_distribution,
    fetch_stage_breakdown_aggregates,
    init_db,
    record_query,
)
from utils.llm import get_model, set_model, test_model_connectivity
from pipeline import build_index
from pipeline_trace import query_with_trace as _common_query_with_trace

init_db()

_agentic_trace_mod = None


def _get_agentic_query_with_trace():
    global _agentic_trace_mod
    if _agentic_trace_mod is None:
        spec = importlib.util.spec_from_file_location(
            "agentic_pipeline_trace",
            _ROOT / "src" / "agentic-rag" / "pipeline_trace.py",
        )
        _agentic_trace_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_agentic_trace_mod)
    return _agentic_trace_mod.query_with_trace


def _query_with_trace(question: str, mode: str):
    if mode == "agentic":
        return _get_agentic_query_with_trace()(question)
    return _common_query_with_trace(question)


st.set_page_config(page_title="RAG Explorer", layout="wide")

if "last_trace" not in st.session_state:
    st.session_state.last_trace = None

# ── 侧边栏 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("RAG 模式")
    rag_mode = st.radio(
        "检索模式",
        options=["common", "agentic"],
        format_func=lambda x: "普通模式" if x == "common" else "Agentic 模式（查询分解）",
        index=0,
        key="rag_mode",
    )
    st.divider()

    st.header("模型设置")
    st.caption(f"当前模型：`{get_model()}`")
    new_model = st.text_input("切换模型", value=get_model(), key="model_input")
    if st.button("验证并切换", use_container_width=True):
        with st.spinner(f"验证 {new_model} 连通性…"):
            ok, msg = test_model_connectivity(new_model)
        if ok:
            set_model(new_model)
            st.success(f"已切换至 `{new_model}`")
            st.rerun()
        else:
            st.error(msg)

tab_ask, tab_dashboard, tab_index = st.tabs(["问答", "性能监控", "索引状态"])

# ── Tab 1: 问答 + Pipeline 追踪 ──────────────────────────────────────────────
with tab_ask:
    mode_label = "Agentic" if rag_mode == "agentic" else "普通"
    st.title(f"RAG 问答系统 [{mode_label}模式]")

    question = st.text_input("请输入问题", placeholder="请输入您的问题…", key="question_input")
    submitted = st.button("提交", type="primary", disabled=not question.strip())

    if submitted and question.strip():
        with st.spinner("查询中…"):
            result = _query_with_trace(question.strip(), rag_mode)
        record_query(result)
        st.session_state.last_trace = result

    trace = st.session_state.last_trace
    if trace:
        st.subheader("答案")
        st.markdown(trace.answer)

        with st.expander("Pipeline 执行追踪", expanded=True):
            router_s = getattr(trace.timings, "router_s", 0.0)
            router_decision = getattr(trace, "router_decision", None)
            query_rewrites = getattr(trace, "query_rewrites", [])
            iterations = getattr(trace, "iterations", 1)

            if router_decision is not None:
                # Agentic 模式：5 列，含路由耗时
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("总耗时", f"{trace.timings.total_s:.2f} s")
                col2.metric("路由决策", f"{router_s:.2f} s")
                col3.metric("向量召回", f"{trace.timings.retrieve_s:.2f} s")
                col4.metric("精排重排", f"{trace.timings.rerank_s:.2f} s")
                col5.metric("LLM 生成", f"{trace.timings.llm_s:.2f} s")

                decision_label = "直接回答（无需检索）" if router_decision == "direct" else "调用知识库检索"
                st.markdown(f"**路由决策：** {decision_label}　**检索轮次：** {iterations}")
                if query_rewrites:
                    st.markdown("**Query 重写记录：**")
                    for i, rw in enumerate(query_rewrites, 1):
                        st.markdown(f"- 第 {i} 次改写：{rw}")
            else:
                # 普通模式：4 列
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("总耗时", f"{trace.timings.total_s:.2f} s")
                col2.metric("向量召回", f"{trace.timings.retrieve_s:.2f} s")
                col3.metric("精排重排", f"{trace.timings.rerank_s:.2f} s")
                col4.metric("LLM 生成", f"{trace.timings.llm_s:.2f} s")

            st.markdown(f"**召回候选文档数：{trace.candidate_count}**")

            with st.expander("所有候选文档"):
                df_cands = pd.DataFrame([asdict(c) for c in trace.candidates])
                st.dataframe(df_cands, use_container_width=True, hide_index=True)

            st.markdown("**精排结果（top 3）**")
            df_rerank = pd.DataFrame([asdict(r) for r in trace.rerank_rows])
            st.dataframe(
                df_rerank,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "score": st.column_config.ProgressColumn(
                        "分数",
                        min_value=-10.0,
                        max_value=10.0,
                        format="%.3f",
                    )
                },
            )

            st.markdown("**发送给 LLM 的 Context**")
            for i, doc in enumerate(trace.context_documents, 1):
                source = doc.metadata.get("source", "unknown")
                with st.expander(f"[{i}] {source}"):
                    st.text(doc.page_content)

# ── Tab 2: 性能监控 Dashboard ────────────────────────────────────────────────
with tab_dashboard:
    st.header("性能监控")

    if st.button("刷新数据"):
        st.rerun()

    series_data = fetch_latency_series()
    if series_data:
        df_series = pd.DataFrame(series_data)
        df_series["时间"] = pd.to_datetime(df_series["ts"], unit="s")

        col_left, col_right = st.columns([2, 1])

        with col_left:
            fig_line = px.line(
                df_series,
                x="时间",
                y=["total_s", "retrieve_s", "rerank_s", "llm_s"],
                labels={"value": "耗时 (s)", "variable": "阶段"},
                title="历史查询耗时趋势",
            )
            fig_line.update_traces(mode="lines+markers")
            st.plotly_chart(fig_line, use_container_width=True)

        with col_right:
            agg = fetch_stage_breakdown_aggregates()
            if any(v > 0 for v in agg.values()):
                fig_pie = px.pie(
                    names=["向量召回", "精排重排", "LLM 生成"],
                    values=[agg["avg_retrieve_s"], agg["avg_rerank_s"], agg["avg_llm_s"]],
                    hole=0.4,
                    title="平均各阶段耗时占比",
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        scores = fetch_rerank_score_distribution()
        if scores:
            fig_hist = px.histogram(
                x=scores,
                nbins=40,
                labels={"x": "Cross-encoder 分数"},
                title="Rerank 分数分布",
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        st.subheader("最近查询记录")
        recent = fetch_recent_queries(limit=20)
        if recent:
            df_recent = pd.DataFrame(recent)
            df_recent["时间"] = pd.to_datetime(df_recent["ts"], unit="s").dt.strftime("%Y-%m-%d %H:%M:%S")
            st.dataframe(
                df_recent[["时间", "question", "total_s", "retrieve_s", "rerank_s", "llm_s", "candidate_count"]].rename(
                    columns={
                        "question": "问题",
                        "total_s": "总耗时(s)",
                        "retrieve_s": "召回(s)",
                        "rerank_s": "重排(s)",
                        "llm_s": "LLM(s)",
                        "candidate_count": "候选数",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("暂无查询记录。请先在「问答」页提交问题。")

# ── Tab 3: 索引状态 ────────────────────────────────────────────────────────
with tab_index:
    st.header("索引状态")

    from utils.store import get_chroma_client

    store = get_chroma_client()
    count = store._collection.count()
    st.metric("已索引分片数", count)

    if count == 0:
        st.warning("索引为空，请点击下方按钮构建索引。")
        if st.button("构建索引"):
            with st.spinner("构建索引中，请稍候…"):
                build_index()
            st.success("索引构建完成。")
            st.rerun()
    else:
        st.success(f"索引已就绪（共 {count} 个分片）。")
