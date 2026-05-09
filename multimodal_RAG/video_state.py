from typing import TypedDict, List, Optional
from langchain_core.documents import Document


class VideoGraphState(TypedDict, total=False):
    """
    在 GraphState 基础上扩展的视频状态。

    graph2 内部字段（由 run_rag 节点填充）：
        question:   用户问题
        generation: RAG 生成的文字回答
        documents:  检索到的文档列表

    视频扩展字段（由调用方传入或节点填充）：
        video_requested: 是否需要生成视频（True/False）；
                         也可通过问题关键词自动检测，无需显式传入
        video_provider:  视频生成服务，"sora"（默认）或 "kling"
        video_path:      生成完成后的视频 URL 或本地路径
    """
    question: str
    generation: str
    documents: List[Document]
    video_requested: bool
    video_provider: str   # "sora"（默认）或 "kling"
    video_save_dir: str   # 本地保存目录，不传则存到项目 datas/videos/
    video_path: str       # 生成完成后的本地文件路径
