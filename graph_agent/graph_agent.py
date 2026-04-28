"""graph_agent 主图：意图感知的多 Agent RAG 系统。

流程概览
--------
                         ┌─ realtime ──→ web_search ──────────────┐
START → classify_intent ─┤                                         ├→ synthesis → END
                         └─ rag ──→ retrieve → rerank → grade_docs ─┤
                                       ↑                            ├─ has docs → expert → critic
                                       │                            │      ├─ high/medium → synthesis
                                  transform_query                   │      └─ low + retry ─→ (loop)
                                       │                            │
                                       └────────────────────────────┘
                                    (no docs, transform_count < 2)
                                    (no docs, transform_count >= 2 → web_search)

与 graph2 的关键区别
-------------------
1. 意图分类（5类）替代原来的二元路由
2. 按意图动态调整检索 k（对比类 k=20，其余 k=10-12）
3. 专家 Agent 分发（事实/对比/公式/解释 四种专用 Prompt）
4. 批判 Agent 输出三级置信度（high/medium/low）取代二元 yes/no
5. 合成节点整合专家输出并附置信度标注
"""
from pprint import pprint

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from draw_png import draw_graph
from graph2.grade_documents_node import grade_documents
from graph2.transform_query_node import transform_query
from graph2.web_search_node import web_search
from graph_agent.nodes.critic_node import critic_check
from graph_agent.nodes.expert_node import expert_dispatch
from graph_agent.nodes.intent_node import classify_intent
from graph_agent.nodes.retrieve_node import rerank_docs, retrieve_by_intent
from graph_agent.nodes.synthesis_node import synthesize
from graph_agent.state import AgentState
from utils.log_utils import log


# ── 条件路由函数 ──────────────────────────────────────────────────────────────

def route_by_intent(state: AgentState) -> str:
    """意图路由：实时信息走 Web，其余走 RAG 检索链。"""
    intent = state.get("intent", "factual")
    if intent == "realtime":
        log.info("---[路由] 实时信息意图 → web_search---")
        return "web_search"
    log.info("---[路由] %s 意图 → RAG 检索链---", intent)
    return "retrieve"


def decide_after_grade(state: AgentState) -> str:
    """文档过滤后的路由：有文档→专家，无文档→改写或 Web 兜底。"""
    documents = state["documents"]
    transform_count = state.get("transform_count", 0)

    if documents:
        log.info("---[路由] 有 %d 篇相关文档 → 专家 Agent---", len(documents))
        return "expert"

    if transform_count < 2:
        log.info("---[路由] 无相关文档（第 %d 次）→ 查询改写---", transform_count + 1)
        return "transform_query"

    log.info("---[路由] 改写已达 2 次仍无结果 → Web 兜底---")
    return "web_search"


def quality_gate(state: AgentState) -> str:
    """置信度门控：low 且还有重试次数 → 改写重试；否则 → 合成输出。"""
    confidence = state.get("confidence", "high")
    transform_count = state.get("transform_count", 0)

    if confidence == "low" and transform_count < 2:
        log.info("---[质量门控] 置信度=low，第 %d 次重试 → 查询改写---", transform_count + 1)
        return "transform_query"

    if confidence == "low":
        log.info("---[质量门控] 置信度=low 但重试次数已满 → 强制合成（兜底）---")
    else:
        log.info("---[质量门控] 置信度=%s → 合成最终答案---", confidence)
    return "synthesis"


# ── 图构建 ────────────────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    # 节点注册
    workflow.add_node("classify_intent", classify_intent)   # 意图分析 Agent
    workflow.add_node("retrieve", retrieve_by_intent)       # 检索 Agent（动态 k）
    workflow.add_node("rerank", rerank_docs)                # BGE 精排
    workflow.add_node("grade_docs", grade_documents)        # 相关性过滤（复用 graph2）
    workflow.add_node("expert", expert_dispatch)            # 专家分发 Agent
    workflow.add_node("critic", critic_check)               # 批判 Agent（三级置信度）
    workflow.add_node("synthesis", synthesize)              # 合成节点
    workflow.add_node("transform_query", transform_query)   # 查询改写（复用 graph2）
    workflow.add_node("web_search", web_search)             # Web 搜索（复用 graph2）

    # 边定义
    workflow.add_edge(START, "classify_intent")

    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {"web_search": "web_search", "retrieve": "retrieve"},
    )

    # RAG 检索链
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "grade_docs")

    workflow.add_conditional_edges(
        "grade_docs",
        decide_after_grade,
        {
            "expert": "expert",
            "transform_query": "transform_query",
            "web_search": "web_search",
        },
    )

    # 专家 → 批判 → 质量门控
    workflow.add_edge("expert", "critic")

    workflow.add_conditional_edges(
        "critic",
        quality_gate,
        {"synthesis": "synthesis", "transform_query": "transform_query"},
    )

    # 查询改写后重新检索（形成重试环）
    workflow.add_edge("transform_query", "retrieve")

    # Web 搜索直接合成（跳过专家和批判）
    workflow.add_edge("web_search", "synthesis")

    workflow.add_edge("synthesis", END)

    return workflow.compile()


graph = _build_graph()


def get_graph():
    return graph


# ── 命令行入口 ────────────────────────────────────────────────────────────────

def run_cli() -> None:
    draw_graph(graph, "graph_agent.png")

    print("\n半导体技术问答 · 多 Agent RAG 系统（输入 q 退出）")
    print("─" * 55)

    while True:
        question = input("\n用户：").strip()
        if question.lower() in {"q", "exit", "quit"}:
            print("已退出。")
            break
        if not question:
            continue

        inputs = {"question": question}
        log.info("=" * 55)

        final_state: dict = {}
        for output in graph.stream(inputs, config={"recursion_limit": 30}):
            for node_name, node_state in output.items():
                pprint(f"  ✓ 节点完成: {node_name}")
                final_state.update(node_state)

        generation = final_state.get("generation", "（无回答）")
        intent = final_state.get("intent", "")
        confidence = final_state.get("confidence", "")

        print(f"\n[意图: {intent} | 置信度: {confidence}]")
        print(f"\n助手：{generation}")


if __name__ == "__main__":
    run_cli()
