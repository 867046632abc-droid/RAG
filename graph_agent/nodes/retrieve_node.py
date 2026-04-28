"""检索节点：根据意图动态调整召回数量 k，并封装精排逻辑。"""
from graph2.reranker_node import rerank
from tools.retriever_tools import get_retriever
from utils.log_utils import log

# 对比类问题需要更多候选文档，公式/解释类适中，事实查询精准即可
_INTENT_K: dict[str, int] = {
    "comparison": 20,
    "formula": 12,
    "explanation": 12,
    "factual": 10,
}


def retrieve_by_intent(state: dict) -> dict:
    """检索 Agent：按意图动态决定召回量 k，从 Milvus 混合检索候选文档。"""
    intent = state.get("intent", "factual")
    k = _INTENT_K.get(intent, 10)
    question = state["question"]
    log.info("---[检索 Agent] intent=%s, k=%d, 开始混合检索---", intent, k)
    documents = get_retriever(k=k).invoke(question)
    log.info("---[检索 Agent] 召回 %d 篇文档---", len(documents))
    return {
        "documents": documents,
        "question": question,
        "transform_count": state.get("transform_count", 0),
    }


def rerank_docs(state: dict) -> dict:
    """精排节点：复用 graph2 的 BGE reranker，保留 top-N 文档。"""
    return rerank(state)
