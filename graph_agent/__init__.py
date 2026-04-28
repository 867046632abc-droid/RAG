"""graph_agent：意图感知的多 Agent RAG 系统。

公开接口
--------
get_graph()  : 返回已编译的 LangGraph 图实例
run_cli()    : 启动命令行交互模式
AgentState   : 图的共享状态 TypedDict
"""
from graph_agent.graph_agent import get_graph, run_cli
from graph_agent.state import AgentState

__all__ = ["get_graph", "run_cli", "AgentState"]
