"""意图分析节点：调用 intent_chain，将结果写入 AgentState。"""
from graph_agent.intent_chain import intent_chain
from utils.log_utils import log


def classify_intent(state: dict) -> dict:
    """意图分析 Agent：判断问题类型，为后续路由提供依据。"""
    question = state["question"]
    result = intent_chain.invoke({"question": question})
    log.info(
        "---[意图分析 Agent] intent=%s | 理由：%s---",
        result.intent,
        result.reason,
    )
    return {
        "intent": result.intent,
        "intent_reason": result.reason,
        "transform_count": state.get("transform_count", 0),
        "expert_output": "",
        "generation": "",
        "confidence": "",
    }
