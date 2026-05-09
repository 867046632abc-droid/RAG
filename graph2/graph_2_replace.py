"""
方案 A — Reranker 替代 grade_documents
retrieve(k=30) → rerank(top-5) → generate → [hallucination/answer check] → END / transform_query
"""
from pprint import pprint

from langgraph.constants import START, END
from langgraph.graph import StateGraph

from utils.draw_png import draw_graph
from graph2.generate_node2 import generate
from graph2.graph_2 import (
    grade_generation_v_documents_and_question,
    route_question,
)
from graph2.graph_state2 import GraphState
from graph2.reranker_node import rerank
from graph2.transform_query_node import transform_query
from graph2.web_search_node import web_search
from tools.retriever_tools import get_retriever
from utils.log_utils import log


def retrieve_wide(state: dict) -> dict:
    log.info("---[Replace] 宽召回 k=30 检索文档---")
    question = state["question"]
    transform_count = state.get("transform_count", 0)
    documents = get_retriever(k=30).invoke(question)
    return {"documents": documents, "question": question, "transform_count": transform_count}


def decide_to_generate_replace(state: dict) -> str:
    """Without LLM grader: always generate if we have docs, else transform/web."""
    filtered = state["documents"]
    transform_count = state.get("transform_count", 0)
    if not filtered:
        if transform_count >= 2:
            log.info("---[Replace] 无文档且已转换2次，转 web search---")
            return "web_search"
        log.info("---[Replace] 无文档，转换查询---")
        return "transform_query"
    log.info("---[Replace] 有文档，直接生成---")
    return "generate"


workflow = StateGraph(GraphState)

workflow.add_node("web_search", web_search)
workflow.add_node("retrieve", retrieve_wide)
workflow.add_node("rerank", rerank)
workflow.add_node("generate", generate)
workflow.add_node("transform_query", transform_query)

workflow.add_conditional_edges(
    START,
    route_question,
    {"web_search": "web_search", "vectorstore": "retrieve"},
)
workflow.add_edge("web_search", "generate")
workflow.add_edge("retrieve", "rerank")
workflow.add_conditional_edges("rerank", decide_to_generate_replace)
workflow.add_conditional_edges(
    "generate",
    grade_generation_v_documents_and_question,
    {"not supported": "generate", "useful": END, "not useful": "transform_query"},
)
workflow.add_edge("transform_query", "retrieve")

graph = workflow.compile()

def run_cli():
    draw_graph(graph, "graph_rag2_replace.png")

    while True:
        question = input("用户：").strip()
        if question.lower() in ["q", "exit", "quit"]:
            print("对话结束，拜拜！")
            break

        inputs = {"question": question}
        for output in graph.stream(inputs):
            for key, value in output.items():
                pprint(f"Node '{key}':")
            pprint("\n---\n")

        pprint(value.get("generation", ""))


if __name__ == "__main__":
    run_cli()