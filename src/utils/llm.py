import os
from typing import List

from dotenv import load_dotenv
from langchain_core.documents import Document
from openai import OpenAI

from utils.logger import setup_logger
from utils.prompt_manage import PromptManager

load_dotenv()

_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_DEFAULT_MODEL = "deepseek-v4-flash"
_llm_client = None
_current_model: str | None = None
_prompt_manager = PromptManager()
logger = setup_logger("generation")


def get_model() -> str:
    return _current_model or os.getenv("DASHSCOPE_MODEL", _DEFAULT_MODEL)


def set_model(name: str) -> None:
    global _current_model
    _current_model = name


def test_model_connectivity(model_name: str) -> tuple[bool, str]:
    """用最小请求验证模型是否可用，返回 (成功, 消息)。"""
    try:
        client = get_llm_client()
        client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        return True, f"模型 {model_name} 连通正常"
    except Exception as e:
        return False, str(e)


def get_llm_client():
    """初始化 LLM 客户端（单例）"""
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise EnvironmentError("未设置环境变量 DASHSCOPE_API_KEY，请在 .env 文件中配置")
        logger.debug(f"初始化 LLM 客户端，base_url={_BASE_URL}")
        _llm_client = OpenAI(api_key=api_key, base_url=_BASE_URL)
    return _llm_client


def _format_context(context_documents: List[Document]) -> str:
    """将召回/重排后的文档分片拼接成 LLM 上下文"""
    context_parts = []
    for index, document in enumerate(context_documents, start=1):
        source = document.metadata.get("source", "unknown")
        context_parts.append(
            f"【资料 {index}】\n来源：{source}\n内容：{document.page_content}"
        )
    return "\n\n".join(context_parts)


def generate_answer(query: str, context_documents: List[Document]) -> str:
    """用 LLM 生成最终答案"""
    logger.debug(f"准备调用 LLM，上下文分片数={len(context_documents)}")

    client = get_llm_client()
    context = _format_context(context_documents)

    messages = _prompt_manager.build_knowledge_qa_messages(
        query=query,
        context=context,
    )

    model_name = 'deepseek-v4-flash'
    logger.debug(f"调用 LLM：model={model_name}")

    completion = client.chat.completions.create(
        model=model_name,
        messages=messages,
    )
    answer = completion.choices[0].message.content
    logger.debug(f"LLM 生成完成，答案长度={len(answer)}")
    return answer
