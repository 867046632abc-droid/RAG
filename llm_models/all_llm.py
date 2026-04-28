from langchain_community.tools import TavilySearchResults
from langchain_openai import ChatOpenAI

from utils.env_utils import OPENAI_API_KEY, DEEPSEEK_API_KEY

llm = ChatOpenAI(  # openai的
    temperature=0,
    model='gpt-4o-mini',
    api_key=OPENAI_API_KEY,
    timeout=120,
    max_retries=2,
    )


web_search_tool = TavilySearchResults(max_results=3)

# llm = ChatOpenAI(
#     temperature=0,
#     model='deepseek-chat',
#     api_key=DEEPSEEK_API_KEY,
#     base_url="https://api.deepseek.com")
