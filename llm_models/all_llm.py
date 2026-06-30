import os
from langchain_community.tools import TavilySearchResults
from langchain_openai import ChatOpenAI
from openai import OpenAI

from utils.env_utils import OPENAI_API_KEY, DEEPSEEK_API_KEY, QWEN_API_KEY, SEED_API_KEY

# llm = ChatOpenAI(  # openai的
#     temperature=0,
#     model='gpt-4o-mini',
#     api_key=OPENAI_API_KEY,
#     timeout=120,
#     max_retries=2,
#     )

# llm = ChatOpenAI(  # openai的
#     temperature=0,
#     model='qwen3-vl-235b-a22b-thinking',
#     base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
#     api_key=QWEN_API_KEY,
#     timeout=120,
#     max_retries=2,
#     )

llm = ChatOpenAI(  # openai的
    temperature=0,
    model='doubao-seed-2-0-lite-260215',
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=SEED_API_KEY,
    timeout=120,
    max_retries=2,
    )

web_search_tool = TavilySearchResults(max_results=3)

# llm = ChatOpenAI(
#     temperature=0,
#     model='deepseek-chat',
#     api_key=DEEPSEEK_API_KEY,
#     base_url="https://api.deepseek.com")

# ---------- 视频生成客户端 ----------

# OpenAI Sora：原生客户端，用于调用视频生成接口
# 文档参考：https://platform.openai.com/docs/guides/video
sora_client = OpenAI(api_key=OPENAI_API_KEY)

# Kling（可灵）：从环境变量读取，需在 .env 中配置
# KLING_ACCESS_KEY=<your_access_key>
# KLING_SECRET_KEY=<your_secret_key>
KLING_ACCESS_KEY: str = os.getenv("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY: str = os.getenv("KLING_SECRET_KEY", "")
