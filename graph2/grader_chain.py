from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from llm_models.all_llm import llm


# 数据模型 - 文档相关性评分
class GradeDocuments(BaseModel):
    """对检索到的文档进行相关性评分的二元判断"""

    binary_score: str = Field(
        description="文档是否与问题相关，取值为'yes'或'no'"
    )


# 带函数调用的LLM初始化
structured_llm_grader = llm.with_structured_output(GradeDocuments)  # 绑定结构化输出到评分模型

# 提示词模板
system = """你是一个专业的半导体技术文档相关性评分器。
判断标准：文档内容是否直接包含回答该问题所需的技术信息。
- "yes"：文档包含与问题直接相关的技术术语、数值、机制描述，能够为回答提供具体依据
- "no"：文档仅主题相关但不含具体答案信息，或属于引言/结论等泛泛描述，或内容与问题无关
请给出严格的 yes/no 二元评分。"""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),  # 系统角色提示
        ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),  # 用户输入模板
    ]
)

# 构建检索评分器工作流
retrieval_grader_chain = grade_prompt | structured_llm_grader  # 组合提示模板和LLM评分器
