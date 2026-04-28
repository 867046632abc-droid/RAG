"""意图分类链：将用户问题分为 5 种意图，供图做细粒度路由。"""
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from llm_models.all_llm import llm


class IntentResult(BaseModel):
    """意图分析结果"""

    intent: Literal["comparison", "formula", "explanation", "factual", "realtime"] = Field(
        description="问题意图类别"
    )
    reason: str = Field(description="一句话说明判断依据")


_structured_llm = llm.with_structured_output(IntentResult)

_system = """你是半导体技术问答系统的意图分析器，将用户问题分类为以下 5 种意图之一：

- comparison（对比分析）：问题涉及两个或多个概念/技术/方案的比较
  示例："SADP 与 LELE 的核心区别是什么？""FinFET 和 GAAFET 在静电控制上有何差异？"

- formula（公式推导）：问题涉及数学/物理公式、符号定义、参数推导或量化关系
  示例："高χ值嵌段共聚物的χ值如何影响周期尺寸？""DIBL 的量化公式是什么？"

- explanation（概念解释）：问题要求解释某个技术概念的原理、工作机制或工艺流程
  示例："HKMG 技术如何降低漏电流？""等离子体刻蚀的物理机制是什么？"

- factual（事实查询）：问题要求提取具体数值、参数、工艺指标或工程事实
  示例："16nm FinFET 比 28nm 工艺功耗降低多少？""EUV 光刻胶的随机缺陷密度要求是多少？"

- realtime（实时信息）：问题涉及价格行情、产品发布、时事新闻等知识库无法覆盖的实时数据
  示例："台积电最新季报营收是多少？""当前 EUV 设备的最新报价？"

判断原则：优先选最具体的意图类别；若问题同时涉及公式推导和对比，选 comparison。"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _system),
    ("human", "{question}"),
])

intent_chain = _prompt | _structured_llm
