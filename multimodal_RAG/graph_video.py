import re

from langgraph.constants import START, END
from langgraph.graph import StateGraph

from graph2.graph_2 import get_graph as get_graph2
from multimodal_RAG.video_generate_node import video_generate
from multimodal_RAG.video_state import VideoGraphState
from utils.log_utils import log

_graph2 = get_graph2()

_VIDEO_KEYWORDS = {"视频", "video", "生成视频", "制作视频", "动画", "演示"}

# 匹配 "请帮我生成一个10s的视频介绍" 这类视频指令前缀
_VIDEO_CMD_RE = re.compile(
    r'^.*?(生成|制作|做|创建)\s*\w{0,6}(视频|动画|演示)\s*(介绍|讲解|解释|说明)?',
    re.IGNORECASE,
)


def _strip_video_cmd(question: str) -> str:
    """
    从视频请求中提取纯知识问题传给 RAG，避免 '视频介绍' 字样干扰幻觉检测。
    例：'请帮我生成一个10s的视频介绍FinFET结构' → 'FinFET结构'
    """
    cleaned = _VIDEO_CMD_RE.sub("", question).strip()
    return cleaned if len(cleaned) > 2 else question


def run_rag(state: VideoGraphState) -> dict:
    """将 graph2 作为黑盒整体调用，仅传入知识问题，取回 generation 和 documents。"""
    raw_q = state["question"]
    rag_q = _strip_video_cmd(raw_q)
    if rag_q != raw_q:
        log.info(f"RAG 查询已净化: '{raw_q}' → '{rag_q}'")

    # recursion_limit 防止幻觉检测死循环崩溃
    result = _graph2.invoke(
        {"question": rag_q},
        config={"recursion_limit": 15},
    )
    return {
        "generation": result.get("generation", ""),
        "documents": result.get("documents", []),
    }


def _route_after_rag(state: VideoGraphState) -> str:
    explicit = state.get("video_requested", False)
    keyword_hit = any(kw in state.get("question", "") for kw in _VIDEO_KEYWORDS)
    if explicit or keyword_hit:
        log.info("---检测到视频请求，路由到视频生成节点---")
        return "video_generate"
    return END


workflow = StateGraph(VideoGraphState)
workflow.add_node("run_rag", run_rag)
workflow.add_node("video_generate", video_generate)

workflow.add_edge(START, "run_rag")
workflow.add_conditional_edges(
    "run_rag",
    _route_after_rag,
    {"video_generate": "video_generate", END: END},
)
workflow.add_edge("video_generate", END)

graph = workflow.compile()


def get_graph():
    return graph


if __name__ == "__main__":


    # ── 方式二：关键词自动触发视频生成 ──
    # 问题中含 "视频/动画/演示/video" 等词会自动路由到视频节点
    result2 = graph.invoke({
        "question": "请帮我生成一个10s的视频介绍FinFET结构",
        # video_save_dir 不传则默认保存到 datas/videos/
    })
    print("回答:", result2["generation"])
    print("视频本地路径:", result2.get("video_path"))

    # ── 方式三：显式标志触发，自定义 provider 和保存路径 ──
    result3 = graph.invoke({
        "question": "什么是GAAFET？",
        "video_requested": True,          # 强制触发，问题无需含关键词
        "video_provider": "kling",         # 可选 "sora"（默认）或 "kling"
        "video_save_dir": r"D:\my_videos", # 自定义保存目录
    })
    print("回答:", result3["generation"])
    print("视频本地路径:", result3.get("video_path"))
