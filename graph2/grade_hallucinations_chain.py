from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

from llm_models.all_llm import llm


# 数据模型 - 生成内容幻觉评分
class GradeHallucinations(BaseModel):
    """对生成回答中是否存在幻觉进行二元评分"""

    binary_score: str = Field(
        description="回答是否基于事实，取值为'yes'或'no'"
    )


# 带函数调用的LLM初始化
structured_llm_grader = llm.with_structured_output(GradeHallucinations)  # 绑定结构化输出到评分模型

# 提示词模板
system = """你是一个严格的事实核查评分器。
评判标准：生成内容中的每一个具体事实（尤其是数值、参数、材料名称）必须能在给定事实集中找到明确依据。
- "yes"：所有具体陈述均可在事实集中找到原文支撑（合理总结和改写允许）
- "no"：存在任何事实集未提及的具体数值、参数或机制描述（包括推算和补充）
注意：对事实集内容的合理总结允许判 yes，但补充事实集以外的具体数字必须判 no。"""

hallucination_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),  # 系统角色设定
        ("human", "事实集: \n\n {documents} \n\n 生成内容: {generation}"),  # 用户输入模板
    ]
)

# 构建幻觉检测工作流
hallucination_grader_chain = (
        hallucination_prompt  # 使用幻觉检测提示模板
        | structured_llm_grader  # 调用结构化评分的LLM
)
