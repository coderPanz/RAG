from utils.llm import get_llm_client
from utils.prompt_manage import PromptManager
from utils.rag_search import rag_search
from utils.logger import setup_logger
import json
import re

logger = setup_logger("agentic.router")
prompt_manager = PromptManager()


def llm_reason(query: str):
    logger.debug("llm_reason 调用 | query_len=%d", len(query))
    client = get_llm_client()
    response = client.chat.completions.create(
        model='deepseek-v4-flash',
        messages=[
            {"role": "system", "content": query}
        ]
    )
    result = response.choices[0].message.content.strip()
    logger.debug("llm_reason 完成 | result_len=%d", len(result))
    return result


def action_match(text: str):
    if re.search(r'chat_qa', text):
        logger.debug("action_match → chat_qa")
        return 'chat_qa'
    if re.search(r'knowledge_qa', text):
        logger.debug("action_match → knowledge_qa")
        return 'knowledge_qa'

    try:
        json_text = text
        json_match = re.search(r"\{.*\}", text, re.S)
        if json_match:
            json_text = json_match.group(0)
        payload = json.loads(json_text)
        score = payload.get("score")
        if score == "resolve":
            logger.debug("action_match → resolve")
            return "resolve"
        if score == "reject":
            re_write_query = payload.get("query", "").strip()
            logger.debug("action_match → reject | re_write_query=%r", re_write_query)
            return re_write_query
    except json.JSONDecodeError:
        pass

    score_match = re.search(r'["\']?score["\']?\s*:\s*["\']?(\w+)["\']?', text)
    if score_match:
        score = score_match.group(1)
        if score == "reject":
            query_match = re.search(r"query:\s*(.+)", text)
            re_write_query = query_match.group(1).strip() if query_match else ""
            logger.debug("action_match → reject | re_write_query=%r", re_write_query)
            return re_write_query
        if score == "resolve":
            logger.debug("action_match → resolve")
            return "resolve"

    logger.warning("action_match → None（未匹配任何分支） | text=%r", text[:120])
    return None


def llm_router(query: str) -> str:
    logger.info("llm_router 开始 | query=%r", query)

    # 路由决策
    router_raw = llm_reason(prompt_manager.build_router_prompt(query))
    logger.info("路由 LLM 原始输出 | raw=%r", router_raw[:200])

    fork_res = action_match(router_raw)
    logger.info("路由分支 → %r", fork_res)

    if fork_res == 'knowledge_qa':
        logger.info("[RAG 分支] 开始向量检索 | query=%r", query)
        docs, llm_reason_res = rag_search(query)
        logger.info("[RAG 分支] 检索完成 | doc_count=%d", len(docs) if docs else 0)

        # 文档相关性评分
        logger.info("[RAG 分支] 开始文档相关性评分")
        score_res = rag_depend_reason(query, docs, llm_reason_res)
        logger.info("[RAG 分支] 相关性评分结果 → %r", score_res)

        if isinstance(score_res, dict) and score_res.get("score_res") == "reject":
            re_write = score_res.get("re_write_query") or query
            logger.info("[RAG 分支] 评分 reject，重写 query 并重走 RAG | re_write=%r", re_write)
            docs, answer = rag_search(re_write)
            logger.info("[RAG 分支] 二次检索完成 | doc_count=%d", len(docs) if docs else 0)
            return answer

        logger.info("llm_router 完成 → RAG 结果返回")
        return score_res

    else:
        logger.info("[直接对话分支] 路由到普通 LLM 生成 | fork_res=%r", fork_res)
        res = llm_reason(query)
        logger.info("llm_router 完成 → 直接回答")
        return res


def rag_depend_reason(query: str, embed_doc, llm_reason_res):
    """
    文档相关性评分
      query：用户原始输入
      embed_doc: rag 检索到的向量文档片段
      llm_reason_res：基于 rag 片段生成的答案
    """
    logger.info("rag_depend_reason 开始 | query=%r", query)

    raw = llm_reason(prompt_manager.build_doc_depend_prompt(
        query=query,
        embed_doc=embed_doc,
        llm_reason_res=llm_reason_res
    ))
    logger.debug("rag_depend_reason LLM 原始输出 | raw=%r", raw[:200])

    score_res = action_match(raw)
    logger.info("rag_depend_reason 评分结果 → %r", score_res)

    if score_res == "resolve":
        logger.info("rag_depend_reason → resolve，直接返回 LLM 答案")
        return llm_reason_res

    logger.info("rag_depend_reason → reject，返回重写 query | re_write=%r", score_res)
    return {
        "score_res": "reject",
        "re_write_query": score_res
    }
