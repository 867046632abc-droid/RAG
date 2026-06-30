from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from llm_models.all_llm import llm


# 查询的动态路由： 根据用户的提问，决策采用哪种检索策略（网络检索，RAG）


# 数据模型
class RouteQuery(BaseModel):
    """将用户查询路由到最相关的数据源"""
    datasource: Literal["vectorstore", "web_search"] = Field(
        ...,
        description="根据用户问题选择将其路由到向量知识库或网络搜索",
    )


# 带函数调用的LLM
structured_llm_router = llm.with_structured_output(RouteQuery)

# 提示词模板
system = """你是一个擅长将用户问题路由到向量知识库或网络搜索的专家。
向量知识库包含以下主题的专业文档：
- 半导体材料与器件（HKMG、FinFET、GAAFET、量子点、量子阱）
- 芯片制造工艺（等离子体刻蚀、MOCVD、ALD、CMP、薄膜沉积）
- 光刻技术（EUV、多重曝光、DSA、光刻胶、SADP、SAQP）
- 封装技术（WLP、晶圆级封装、异构集成、RDL）
- 半导体测试与可靠性评估
对于上述主题的问题，优先使用向量知识库。
仅对时事新闻、价格行情、具体产品发布等实时信息使用网络搜索。"""
route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),  # 系统提示词
        ("human", "{question}"),  # 用户问题占位符
    ]
)

# 创建问题路由器链
question_router_chain = route_prompt | structured_llm_router


# 测试路由器
# print(  # 测试非技术问题（应路由到网络搜索）
#     question_router_chain.invoke(
#         {"question": "什么是EUV光刻技术?"}
#     )
# )
# print(  # 测试技术问题（应路由到向量数据库）
#     question_router_chain.invoke({"question": "今天，长沙的天气怎么样?"})
# )