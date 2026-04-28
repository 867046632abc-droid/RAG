from typing import List, TypedDict

from langchain_core.documents import Document


class AgentState(TypedDict):
    """多 Agent 图的共享状态。

    字段说明
    --------
    question       : 用户原始问题（transform_query 后会被改写）
    intent         : 意图分类结果，取值见 intent_chain.IntentResult
    intent_reason  : 意图分析器给出的一句话理由（用于日志/展示）
    documents      : 当前候选文档列表（检索→精排→过滤后更新）
    expert_output  : 专家 Agent 输出的原始分析文本
    generation     : 最终面向用户的答案（由 synthesis_node 生成）
    transform_count: 查询改写次数（用于控制重试上限）
    confidence     : 批判 Agent 输出的置信度 high | medium | low
    """

    question: str
    intent: str
    intent_reason: str
    documents: List[Document]
    expert_output: str
    generation: str
    transform_count: int
    confidence: str
