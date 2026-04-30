# 初始化 llm sdk
from openai import OpenAI
import os
from dotenv import load_dotenv
# 将根目录的环境变量注入 py 进程
load_dotenv()

_current_model = None
_llm_client = None

# 读取当前 python 进程的环境变量
def get_llm_client():
    global _llm_client
    if _llm_client:
        return _llm_client
    logger.debug(f"初始化 LLM 客户端")
    llm_client = OpenAI(
        api_key=os.getenv('LLM_API_KEY'), 
        base_url=os.getenv('LLM_BASE_URL')
    )
    return llm_client
